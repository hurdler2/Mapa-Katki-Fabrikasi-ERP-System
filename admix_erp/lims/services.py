"""LIMS servisleri: push (talep gönder) + pull (sonuç al) + QCTestResult üret."""
from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from quality.models import QCParameter, QCTestResult
from quality.services import record_test

from .adapters import LimsAdapter, SampleRequestPayload, build_adapter
from .models import LimsEndpoint, LimsSyncLog, SampleRequest


@transaction.atomic
def create_and_send_request(
    endpoint: LimsEndpoint,
    *,
    request_number: str,
    parameters: list[QCParameter],
    batch=None,
    lot=None,
    priority: str = "NORMAL",
    adapter: LimsAdapter | None = None,
) -> SampleRequest:
    """Bir örnek talebini oluştur ve LIMS'e gönder."""
    if (batch is None) == (lot is None):
        raise ValidationError("Ya batch ya da lot verilmeli (yalnızca biri).")

    target_type = "BATCH" if batch else "LOT"
    target_ref = batch.batch_number if batch else lot.lot_number

    req = SampleRequest.objects.create(
        request_number=request_number,
        endpoint=endpoint, batch=batch, lot=lot,
        priority=priority,
    )
    req.parameters.set(parameters)

    payload = SampleRequestPayload(
        request_number=request_number,
        target_type=target_type,
        target_reference=target_ref,
        parameters=[p.code for p in parameters],
        priority=priority,
    )
    req.payload_sent = {
        "request_number": payload.request_number,
        "target_type": payload.target_type,
        "target_reference": payload.target_reference,
        "parameters": payload.parameters,
        "priority": payload.priority,
    }

    adapter = adapter or build_adapter(endpoint)
    try:
        lims_ref = adapter.send_sample_request(payload)
    except Exception as exc:
        req.status = SampleRequest.Status.FAILED
        req.notes = f"{type(exc).__name__}: {exc}"
        req.save(update_fields=["status", "notes", "payload_sent", "updated_at"])
        LimsSyncLog.objects.create(
            endpoint=endpoint, direction=LimsSyncLog.Direction.PUSH,
            status=LimsSyncLog.Status.FAILED, records_processed=0,
            error_message=str(exc),
        )
        raise

    req.status = SampleRequest.Status.SENT
    req.sent_at = timezone.now()
    req.lims_reference = lims_ref
    req.save(update_fields=[
        "status", "sent_at", "lims_reference", "payload_sent", "updated_at",
    ])

    LimsSyncLog.objects.create(
        endpoint=endpoint, direction=LimsSyncLog.Direction.PUSH,
        status=LimsSyncLog.Status.SUCCESS, records_processed=1,
        payload_summary=f"Sent request {request_number} → {lims_ref}",
    )
    return req


@transaction.atomic
def pull_results(
    endpoint: LimsEndpoint,
    *,
    adapter: LimsAdapter | None = None,
    user=None,
) -> dict:
    """LIMS'ten bekleyen sonuçları çeker ve QCTestResult'lara işler.

    Her sonuç için:
    - SampleRequest'i request_number ile bulur
    - QCParameter'ı parameter_code ile bulur
    - record_test() ile QCTestResult üretir (spec değerlendirmeyle)
    - SampleRequest.status = RECEIVED + payload_received doldurur
    """
    adapter = adapter or build_adapter(endpoint)
    try:
        results = list(adapter.pull_results())
    except Exception as exc:
        LimsSyncLog.objects.create(
            endpoint=endpoint, direction=LimsSyncLog.Direction.PULL,
            status=LimsSyncLog.Status.FAILED,
            error_message=str(exc), executed_by=user,
        )
        raise

    processed = 0
    unmatched = 0
    for r in results:
        req = SampleRequest.objects.filter(
            request_number=r.request_number, endpoint=endpoint,
        ).first()
        if req is None:
            unmatched += 1
            continue
        param = QCParameter.objects.filter(code=r.parameter_code).first()
        if param is None:
            unmatched += 1
            continue

        value = Decimal(str(r.value)) if r.value is not None else None
        record_test(
            param, value,
            lot=req.lot, batch=req.batch,
            tester=r.tester or f"LIMS ({endpoint.code})",
            notes=f"LIMS ref: {r.lims_reference}",
        )
        req.payload_received = r.raw or {
            "value": r.value, "unit": r.unit, "verdict": r.verdict,
        }
        req.status = SampleRequest.Status.RECEIVED
        req.received_at = timezone.now()
        req.save(update_fields=[
            "payload_received", "status", "received_at", "updated_at",
        ])
        processed += 1

    status = (
        LimsSyncLog.Status.SUCCESS if unmatched == 0
        else LimsSyncLog.Status.PARTIAL
    )
    LimsSyncLog.objects.create(
        endpoint=endpoint, direction=LimsSyncLog.Direction.PULL,
        status=status, records_processed=processed,
        executed_by=user,
        payload_summary=f"processed={processed}, unmatched={unmatched}",
    )
    return {"processed": processed, "unmatched": unmatched}
