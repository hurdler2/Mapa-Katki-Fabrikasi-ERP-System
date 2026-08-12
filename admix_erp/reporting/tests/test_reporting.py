"""Raporlama testleri: batch_cost, mass_balance, dönem özeti, dashboard erişimi."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from production.models import ProductionBatch
from production.services import create_batch_from_order, record_dosing
from reporting.services import (
    batch_cost,
    mass_balance,
    production_summary,
    raw_material_consumption,
)


pytestmark = pytest.mark.django_db


def _dose_full(order, released_lots, batch_number, actual_qty=None):
    batch = create_batch_from_order(order, batch_number=batch_number)
    batch.transition_to(ProductionBatch.Status.IN_PROGRESS)
    for code, w in [("W", Decimal("300")), ("G", Decimal("7.5")),
                    ("SP", Decimal("175")), ("HD", Decimal("17.5"))]:
        c = batch.consumptions.get(raw_material__code=code)
        record_dosing(c, actual_weight=w)
    if actual_qty is not None:
        batch.actual_qty = actual_qty
        batch.save(update_fields=["actual_qty"])
    return batch


def test_batch_cost_computes_from_lot_unit_cost(order, released_lots):
    batch = _dose_full(order, released_lots, "BATCH-COST-1", actual_qty=Decimal("500"))
    cost = batch_cost(batch)
    # W 300 × 0.10 = 30
    # G 7.5 × 8.00 = 60
    # SP 175 × 4.00 = 700
    # HD 17.5 × 12.00 = 210
    # total = 1000
    assert cost["total_cost"] == Decimal("1000.0000")
    assert cost["per_kg_cost"] == Decimal("2.0000")
    assert len(cost["lines"]) == 4
    sp_line = next(l for l in cost["lines"] if l["raw_material"] == "SP")
    assert sp_line["line_cost"] == Decimal("700.0000")


def test_batch_cost_waste(order, released_lots):
    batch = _dose_full(order, released_lots, "BATCH-COST-2", actual_qty=Decimal("495"))
    cost = batch_cost(batch)
    assert cost["waste_qty"] == Decimal("5.0000")
    assert cost["waste_pct"] == Decimal("1.00")


def test_mass_balance(order, released_lots):
    batch = _dose_full(order, released_lots, "BATCH-COST-3", actual_qty=Decimal("495"))
    balance = mass_balance(batch)
    # Σ input = 300 + 7.5 + 175 + 17.5 = 500
    assert balance["total_input"] == Decimal("500.0000")
    assert balance["actual_output"] == Decimal("495.0000")
    assert balance["delta"] == Decimal("-5.0000")
    assert balance["delta_pct"] == Decimal("-1.00")


def test_production_summary_and_top_waste(order, released_lots):
    _dose_full(order, released_lots, "BATCH-SUM-1", actual_qty=Decimal("495"))
    _dose_full(order, released_lots, "BATCH-SUM-2", actual_qty=Decimal("450"))
    summary = production_summary()
    assert summary["total_batches"] >= 2
    assert summary["total_cost"] > 0
    # En yüksek fire: BATCH-SUM-2 (10%)
    assert summary["top_waste"][0]["batch_number"] == "BATCH-SUM-2"
    assert summary["top_waste"][0]["waste_pct"] == Decimal("10.00")


def test_raw_material_consumption(order, released_lots):
    _dose_full(order, released_lots, "BATCH-CONS-1")
    consumption = raw_material_consumption()
    by_code = {c["raw_material"]: c for c in consumption}
    assert by_code["SP"]["total_weight"] == Decimal("175.0000")
    assert by_code["W"]["total_weight"] == Decimal("300.0000")


def test_dashboard_requires_staff_login(client, order, released_lots):
    resp = client.get(reverse("reporting:dashboard"))
    # Staff olmayan (anonim) admin login sayfasına yönlendirilir
    assert resp.status_code in (302, 301)


def test_dashboard_renders_for_staff(client, order, released_lots):
    User.objects.create_user("qa", password="pw", is_staff=True)
    client.login(username="qa", password="pw")
    _dose_full(order, released_lots, "BATCH-DASH-1", actual_qty=Decimal("495"))
    resp = client.get(reverse("reporting:dashboard"))
    assert resp.status_code == 200
    assert b"BATCH-DASH-1" in resp.content


def test_batch_report_renders(client, order, released_lots):
    User.objects.create_user("qa2", password="pw", is_staff=True)
    client.login(username="qa2", password="pw")
    batch = _dose_full(order, released_lots, "BATCH-DASH-2", actual_qty=Decimal("495"))
    resp = client.get(reverse("reporting:batch_report", args=[batch.pk]))
    assert resp.status_code == 200
    assert b"BATCH-DASH-2" in resp.content
    assert b"1000" in resp.content  # total_cost
