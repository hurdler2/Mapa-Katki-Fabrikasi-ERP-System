"""MCOS Faz F — Retrieval Endpoint.

`GET /api/v1/retrieve/?ref=<any-id>` — herhangi bir MCOS/ERP kimliğinden
tam dossier'i tek çağrıda döner. 00_MCO_1 sheet 9 sınav kriteri:
2 dakika içinde her kayıt bulunabilir olmalı.

Çözülen ref türleri:
    - Case ID          (INCIDENT-001, NCR-2026-...)
    - Record ID        (RTS-G001-001, CAPA-G001-...)
    - Evidence ID      (EVD-G001-001)
    - Decision ID      (DEC-001)
    - Gate ID          (GATE-001)
    - Batch number     (BATCH-2026-0001)
    - Lot number       (LOT-SP-001)

Cevap: {resolved_type, case, records, evidence, decisions, gate,
        generated_at, generation_time_ms, warnings}
"""
from __future__ import annotations

import time
from typing import Any

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gates.models import Gate
from records.models import Case, Decision, Evidence, RecordInstance


# 2 dakikalık SLA — 00_MCO_1 sınav kriteri.
RETRIEVAL_SLA_MS = 2 * 60 * 1000  # 120_000


# ---------------------------------------------------------------------------
# Resolver — ref hangi katmanda?
# ---------------------------------------------------------------------------

def _resolve_ref(ref: str) -> tuple[str, Any] | tuple[None, None]:
    """Ref'i tüm MCOS + ERP kimlik alanlarında arar. İlk eşleşen (type, obj) döner."""
    ref = (ref or "").strip()
    if not ref:
        return None, None

    # 1) Case
    obj = (Case.objects
           .select_related("business_line", "detected_by")
           .filter(case_id=ref).first())
    if obj:
        return "Case", obj

    # 2) RecordInstance
    obj = (RecordInstance.objects
           .select_related("case__business_line", "controlled_code",
                            "preparer", "reviewer", "approver")
           .filter(record_id=ref).first())
    if obj:
        return "RecordInstance", obj

    # 3) Evidence
    obj = (Evidence.objects
           .select_related("case__business_line", "record_instance",
                            "collected_by")
           .filter(evidence_id=ref).first())
    if obj:
        return "Evidence", obj

    # 4) Decision
    obj = (Decision.objects
           .select_related("case__business_line", "record_instance",
                            "decision_maker")
           .filter(decision_id=ref).first())
    if obj:
        return "Decision", obj

    # 5) Gate
    obj = (Gate.objects
           .select_related("case__business_line", "owner", "closed_by")
           .prefetch_related("sections__evidence")
           .filter(gate_id=ref).first())
    if obj:
        return "Gate", obj

    # 6) ProductionBatch — batch_number
    from production.models import ProductionBatch
    obj = (ProductionBatch.objects
           .select_related("recipe__product", "business_line",
                            "controlled_code")
           .filter(batch_number=ref).first())
    if obj:
        return "Batch", obj

    # 7) RawMaterialLot — lot_number
    from inventory.models import RawMaterialLot
    obj = (RawMaterialLot.objects
           .select_related("raw_material", "supplier", "business_line")
           .filter(lot_number=ref).first())
    if obj:
        return "Lot", obj

    return None, None


# ---------------------------------------------------------------------------
# Serialize — küçük, JSON-safe payload'lar
# ---------------------------------------------------------------------------

def _s_case(c: Case) -> dict:
    return {
        "case_id": c.case_id,
        "family": c.family,
        "severity": c.severity,
        "status": c.status,
        "business_line": getattr(c.business_line, "code", None),
        "gate": c.gate or None,
        "title": c.title,
        "description": c.description,
        "detected_by": c.detected_by.username if c.detected_by_id else None,
        "timeline": {
            "detected_at": c.detected_at.isoformat() if c.detected_at else None,
            "contained_at": c.contained_at.isoformat() if c.contained_at else None,
            "scope_frozen_at": c.scope_frozen_at.isoformat() if c.scope_frozen_at else None,
            "classified_at": c.classified_at.isoformat() if c.classified_at else None,
            "recovery_at": c.recovery_at.isoformat() if c.recovery_at else None,
            "reconciled_at": c.reconciled_at.isoformat() if c.reconciled_at else None,
            "capa_opened_at": c.capa_opened_at.isoformat() if c.capa_opened_at else None,
            "closed_at": c.closed_at.isoformat() if c.closed_at else None,
        },
    }


def _s_record(r: RecordInstance) -> dict:
    return {
        "record_id": r.record_id,
        "controlled_code": r.controlled_code.full_code if r.controlled_code_id else None,
        "case_id": r.case.case_id if r.case_id else None,
        "status": r.status,
        "preparer": r.preparer.username if r.preparer_id else None,
        "reviewer": r.reviewer.username if r.reviewer_id else None,
        "approver": r.approver.username if r.approver_id else None,
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "record_copy_at": r.record_copy_at.isoformat() if r.record_copy_at else None,
    }


def _s_evidence(e: Evidence) -> dict:
    return {
        "evidence_id": e.evidence_id,
        "case_id": e.case.case_id if e.case_id else None,
        "record_id": e.record_instance.record_id if e.record_instance_id else None,
        "kind": e.kind,
        "title": e.title,
        "sha256": e.sha256 or None,
        "is_contemporaneous": e.is_contemporaneous,
        "is_original": e.is_original,
        "collected_at": e.collected_at.isoformat() if e.collected_at else None,
        "collected_by": e.collected_by.username if e.collected_by_id else None,
    }


