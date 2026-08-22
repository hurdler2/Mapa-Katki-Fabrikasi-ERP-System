"""Sprint 9: REACH SVHC + EN 480 + FPC audit + DoP testleri."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from chemicals.models import (
    DeclarationOfPerformance,
    FPCAudit,
    NotifiedBody,
    CertificateOfConformity,
    FPCTestPlan,
    AVCPSystem,
)
from masterdata.models import Product, RawMaterial, UnitOfMeasure
from quality.models import QCParameter


pytestmark = pytest.mark.django_db


@pytest.fixture
def uom():
    return UnitOfMeasure.objects.get_or_create(
        code="kg", defaults={"name": "Kilogram"},
    )[0]


@pytest.fixture
def product(uom):
    return Product.objects.create(code="ADX-100", name="Superplasticizer", unit=uom)


def test_rawmaterial_svhc_flag(uom):
    rm = RawMaterial.objects.create(
        code="SVHC-01", name="Test SVHC bileşik", unit=uom,
        svhc_flag=True,
        svhc_pct=Decimal("0.150"),
        reach_registration_no="01-2119471299-27-0001",
        cas_number="9003-01-4",
        ec_number="618-347-7",
    )
    assert rm.svhc_flag is True
    assert rm.svhc_pct == Decimal("0.150")
    assert rm.reach_registration_no.startswith("01-")


def test_rawmaterial_no_svhc_default(uom):
    rm = RawMaterial.objects.create(code="W", name="Su", unit=uom)
    assert rm.svhc_flag is False
    assert rm.svhc_pct is None


def test_qcparameter_en480_method():
    p = QCParameter.objects.create(
        code="CHLORIDE", name="Klorür iyonu",
        unit="%", en480_method_ref="EN 480-10",
    )
    assert p.en480_method_ref == "EN 480-10"


def test_notified_body_creation():
    nb = NotifiedBody.objects.create(
        number="1234", name="CTC Groupe", country="France",
    )
    assert str(nb).startswith("NB 1234")


def test_fpc_audit_lifecycle():
    nb = NotifiedBody.objects.create(number="0987", name="CSTB", country="France")
    audit = FPCAudit.objects.create(
        audit_number="FPC-2026-001",
        notified_body=nb,
        audit_type=FPCAudit.AuditType.INITIAL,
        audit_date=dt.date.today(),
        auditor_name="Jean Dupont",
        scope="Superplasticizer PCE hattı — ADX-100",
        major_nc_count=0,
        minor_nc_count=2,
        observations_count=5,
        outcome=FPCAudit.Outcome.PASSED_WITH_FINDINGS,
        corrective_action_deadline=dt.date.today() + dt.timedelta(days=90),
        certificate_issued=True,
    )
    assert audit.outcome == FPCAudit.Outcome.PASSED_WITH_FINDINGS
    assert audit.certificate_issued is True


def test_declaration_of_performance_creation(product):
    nb = NotifiedBody.objects.create(number="1111", name="Test NB")
    fpc = FPCTestPlan.objects.create(
        product=product, avcp_system=AVCPSystem.SYSTEM_2PLUS,
        notified_body=nb, effective_from=dt.date.today(),
        frequency_per_batch="DENSITY,PH,SOLIDS,CHLORIDE",
    )
    coc = CertificateOfConformity.objects.create(
        coc_number="COC-2026-001",
        product=product, fpc_plan=fpc,
        admixture_type="Superplasticizer PCE",
        ce_marking_year=2026,
        dop_number="DOP-2026-001",
        issue_date=dt.date.today(),
        issuing_body=nb,
    )
    dop = DeclarationOfPerformance.objects.create(
        dop_number="DOP-2026-001",
        product=product,
        coc=coc,
        issue_date=dt.date.today(),
        intended_use="Superplasticizer / High Range Water Reducer",
        performance_data={
            "chloride_ion_content": "<=0.1%",
            "alkali_content": "<=1.5%",
            "water_reduction": ">=12%",
            "compressive_strength_ratio_7d": ">=125%",
            "compressive_strength_ratio_28d": ">=115%",
        },
        manufacturer_signatory="A. Bouzidi, Directeur Général",
        status=DeclarationOfPerformance.Status.ISSUED,
    )
    assert dop.status == DeclarationOfPerformance.Status.ISSUED
    assert dop.performance_data["water_reduction"] == ">=12%"
    assert dop.coc.dop_number == "DOP-2026-001"
