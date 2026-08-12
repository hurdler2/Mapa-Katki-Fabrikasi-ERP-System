"""Dashboard ve rapor view'ları — admin auth zorunlu."""
from __future__ import annotations

import datetime as dt

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from production.models import ProductionBatch

from .services import (
    batch_cost,
    mass_balance,
    production_summary,
    raw_material_consumption,
)


def _parse_range(request: HttpRequest, default_days: int = 30) -> tuple[dt.date, dt.date]:
    today = dt.date.today()
    default_from = today - dt.timedelta(days=default_days)
    try:
        d_from = dt.date.fromisoformat(request.GET.get("from") or "") or default_from
    except ValueError:
        d_from = default_from
    try:
        d_to = dt.date.fromisoformat(request.GET.get("to") or "") or today
    except ValueError:
        d_to = today
    return d_from, d_to


@staff_member_required
def dashboard(request: HttpRequest) -> HttpResponse:
    d_from, d_to = _parse_range(request)
    summary = production_summary(d_from, d_to)
    consumption = raw_material_consumption(d_from, d_to)
    return render(request, "reporting/dashboard.html", {
        "summary": summary,
        "consumption": consumption,
        "date_from": d_from,
        "date_to": d_to,
    })


@staff_member_required
def batch_report(request: HttpRequest, batch_id: int) -> HttpResponse:
    batch = get_object_or_404(ProductionBatch, pk=batch_id)
    return render(request, "reporting/batch_report.html", {
        "batch": batch,
        "cost": batch_cost(batch),
        "balance": mass_balance(batch),
    })