def _s_decision(d: Decision) -> dict:
    return {
        "decision_id": d.decision_id,
        "case_id": d.case.case_id if d.case_id else None,
        "record_id": d.record_instance.record_id if d.record_instance_id else None,
        "level": d.level,
        "status": d.status,
        "decision_date": d.decision_date.isoformat() if d.decision_date else None,
        "decision_maker": d.decision_maker.username if d.decision_maker_id else None,
        "veto_holder_role": d.veto_holder_role or None,
        "delegated_authority": d.delegated_authority or None,
        "signature_count": d.signatures.count(),
    }


def _s_gate(g: Gate) -> dict:
    return {
        "gate_id": g.gate_id,
        "case_id": g.case.case_id if g.case_id else None,
        "status": g.status,
        "owner": g.owner.username if g.owner_id else None,
        "opened_at": g.opened_at.isoformat() if g.opened_at else None,
        "closed_at": g.closed_at.isoformat() if g.closed_at else None,
        "sections": [
            {
                "section": gs.section,
                "completion_status": gs.completion_status,
                "evidence_count": gs.evidence.count(),
                "reviewer": gs.reviewer.username if gs.reviewer_id else None,
            }
            for gs in g.sections.all()
        ],
        "reopen_count": len(g.reopen_history or []),
    }


def _s_batch(b) -> dict:
    return {
        "batch_number": b.batch_number,
        "product": b.recipe.product.code if getattr(b.recipe, "product_id", None) else None,
        "recipe_version": b.recipe.version if b.recipe_id else None,
        "status": b.status,
        "qc_status": b.qc_status,
        "business_line": getattr(b.business_line, "code", None),
        "controlled_code": b.controlled_code.full_code if b.controlled_code_id else None,
    }


def _s_lot(l) -> dict:
    return {
        "lot_number": l.lot_number,
        "raw_material": l.raw_material.code if l.raw_material_id else None,
        "supplier": l.supplier.code if l.supplier_id else None,
        "qc_status": l.qc_status,
        "received_qty": str(l.received_qty),
        "remaining_qty": str(l.remaining_qty),
        "business_line": getattr(l.business_line, "code", None),
    }


# ---------------------------------------------------------------------------
# Dossier — bir Case için tüm bağlı katmanları topla
# ---------------------------------------------------------------------------

def _build_dossier_for_case(case: Case) -> dict:
    """Case için tam MCOS dossier. Records + evidence + decisions + gate."""
    records = list(case.records.select_related("controlled_code",
                                                 "preparer", "reviewer",
                                                 "approver"))
    evidence = list(case.evidence_set.select_related("collected_by",
                                                       "record_instance"))
    decisions = list(case.decisions.select_related("decision_maker",
                                                     "record_instance")
                                     .prefetch_related("signatures"))
    gates = list(case.gates.select_related("owner", "closed_by")
                             .prefetch_related("sections__evidence"))
    return {
        "case": _s_case(case),
        "records": [_s_record(r) for r in records],
        "evidence": [_s_evidence(e) for e in evidence],
        "decisions": [_s_decision(d) for d in decisions],
        "gate": _s_gate(gates[0]) if gates else None,
        "gates_all": [_s_gate(g) for g in gates] if len(gates) > 1 else None,
    }


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def retrieve(request):
    """MCOS retrieval endpoint. Query: `?ref=<id>`."""
    t0 = time.perf_counter()
    ref = request.GET.get("ref", "").strip()

    if not ref:
        return Response({
            "error": "ref query parameter is required.",
            "example": "/api/v1/retrieve/?ref=INCIDENT-001",
        }, status=400)

    resolved_type, obj = _resolve_ref(ref)
    if obj is None:
        return Response({
            "error": f"Kimlik bulunamadı: '{ref}'",
            "searched": ["Case", "RecordInstance", "Evidence", "Decision",
                          "Gate", "Batch", "Lot"],
        }, status=404)

    warnings = []

    # Case → tam dossier (resolved_object = case özeti)
    if resolved_type == "Case":
        dossier = _build_dossier_for_case(obj)
        payload = {
            "resolved_type": "Case",
            "resolved_object": dossier["case"],
            **dossier,
        }
    # Alt katmanlar → resolved_object olarak kendini koyar, sonra Case dossier
    elif resolved_type in ("RecordInstance", "Evidence", "Decision", "Gate"):
        serializers = {
            "RecordInstance": _s_record,
            "Evidence": _s_evidence,
            "Decision": _s_decision,
            "Gate": _s_gate,
        }
        matched = serializers[resolved_type](obj)
        case = getattr(obj, "case", None)
        # Case dossier'ı önce koy (evidence/records/decisions listeleri onun),
        # sonra resolved_object'i EN SON yaz — anahtar çakışması olmasın diye
        payload = {"resolved_type": resolved_type}
        if case:
            payload.update(_build_dossier_for_case(case))
        payload["resolved_object"] = matched
    elif resolved_type == "Batch":
        payload = {
            "resolved_type": "Batch",
            "resolved_object": _s_batch(obj),
        }
    elif resolved_type == "Lot":
        payload = {
            "resolved_type": "Lot",
            "resolved_object": _s_lot(obj),
        }
    else:
        payload = {"resolved_type": resolved_type}

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    if elapsed_ms > RETRIEVAL_SLA_MS:
        warnings.append(
            f"SLA ihlali: {elapsed_ms}ms > {RETRIEVAL_SLA_MS}ms (2 dakika)"
        )

    payload.update({
        "generated_at": timezone.now().isoformat(),
        "generation_time_ms": elapsed_ms,
        "warnings": warnings,
    })
    return Response(payload)
