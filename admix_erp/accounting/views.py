"""Mizan (Balance) ve Büyük Defter (Grand Livre) sayfaları."""
from __future__ import annotations

import datetime as dt

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Account
from .services import general_ledger, trial_balance


def _parse_range(request: HttpRequest):
    today = dt.date.today()
    default_from = today.replace(month=1, day=1)
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
def trial_balance_view(request: HttpRequest) -> HttpResponse:
    d_from, d_to = _parse_range(request)
    balance = trial_balance(date_from=d_from, date_to=d_to)
    return render(request, "accounting/trial_balance.html", {
        "balance": balance, "date_from": d_from, "date_to": d_to,
    })


@staff_member_required
def ledger_view(request: HttpRequest, account_id: int) -> HttpResponse:
    account = get_object_or_404(Account, pk=account_id)
    d_from, d_to = _parse_range(request)
    ledger = general_ledger(account, date_from=d_from, date_to=d_to)
    return render(request, "accounting/general_ledger.html", {
        "account": account, "ledger": ledger,
        "date_from": d_from, "date_to": d_to,
    })
