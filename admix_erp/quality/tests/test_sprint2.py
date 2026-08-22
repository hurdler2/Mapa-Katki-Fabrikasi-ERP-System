"""Sprint 2 UsineERP paritesi: spec versiyonlama + QA onayı + per-Gate + is_critical
+ spec_locked (BR-QA-04) + SamplingPlan (BR-QA-12) + precision."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from quality.models import QCParameter, QCSpec, QCTestResult, SamplingPlan


pytestmark = pytest.mark.django_db


@pytest.fixture
def user_qa():
    User = get_user_model()
    return User.objects.create_user(username="qa1", password="x")


@pytest.fixture
def batch(order):
    from production.services import create_batch_from_order
    return create_batch_from_order(order, batch_number="B-SPRINT2-001")


@pytest.fixture
def ph_param():
    return QCParameter.objects.create(code="PH", name="pH", unit="", decimal_precision=1)


@pytest.fixture
def viscosity_param():
    return QCParameter.objects.create(
        code="VISC", name="Viskozite", unit="cP", decimal_precision=2,
    )


def test_qcparameter_decimal_precision_default():
    p = QCParameter.objects.create(code="X", name="X")
    assert p.decimal_precision == 2


def test_qcparameter_precision_stored(ph_param):
    assert ph_param.decimal_precision == 1


def test_spec_versioning_two_versions_same_product_ok(product, ph_param, user_qa):
    """Aynı ürün+parametreye iki farklı versiyon problem çıkarmamalı."""
    QCSpec.objects.create(
        parameter=ph_param, product=product, version=1,
        min_value=Decimal("4"), max_value=Decimal("7"),
        is_active=False,
    )
    QCSpec.objects.create(
        parameter=ph_param, product=product, version=2,
        min_value=Decimal("5"), max_value=Decimal("8"),
        is_active=False,
    )
    assert QCSpec.objects.filter(product=product, parameter=ph_param).count() == 2


def test_spec_versioning_duplicate_version_blocked(product, ph_param):
    """Aynı parameter+product+version kombinasyonu tekli olmalı."""
    QCSpec.objects.create(
        parameter=ph_param, product=product, version=1,
        min_value=Decimal("4"), max_value=Decimal("7"),
        is_active=False,
    )
    with pytest.raises(IntegrityError):
        QCSpec.objects.create(
            parameter=ph_param, product=product, version=1,
            min_value=Decimal("5"), max_value=Decimal("8"),
            is_active=False,
        )


def test_spec_only_one_active_per_parameter_product(product, ph_param, user_qa):
    """Aynı ürün+parametrede AKTİF spec yalnız 1 tane olabilir."""
    QCSpec.objects.create(
        parameter=ph_param, product=product, version=1,
        min_value=Decimal("4"), max_value=Decimal("7"),
        is_active=True, approved_by=user_qa,
    )
    with pytest.raises(IntegrityError):
        QCSpec.objects.create(
            parameter=ph_param, product=product, version=2,
            min_value=Decimal("5"), max_value=Decimal("8"),
            is_active=True, approved_by=user_qa,
        )


def test_active_spec_requires_qa_approval(product, ph_param):
    """Aktif spec, approved_by dolu olmadan clean() sırasında hata vermeli."""
    s = QCSpec(
        parameter=ph_param, product=product, version=1,
        min_value=Decimal("4"), max_value=Decimal("7"),
        is_active=True, approved_by=None,
    )
    with pytest.raises(ValidationError):
        s.full_clean()


def test_active_spec_with_qa_ok(product, ph_param, user_qa):
    """QA imzası dolu ise aktifleşebilir."""
    s = QCSpec(
        parameter=ph_param, product=product, version=1,
        min_value=Decimal("4"), max_value=Decimal("7"),
        is_active=True, approved_by=user_qa,
    )
    s.full_clean()  # ValidationError atmamalı


def test_spec_per_gate_flags(product, ph_param, user_qa):
    s = QCSpec.objects.create(
        parameter=ph_param, product=product, version=1,
        min_value=Decimal("4"), max_value=Decimal("7"),
        check_at_gate_a=True, check_at_gate_c=True,
        is_critical=True,
        is_active=True, approved_by=user_qa,
    )
    assert s.check_at_gate_a is True
    assert s.check_at_gate_b is False
    assert s.check_at_gate_c is True
    assert s.is_critical is True


def test_qctestresult_spec_locked(product, ph_param, batch, user_qa):
    """BR-QA-04: numune sonucu, o an aktif spec'i FK ile kilitler."""
    spec_v1 = QCSpec.objects.create(
        parameter=ph_param, product=product, version=1,
        min_value=Decimal("4"), max_value=Decimal("7"),
        is_active=True, approved_by=user_qa,
    )
    result = QCTestResult.objects.create(
        parameter=ph_param, batch=batch, value=Decimal("5.5"),
        gate="C", spec_locked=spec_v1,
    )
    # Spec değişse bile result eski spec'e bağlı kalmalı
    spec_v1.is_active = False
    spec_v1.save()
    spec_v2 = QCSpec.objects.create(
        parameter=ph_param, product=product, version=2,
        min_value=Decimal("5"), max_value=Decimal("8"),
        is_active=True, approved_by=user_qa,
    )
    result.refresh_from_db()
    assert result.spec_locked_id == spec_v1.pk
    assert result.spec_locked.version == 1


# --- SamplingPlan (BR-QA-12) ------------------------------------------------

def test_sampling_plan_needs_rm_or_product(product):
    """Ne raw_material ne product yoksa constraint patlamalı."""
    with pytest.raises(IntegrityError):
        SamplingPlan.objects.create(
            code="SP-X", name="Boş", gate="A", trigger="on_receipt",
            frequency_n=1, sample_size_rule="1",
        )


def test_sampling_plan_active_ok(product):
    plan = SamplingPlan.objects.create(
        code="SP-PF-01", name="PF her batch", product=product,
        gate="C", trigger="per_batch", frequency_n=1,
        sample_size_rule="1 numune / batch", is_active=True,
    )
    plan.full_clean()
    assert plan.is_active


def test_sampling_plan_deactivation_requires_reason(product):
    """BR-QA-12: pasifleştirmek için sebep zorunlu."""
    plan = SamplingPlan(
        code="SP-PF-02", name="Test", product=product,
        gate="A", trigger="on_receipt", frequency_n=5,
        sample_size_rule="sqrt(N)+1", is_active=False,
        deactivation_reason="",
    )
    with pytest.raises(ValidationError):
        plan.full_clean()


def test_sampling_plan_deactivation_with_reason_ok(product):
    plan = SamplingPlan(
        code="SP-PF-03", name="Test", product=product,
        gate="A", trigger="on_receipt", frequency_n=5,
        sample_size_rule="sqrt(N)+1", is_active=False,
        deactivation_reason="Metot değiştiği için yeni plan devreye alındı.",
    )
    plan.full_clean()  # hata olmamalı
