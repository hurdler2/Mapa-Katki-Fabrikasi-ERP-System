"""LIMS testleri: push (talep) + pull (sonuç → QCTestResult)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from lims.adapters import LimsResultPayload, MockLimsAdapter
from lims.models import LimsEndpoint, LimsSyncLog, SampleRequest
from lims.services import create_and_send_request, pull_results
from production.services import create_batch_from_order
from quality.models import QCParameter, QCSpec, QCTestResult


pytestmark = pytest.mark.django_db


@pytest.fixture
def endpoint(db):
    return LimsEndpoint.objects.create(
        code="LAB-1", name="Test lab",
        protocol=LimsEndpoint.Protocol.MOCK,
        endpoint_url="http://mock",
    )


@pytest.fixture
def qc_ph(db):
    return QCParameter.objects.create(code="PH", name="pH")


def test_create_and_send_request_marks_sent(endpoint, order, released_lots, qc_ph):
    batch = create_batch_from_order(order, batch_number="BATCH-LIMS-1")
    adapter = MockLimsAdapter()
    req = create_and_send_request(
        endpoint, request_number="SR-001", parameters=[qc_ph],
        batch=batch, adapter=adapter,
    )
    assert req.status == SampleRequest.Status.SENT
    assert req.lims_reference == "MOCK-LIMS-00001"
    assert len(adapter.sent) == 1
    assert adapter.sent[0].target_reference == "BATCH-LIMS-1"
    # Sync log yazıldı
    assert LimsSyncLog.objects.filter(
        endpoint=endpoint, direction=LimsSyncLog.Direction.PUSH,
        status=LimsSyncLog.Status.SUCCESS,
    ).exists()


def test_create_request_requires_batch_xor_lot(endpoint, qc_ph):
    with pytest.raises(ValidationError):
        create_and_send_request(
            endpoint, request_number="SR-X", parameters=[qc_ph],
        )


def test_pull_results_creates_qc_test_result(endpoint, order, released_lots,
                                                product, qc_ph):
    batch = create_batch_from_order(order, batch_number="BATCH-LIMS-2")
    QCSpec.objects.create(parameter=qc_ph, product=product,
                           min_value=Decimal("4"), max_value=Decimal("7"))

    # Talep gönder
    adapter = MockLimsAdapter()
    create_and_send_request(
        endpoint, request_number="SR-002", parameters=[qc_ph],
        batch=batch, adapter=adapter,
    )
    # Sonuç geldi (PASS aralığında)
    adapter._results = [
        LimsResultPayload(
            request_number="SR-002", parameter_code="PH",
            value=5.5, unit="", tester="LabTech",
            lims_reference="LIMS-R-001",
        ),
    ]
    stats = pull_results(endpoint, adapter=adapter)
    assert stats["processed"] == 1
    assert stats["unmatched"] == 0

    # QCTestResult üretildi ve PASS
    r = QCTestResult.objects.filter(parameter=qc_ph, batch=batch).first()
    assert r is not None
    assert r.value == Decimal("5.5")
    assert r.verdict == QCTestResult.Verdict.PASS

    # SampleRequest RECEIVED
    req = SampleRequest.objects.get(request_number="SR-002")
    assert req.status == SampleRequest.Status.RECEIVED
    assert req.received_at is not None


def test_pull_results_unmatched_request(endpoint):
    adapter = MockLimsAdapter(canned_results=[
        LimsResultPayload(
            request_number="SR-UNKNOWN", parameter_code="PH",
            value=6.0, unit="",
        ),
    ])
    stats = pull_results(endpoint, adapter=adapter)
    assert stats["processed"] == 0
    assert stats["unmatched"] == 1
    log = LimsSyncLog.objects.filter(
        endpoint=endpoint, direction=LimsSyncLog.Direction.PULL,
    ).last()
    assert log.status == LimsSyncLog.Status.PARTIAL
