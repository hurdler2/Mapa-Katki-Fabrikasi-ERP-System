"""Sprint 10: TrialBatch + MixDesign + ApplicatorTraining + Warranty + CustomerSiteTest."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from masterdata.models import Customer, Product, UnitOfMeasure
from quality.models import CustomerSiteTest
from sales.models import (
    ApplicatorTraining, MixDesignConsultation, PerformanceWarranty,
    TrialBatch,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user(username="sup1", password="x")


@pytest.fixture
def uom():
    return UnitOfMeasure.objects.get_or_create(
        code="kg", defaults={"name": "Kilogram"},
    )[0]


@pytest.fixture
def customer():
    return Customer.objects.create(code="C-TRIAL-1", name="Beton Cezayir Test")


@pytest.fixture
def product(uom):
    return Product.objects.create(code="ADX-A", name="Test superplasticizer", unit=uom)


def test_trial_batch_lifecycle(customer, product, uom, user):
    trial = TrialBatch.objects.create(
        trial_number="TRL-2026-001",
        customer=customer, product=product,
        trial_date=dt.date.today(),
        sample_quantity=Decimal("25.00"), unit=uom,
        site_address="Chantier autoroute Sétif-Constantine",
        customer_cement_brand="Ciments d'Algérie CEM I",
        customer_cement_class="CEM I 42.5 R",
        target_slump="S4 (160-210 mm)",
        target_wc_ratio=Decimal("0.450"),
        dosage_pct=Decimal("1.200"),
        performed_by=user,
    )
    assert trial.status == TrialBatch.Status.PLANNED
    trial.initial_slump = "180"
    trial.slump_30min = "170"
    trial.slump_60min = "155"
    trial.slump_90min = "140"
    trial.site_temperature = "32"
    trial.status = TrialBatch.Status.SUCCESS
    trial.save()
    assert trial.status == TrialBatch.Status.SUCCESS


def test_mix_design_consultation(customer, user):
    mdc = MixDesignConsultation.objects.create(
        consultation_number="MDC-2026-001",
        customer=customer, request_date=dt.date.today(),
        project_name="Baraj enjeksiyon karışımı - Béjaïa",
        concrete_class_target="C40/50",
        special_requirements="Sıcak iklim + deniz suyu maruziyeti",
        consultant=user,
        proposed_products="ADX-A + ADX-B",
        proposed_dosage="ADX-A: 1.2% · ADX-B: 0.3%",
    )
    assert mdc.status == MixDesignConsultation.Status.REQUESTED


def test_applicator_training(customer, user):
    at = ApplicatorTraining.objects.create(
        training_number="ATR-2026-001",
        customer=customer, training_date=dt.date.today(),
        location="Chantier Cimenterie Blida",
        topics="Dozaj kalibrasyonu, slump yönetimi, güvenlik prosedürleri",
        products_covered="ADX-A, ADX-B",
        participant_count=12,
        participant_list="A. Belaidi · Foreman\nM. Boudjelal · Operator\nK. Djellal · QC",
        trainer=user,
        duration_hours=Decimal("6.5"),
        certificate_issued=True,
        feedback_score=Decimal("4.7"),
    )
    assert at.participant_count == 12
    assert at.certificate_issued is True


def test_performance_warranty(customer, product, uom, user):
    w = PerformanceWarranty.objects.create(
        warranty_number="WAR-2026-001",
        customer=customer, product=product,
        project_name="Otoyol köprüsü Sétif",
        project_location="Autoroute Est-Ouest, Sétif",
        quantity_supplied=Decimal("15000.00"), unit=uom,
        warranty_start=dt.date.today(),
        warranty_end=dt.date.today() + dt.timedelta(days=25*365),
        coverage_summary="25 yıl dayanıklılık — doğru dosaj koşullarında.",
        signed_by=user,
    )
    assert w.status == PerformanceWarranty.Status.ACTIVE


def test_customer_site_test():
    t = CustomerSiteTest.objects.create(
        test_number="CST-2026-001",
        project_name="Otoyol köprüsü Sétif",
        site_location="Autoroute Sétif",
        test_date=dt.date.today(),
        test_type=CustomerSiteTest.TestType.CUBE_28,
        measured_value=Decimal("42.50"),
        unit="MPa",
        target_value=Decimal("40.00"),
        verdict=CustomerSiteTest.Verdict.PASS,
        tested_by="Lab Central Alger",
    )
    assert t.verdict == CustomerSiteTest.Verdict.PASS
    assert t.measured_value >= t.target_value
