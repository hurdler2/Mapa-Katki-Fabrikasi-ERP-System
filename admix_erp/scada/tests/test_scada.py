"""SCADA testleri: reçete indirme + PLC tartım ingest → MaterialConsumption(source=SCADA)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from production.models import MaterialConsumption, ProductionBatch
from production.services import create_batch_from_order
from scada.adapters import MockAdapter, WeighmentSample
from scada.models import PLCEndpoint, RecipeDownload, WeighmentEvent
from scada.services import download_recipe, ingest_weighment, poll_and_ingest


pytestmark = pytest.mark.django_db


@pytest.fixture
def endpoint(db):
    return PLCEndpoint.objects.create(
        code="PLC-1", name="Reaktör 1 PLC",
        protocol=PLCEndpoint.Protocol.MOCK,
        host="127.0.0.1", port=4840, is_active=True,
    )


def test_download_recipe_creates_batch_and_payload(endpoint, order):
    adapter = MockAdapter()
    dl = download_recipe(endpoint, order, adapter=adapter)

    assert dl.status == RecipeDownload.Status.SIMULATED
    assert dl.sent_at is not None
    assert dl.batch is not None
    assert dl.batch.batch_number.startswith("AUTO-PO-001-")
    assert dl.batch.consumptions.count() == 4

    # payload doğruluğu
    assert dl.payload["order_number"] == "PO-001"
    assert dl.payload["product_code"] == "ADX-100"
    assert dl.payload["recipe_version"] == 1
    line_codes = {l["material_code"] for l in dl.payload["lines"]}
    assert line_codes == {"W", "G", "SP", "HD"}

    # adapter'a gönderildi
    assert len(adapter.sent_payloads) == 1
    assert adapter.sent_payloads[0]["batch_number"] == dl.batch.batch_number


def test_ingest_weighment_matches_consumption_and_marks_source_scada(
    endpoint, order, released_lots,
):
    batch = create_batch_from_order(order, batch_number="BATCH-SCADA-1")
    sample = WeighmentSample(tag="BATCH-SCADA-1.SP", weight=Decimal("175"))
    event = ingest_weighment(endpoint, sample)

    assert event.status == WeighmentEvent.Status.MATCHED
    assert event.consumption is not None
    c = event.consumption
    c.refresh_from_db()
    assert c.actual_weight == Decimal("175")
    assert c.source == MaterialConsumption.Source.SCADA
    assert c.lot is not None
    assert c.lot.lot_number == "LOT-SP-001"  # FEFO seçimi


def test_ingest_weighment_unmatched_when_no_pending_consumption(endpoint):
    sample = WeighmentSample(tag="BATCH-YOK.SP", weight=Decimal("100"))
    event = ingest_weighment(endpoint, sample)
    assert event.status == WeighmentEvent.Status.UNMATCHED
    assert "bulunamadı" in event.error_message.lower()


def test_ingest_weighment_bad_tag_format(endpoint):
    sample = WeighmentSample(tag="NOKTA_YOK", weight=Decimal("50"))
    event = ingest_weighment(endpoint, sample)
    assert event.status == WeighmentEvent.Status.FAILED
    assert "tag" in event.error_message.lower()


def test_poll_and_ingest_drains_adapter_queue(endpoint, order, released_lots):
    batch = create_batch_from_order(order, batch_number="BATCH-SCADA-2")
    adapter = MockAdapter(samples=[
        WeighmentSample(tag="BATCH-SCADA-2.W", weight=Decimal("300")),
        WeighmentSample(tag="BATCH-SCADA-2.G", weight=Decimal("7.5")),
        WeighmentSample(tag="BATCH-SCADA-2.SP", weight=Decimal("175")),
        WeighmentSample(tag="BATCH-SCADA-2.HD", weight=Decimal("17.5")),
    ])
    events = poll_and_ingest(endpoint, adapter=adapter)
    assert len(events) == 4
    assert all(e.status == WeighmentEvent.Status.MATCHED for e in events)

    # Tüm consumption'lar SCADA kaynağıyla dolduruldu
    scada_count = batch.consumptions.filter(
        source=MaterialConsumption.Source.SCADA,
        actual_weight__isnull=False,
    ).count()
    assert scada_count == 4


def test_repeated_ingest_for_same_consumption_matches_next_available(
    endpoint, order, released_lots,
):
    """Bir tag için ikinci event: aynı slot dolu; UNMATCHED beklenir (idempotent güvenliği)."""
    create_batch_from_order(order, batch_number="BATCH-SCADA-3")
    first = ingest_weighment(endpoint, WeighmentSample(
        tag="BATCH-SCADA-3.SP", weight=Decimal("175")))
    assert first.status == WeighmentEvent.Status.MATCHED

    second = ingest_weighment(endpoint, WeighmentSample(
        tag="BATCH-SCADA-3.SP", weight=Decimal("10")))
    assert second.status == WeighmentEvent.Status.UNMATCHED
