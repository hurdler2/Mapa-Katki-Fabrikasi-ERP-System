"""Sprint 4: NCR taksonomi + BR-QA-11 justificatif enforcement."""
from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from qms.models import Nonconformance


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user(username="det1", password="x")


def _make_ncr(user, disposition, proof=None):
    return Nonconformance(
        ncr_number="NCR-TEST-1",
        source=Nonconformance.Source.PRODUCTION,
        severity=Nonconformance.Severity.HIGH if hasattr(Nonconformance, "Severity") else "HIGH",
        detected_at=timezone.now(),
        detected_by=user,
        title="Test NCR",
        description="Test açıklaması",
        disposition=disposition,
        proof_document=proof,
    )


def test_ncr_return_to_supplier_requires_proof(user):
    """BR-QA-11: Retour fournisseur → justificatif zorunlu."""
    ncr = _make_ncr(user, Nonconformance.Disposition.RETURN_TO_SUPPLIER)
    with pytest.raises(ValidationError) as exc:
        ncr.full_clean()
    assert "proof_document" in exc.value.error_dict


def test_ncr_reject_requires_proof(user):
    """BR-QA-11: Rebut → justificatif zorunlu."""
    ncr = _make_ncr(user, Nonconformance.Disposition.REJECT)
    with pytest.raises(ValidationError) as exc:
        ncr.full_clean()
    assert "proof_document" in exc.value.error_dict


def test_ncr_waiver_requires_proof(user):
    """BR-QA-11: Dérogation → justificatif zorunlu."""
    ncr = _make_ncr(user, Nonconformance.Disposition.WAIVER)
    with pytest.raises(ValidationError) as exc:
        ncr.full_clean()
    assert "proof_document" in exc.value.error_dict


def test_ncr_pending_does_not_require_proof(user):
    """PENDING (karar bekliyor) proof gerektirmez."""
    ncr = _make_ncr(user, Nonconformance.Disposition.PENDING)
    ncr.full_clean()  # hata olmamalı


def test_ncr_rework_does_not_require_proof(user):
    """Rework proof gerektirmez."""
    ncr = _make_ncr(user, Nonconformance.Disposition.REWORK)
    ncr.full_clean()


def test_ncr_reject_with_proof_ok(user):
    """Rebut + justificatif → geçerli."""
    proof = SimpleUploadedFile(
        "justificatif.pdf", b"fake pdf content", content_type="application/pdf",
    )
    ncr = _make_ncr(user, Nonconformance.Disposition.REJECT, proof=proof)
    ncr.full_clean()


def test_root_cause_category_enum(user):
    """Root cause 7-choice taksonomi."""
    categories = {c[0] for c in Nonconformance.RootCauseCategory.choices}
    assert "SUPPLIER_QUALITY" in categories
    assert "EQUIPMENT" in categories
    assert "PROCESS_OPERATOR" in categories
    assert "FORMULA_DESIGN" in categories
    assert "MEASUREMENT_ERROR" in categories
    assert "ENVIRONMENTAL" in categories
    assert "OTHER" in categories


def test_gate_enum(user):
    """Gate 3-choice enum: A/B/C."""
    gates = {c[0] for c in Nonconformance.Gate.choices}
    assert gates == {"A", "B", "C"}
