"""MRP servisleri: brüt/net ihtiyaç hesabı + requisition üretici."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from inventory.models import RawMaterialLot
from masterdata.models import RawMaterial
from production.models import ProductionOrder
from purchasing.models import PurchaseOrder, PurchaseOrderLine
from sales.models import SalesOrder

from .models import MaterialRequirement, MRPRun, PurchaseRequisition


ZERO = Decimal("0")


def _compute_gross_requirements(
    *,
    horizon: dt.date,
    include_forecasts: bool,
    include_sales_orders: bool,
    include_production_orders: bool,
) -> dict[int, Decimal]:
    """Hammadde başına brüt ihtiyaç. Kaynaklar:
    1. Ufuk içindeki planlanmış üretim emirleri: recipe.scaled_lines × qty
    2. Açık müşteri siparişleri: aktif reçete × qty
    3. Talep tahmini: aktif reçete × forecast qty
    Sonuç: {raw_material_id: quantity}
    """
    gross: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))

    if include_production_orders:
        pos = ProductionOrder.objects.filter(
            status__in=[
                ProductionOrder.Status.PLANNED, ProductionOrder.Status.RELEASED,
            ],
            scheduled_date__lte=horizon,
        ).select_related("recipe")
        for po in pos:
            for line in po.recipe.scaled_lines(po.target_qty):
                gross[line["raw_material"].id] += line["quantity"]

    if include_sales_orders:
        sos = SalesOrder.objects.filter(
            status__in=[SalesOrder.Status.CONFIRMED, SalesOrder.Status.PARTIAL],
            delivery_date__lte=horizon,
        ).prefetch_related("lines")
        for so in sos:
            for line in so.lines.select_related("product").all():
                outstanding = line.outstanding_qty
                if outstanding <= 0:
                    continue
                from formulation.models import Recipe
                recipe = Recipe.objects.filter(
                    product=line.product, is_active=True,
                ).first()
                if recipe is None:
                    continue
                for scaled in recipe.scaled_lines(outstanding):
                    gross[scaled["raw_material"].id] += scaled["quantity"]

    if include_forecasts:
        from .models import DemandForecast
        forecasts = DemandForecast.objects.filter(
            period_end__lte=horizon,
        ).select_related("product")
        for f in forecasts:
            from formulation.models import Recipe
            recipe = Recipe.objects.filter(
                product=f.product, is_active=True,
            ).first()
            if recipe is None:
                continue
            for scaled in recipe.scaled_lines(f.quantity):
                gross[scaled["raw_material"].id] += scaled["quantity"]

    return gross


def _on_hand_quantity(rm_id: int) -> Decimal:
    return RawMaterialLot.objects.filter(
        raw_material_id=rm_id,
        qc_status=RawMaterialLot.QCStatus.RELEASED,
        remaining_qty__gt=0,
    ).aggregate(t=Sum("remaining_qty"))["t"] or ZERO


def _on_order_quantity(rm_id: int) -> Decimal:
    """Açık PO'lardaki bekleyen miktar (received_qty < quantity)."""
    return PurchaseOrderLine.objects.filter(
        raw_material_id=rm_id,
        po__status__in=[
            PurchaseOrder.Status.OPEN, PurchaseOrder.Status.PARTIAL,
            PurchaseOrder.Status.DRAFT,
        ],
    ).aggregate(t=Sum("quantity") - Sum("received_qty"))["t"] or ZERO


@transaction.atomic
def run_mrp(
    *,
    run_number: str,
    horizon_date: dt.date,
    executed_by,
    include_forecasts: bool = True,
    include_sales_orders: bool = True,
    include_production_orders: bool = True,
) -> MRPRun:
    """Bir MRP koşusu çalıştırır — brüt, mevcut, açık PO, net ihtiyaç yazılır.

    Reorder önerisi: net > 0 ise `suggested_order_qty = net` (basit yaklaşım).
    """
    run = MRPRun.objects.create(
        run_number=run_number, horizon_date=horizon_date,
        include_forecasts=include_forecasts,
        include_open_sales_orders=include_sales_orders,
        include_planned_production_orders=include_production_orders,
        executed_by=executed_by,
    )
    gross = _compute_gross_requirements(
        horizon=horizon_date,
        include_forecasts=include_forecasts,
        include_sales_orders=include_sales_orders,
        include_production_orders=include_production_orders,
    )

    for rm in RawMaterial.objects.filter(is_active=True):
        g = gross.get(rm.id, ZERO)
        on_hand = _on_hand_quantity(rm.id)
        on_order = _on_order_quantity(rm.id)
        net = max(ZERO, g - on_hand - on_order)
        if net > 0:
            status = MaterialRequirement.Status.SHORTAGE
        elif g > 0 and on_hand < g:
            status = MaterialRequirement.Status.REORDER
        else:
            status = MaterialRequirement.Status.OK

        MaterialRequirement.objects.create(
            run=run, raw_material=rm,
            gross_requirement=g, on_hand=on_hand, on_order=on_order,
            net_requirement=net,
            suggested_order_qty=net,
            status=status,
        )
    return run


@transaction.atomic
def create_requisitions_from_mrp(
    run: MRPRun, *, requested_by, needed_by: dt.date | None = None
) -> list[PurchaseRequisition]:
    """MRP koşusundaki eksikler için PurchaseRequisition üretir (SHORTAGE)."""
    reqs: list[PurchaseRequisition] = []
    needed_by = needed_by or run.horizon_date
    for r in run.requirements.filter(
        status=MaterialRequirement.Status.SHORTAGE,
        suggested_order_qty__gt=0,
    ).select_related("raw_material"):
        req = PurchaseRequisition.objects.create(
            requisition_number=f"PR-{run.run_number}-{r.raw_material.code}",
            raw_material=r.raw_material,
            quantity=r.suggested_order_qty,
            needed_by=needed_by,
            source_mrp=run,
            requested_by=requested_by,
            status=PurchaseRequisition.Status.SUBMITTED,
            justification=f"MRP {run.run_number} eksik: {r.net_requirement}",
        )
        reqs.append(req)
    return reqs


@transaction.atomic
def approve_requisition(req: PurchaseRequisition, *, approver) -> PurchaseRequisition:
    from django.utils import timezone
    if req.status not in {PurchaseRequisition.Status.SUBMITTED,
                          PurchaseRequisition.Status.DRAFT}:
        raise ValidationError("Yalnız SUBMITTED/DRAFT talep onaylanabilir.")
    req.status = PurchaseRequisition.Status.APPROVED
    req.approved_by = approver
    req.approved_at = timezone.now()
    req.save(update_fields=[
        "status", "approved_by", "approved_at", "updated_at",
    ])
    return req
