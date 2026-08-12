"""MRP testleri: brüt/net ihtiyaç + requisition üretimi."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from mrp.models import MaterialRequirement, PurchaseRequisition
from mrp.services import (
    approve_requisition,
    create_requisitions_from_mrp,
    run_mrp,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def planner(db):
    return User.objects.create_user("mrp_planner", password="pw")


def test_mrp_with_only_production_order(order, released_lots, planner):
    """Ufuk içinde PLANNED bir üretim emri var → SP ihtiyacı hesaplanır.
    Mevcut RELEASED SP stoğu (2000) yeterli olduğundan OK/REORDER olur, SHORTAGE yok.
    """
    order.scheduled_date = dt.date.today() + dt.timedelta(days=1)
    order.save()

    run = run_mrp(
        run_number="MRP-1",
        horizon_date=dt.date.today() + dt.timedelta(days=7),
        executed_by=planner,
        include_forecasts=False,
        include_sales_orders=False,
    )
    sp_req = run.requirements.get(raw_material__code="SP")
    # target 500, base 1000 → SP=175, W=300, G=7.5, HD=17.5
    assert sp_req.gross_requirement == Decimal("175.0000")
    assert sp_req.on_hand == Decimal("2000.0000")
    assert sp_req.net_requirement == Decimal("0")
    # Yeterli stok → OK veya REORDER (gross>0 durumu)
    assert sp_req.status in {
        MaterialRequirement.Status.OK, MaterialRequirement.Status.REORDER,
    }


def test_mrp_shortage_creates_requisition(order, planner, raws, supplier, uom_kg):
    """SP stoğu yoksa → SHORTAGE + requisition."""
    order.scheduled_date = dt.date.today() + dt.timedelta(days=1)
    order.save()

    # released_lots fixture kullanılmadı → SP stoğu yok
    run = run_mrp(
        run_number="MRP-2",
        horizon_date=dt.date.today() + dt.timedelta(days=7),
        executed_by=planner,
        include_forecasts=False, include_sales_orders=False,
    )
    sp_req = run.requirements.get(raw_material__code="SP")
    assert sp_req.on_hand == Decimal("0")
    assert sp_req.net_requirement == Decimal("175.0000")
    assert sp_req.status == MaterialRequirement.Status.SHORTAGE

    reqs = create_requisitions_from_mrp(run, requested_by=planner)
    codes = {r.raw_material.code for r in reqs}
    assert "SP" in codes
    sp_r = next(r for r in reqs if r.raw_material.code == "SP")
    assert sp_r.quantity == Decimal("175.0000")
    assert sp_r.status == PurchaseRequisition.Status.SUBMITTED


def test_approve_requisition(order, planner, raws):
    order.scheduled_date = dt.date.today() + dt.timedelta(days=1)
    order.save()
    run = run_mrp(
        run_number="MRP-3", horizon_date=dt.date.today() + dt.timedelta(days=7),
        executed_by=planner, include_forecasts=False, include_sales_orders=False,
    )
    reqs = create_requisitions_from_mrp(run, requested_by=planner)
    approver = User.objects.create_user("mrp_approver", password="pw")
    approve_requisition(reqs[0], approver=approver)
    reqs[0].refresh_from_db()
    assert reqs[0].status == PurchaseRequisition.Status.APPROVED
