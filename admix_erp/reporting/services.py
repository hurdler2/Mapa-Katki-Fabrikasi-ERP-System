"""Raporlama servisleri: parti maliyeti, fire, dönem özeti."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Iterable

from django.db.models import Count, Q, Sum

from production.models import MaterialConsumption, ProductionBatch


ZERO = Decimal("0")
Q4 = Decimal("0.0001")
Q2 = Decimal("0.01")


def batch_cost(batch: ProductionBatch) -> dict:
    """Bir üretim partisinin maliyet dökümü.

    Toplam malzeme maliyeti = Σ (actual_weight × lot.unit_cost).
    Yalnız actual_weight ve lot dolu tüketimler sayılır (dozajlanmış olanlar).
    kg başına maliyet: actual_qty varsa onunla, yoksa target_qty ile hesaplanır.
    Fire: target_qty - actual_qty (actual_qty varsa).
    """
    total_cost = ZERO
    lines: list[dict] = []
    consumptions = batch.consumptions.select_related("raw_material", "lot").all()

    for c in consumptions:
        actual = c.actual_weight or ZERO
        unit_cost = (c.lot.unit_cost if c.lot else ZERO) or ZERO
        line_cost = (actual * unit_cost).quantize(Q4)
        total_cost += line_cost
        lines.append({
            "raw_material": c.raw_material.code,
            "lot_number": c.lot.lot_number if c.lot else None,
            "actual_weight": actual,
            "unit_cost": unit_cost,
            "line_cost": line_cost,
        })

    output_qty = batch.actual_qty or batch.target_qty
    per_kg = (total_cost / output_qty).quantize(Q4) if output_qty and output_qty > 0 else None

    waste_qty = None
    waste_pct = None
    if batch.actual_qty is not None and batch.target_qty:
        waste_qty = (batch.target_qty - batch.actual_qty).quantize(Q4)
        if batch.target_qty > 0:
            waste_pct = (waste_qty / batch.target_qty * Decimal("100")).quantize(Q2)

    return {
        "batch_id": batch.pk,
        "batch_number": batch.batch_number,
        "product": batch.recipe.product.code,
        "target_qty": batch.target_qty,
        "actual_qty": batch.actual_qty,
        "output_qty": output_qty,
        "total_cost": total_cost.quantize(Q4),
        "per_kg_cost": per_kg,
        "waste_qty": waste_qty,
        "waste_pct": waste_pct,
        "lines": lines,
    }


def mass_balance(batch: ProductionBatch) -> dict:
    """Kütle dengesi: Σ actual_weight vs actual_qty. Sapma raporlanır."""
    total_input = batch.consumptions.aggregate(
        total=Sum("actual_weight")
    )["total"] or ZERO
    actual_out = batch.actual_qty or ZERO
    delta = (actual_out - total_input).quantize(Q4) if total_input else None
    delta_pct = None
    if total_input and total_input > 0:
        delta_pct = ((actual_out - total_input) / total_input * Decimal("100")).quantize(Q2)
    return {
        "batch_number": batch.batch_number,
        "total_input": total_input,
        "actual_output": actual_out,
        "delta": delta,
        "delta_pct": delta_pct,
    }


def production_summary(
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> dict:
    """Dönem özeti: üretilen parti sayısı, toplam çıktı, ort. birim maliyet, top fire."""
    qs = ProductionBatch.objects.all()
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        # UTC vs. yerel TZ cutoff farkını tampon için +1 gün ekle
        qs = qs.filter(created_at__date__lte=date_to + dt.timedelta(days=1))

    total_batches = qs.count()
    status_counts = dict(
        qs.values_list("status").annotate(n=Count("id")).values_list("status", "n")
    )
    total_target = qs.aggregate(t=Sum("target_qty"))["t"] or ZERO
    total_actual = qs.aggregate(t=Sum("actual_qty"))["t"] or ZERO

    # Her parti için batch_cost hesapla (küçük N için OK; büyük N için materialize gerekir)
    per_batch: list[dict] = []
    total_cost = ZERO
    for b in qs.select_related("recipe__product")[:500]:
        bc = batch_cost(b)
        per_batch.append(bc)
        total_cost += bc["total_cost"] or ZERO

    avg_per_kg = None
    if total_actual and total_actual > 0:
        avg_per_kg = (total_cost / total_actual).quantize(Q4)

    # En yüksek fireli 5 parti
    top_waste = sorted(
        [b for b in per_batch if b["waste_pct"] is not None],
        key=lambda x: x["waste_pct"], reverse=True,
    )[:5]

    return {
        "date_from": date_from,
        "date_to": date_to,
        "total_batches": total_batches,
        "status_counts": status_counts,
        "total_target_qty": total_target,
        "total_actual_qty": total_actual,
        "total_cost": total_cost.quantize(Q4),
        "avg_per_kg_cost": avg_per_kg,
        "top_waste": top_waste,
        "batches": per_batch,
    }


def raw_material_consumption(
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> list[dict]:
    """Hammadde başına toplam tüketim (dönemli)."""
    qs = MaterialConsumption.objects.filter(actual_weight__isnull=False)
    if date_from:
        qs = qs.filter(dosed_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(dosed_at__date__lte=date_to)

    grouped = (
        qs.values("raw_material__code", "raw_material__name")
        .annotate(total=Sum("actual_weight"), n_batches=Count("batch", distinct=True))
        .order_by("-total")
    )
    return [
        {
            "raw_material": g["raw_material__code"],
            "name": g["raw_material__name"],
            "total_weight": g["total"] or ZERO,
            "n_batches": g["n_batches"],
        }
        for g in grouped
    ]
