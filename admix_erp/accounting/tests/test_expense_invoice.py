"""Sprint 8: Facture de dépense (gider faturası) testleri."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounting.models import (
    ExpenseInvoice, FiscalYear, Period, TVARate,
)
from masterdata.models import Supplier


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user(username="acc_exp", password="x")


@pytest.fixture
def supplier():
    return Supplier.objects.create(
        code="MECATECH", name="MECATECH SARL Maintenance Industrielle",
    )


@pytest.fixture
def tva():
    return TVARate.objects.create(
        code="TVA19", name="TVA 19", rate_pct=Decimal("19.00"),
    )


@pytest.fixture
def period():
    today = dt.date.today()
    fy = FiscalYear.objects.create(
        year=today.year,
        start_date=dt.date(today.year, 1, 1),
        end_date=dt.date(today.year, 12, 31),
    )
    return Period.objects.create(
        year=today.year, month=today.month, fiscal_year=fy,
        status=Period.Status.OPEN,
    )


def test_expense_invoice_recompute(supplier, tva, period, user):
    exp = ExpenseInvoice.objects.create(
        expense_number="EXP-2026-001",
        supplier=supplier,
        category=ExpenseInvoice.Category.MAINTENANCE,
        invoice_date=dt.date.today(),
        period=period,
        description="Réparation superplastifiant mixer R-101",
        supplier_invoice_number="MECT-2026-4489",
        amount_ht=Decimal("100000.00"),
        tva_rate=tva,
        equipment_reference="Réacteur R-101",
        performed_by=user,
    )
    exp.recompute()
    assert exp.amount_tva == Decimal("19000.00")
    assert exp.amount_ttc == Decimal("119000.00")


def test_expense_default_draft_status(supplier, tva, period, user):
    exp = ExpenseInvoice.objects.create(
        expense_number="EXP-2026-002",
        supplier=supplier,
        category=ExpenseInvoice.Category.UTILITY,
        invoice_date=dt.date.today(),
        period=period,
        description="Elektrik faturası Ağustos 2026",
        amount_ht=Decimal("50000"),
        tva_rate=tva,
        performed_by=user,
    )
    assert exp.status == ExpenseInvoice.Status.DRAFT


def test_expense_categories_available():
    cats = {c[0] for c in ExpenseInvoice.Category.choices}
    assert {"MAINTENANCE", "UTILITY", "RENT", "CONSULTING",
            "TRANSPORT", "CLEANING", "SECURITY", "OFFICE",
            "LEGAL", "MARKETING", "OTHER"}.issubset(cats)


def test_expense_approval_workflow(supplier, tva, period, user):
    approver = get_user_model().objects.create_user(username="dir1", password="x")
    exp = ExpenseInvoice.objects.create(
        expense_number="EXP-2026-003",
        supplier=supplier,
        category=ExpenseInvoice.Category.CONSULTING,
        invoice_date=dt.date.today(),
        period=period,
        description="ISO 9001 danışmanlık",
        amount_ht=Decimal("75000"),
        tva_rate=tva,
        performed_by=user,
    )
    exp.status = ExpenseInvoice.Status.APPROVED
    exp.approved_by = approver
    exp.approved_at = timezone.now()
    exp.save()
    assert exp.status == ExpenseInvoice.Status.APPROVED
    assert exp.approved_by_id == approver.pk
