"""Doküman kontrol testleri: onay zinciri, görev ayrımı, yürürlüğe alma."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from docs.models import ControlledDocument, DocumentCategory, DocumentRevision
from docs.services import (
    acknowledge,
    approve_revision,
    make_effective,
    review_revision,
    submit_for_review,
    withdraw,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def users(db):
    return {
        "author": User.objects.create_user("author", password="pw"),
        "reviewer": User.objects.create_user("reviewer", password="pw"),
        "approver": User.objects.create_user("approver", password="pw"),
        "reader": User.objects.create_user("reader", password="pw"),
    }


@pytest.fixture
def doc(users):
    cat = DocumentCategory.objects.create(code="SOP", name="Standart Prosedür", prefix="SOP")
    return ControlledDocument.objects.create(
        document_number="SOP-001", title="Reçete Yönetimi",
        category=cat, process_owner=users["author"],
    )


def test_full_approval_workflow(users, doc):
    rev = DocumentRevision.objects.create(
        document=doc, revision="01", prepared_by=users["author"],
        change_summary="İlk versiyon",
    )
    submit_for_review(rev)
    review_revision(rev, reviewer=users["reviewer"])
    approve_revision(rev, approver=users["approver"])
    make_effective(rev)
    rev.refresh_from_db()
    assert rev.status == DocumentRevision.Status.EFFECTIVE
    assert rev.effective_date is not None


def test_segregation_of_duties_review(users, doc):
    rev = DocumentRevision.objects.create(
        document=doc, revision="01", prepared_by=users["author"],
        change_summary="İlk",
    )
    submit_for_review(rev)
    with pytest.raises(ValidationError):
        review_revision(rev, reviewer=users["author"])


def test_segregation_of_duties_approver(users, doc):
    rev = DocumentRevision.objects.create(
        document=doc, revision="01", prepared_by=users["author"],
        change_summary="İlk",
    )
    submit_for_review(rev)
    review_revision(rev, reviewer=users["reviewer"])
    with pytest.raises(ValidationError):
        approve_revision(rev, approver=users["author"])
    with pytest.raises(ValidationError):
        approve_revision(rev, approver=users["reviewer"])


def test_make_effective_supersedes_previous(users, doc):
    r1 = DocumentRevision.objects.create(
        document=doc, revision="01", prepared_by=users["author"],
        change_summary="v1", status=DocumentRevision.Status.EFFECTIVE,
    )
    r2 = DocumentRevision.objects.create(
        document=doc, revision="02", prepared_by=users["author"],
        change_summary="v2",
    )
    submit_for_review(r2)
    review_revision(r2, reviewer=users["reviewer"])
    approve_revision(r2, approver=users["approver"])
    make_effective(r2)
    r1.refresh_from_db()
    assert r1.status == DocumentRevision.Status.SUPERSEDED


def test_acknowledge_only_effective(users, doc):
    r = DocumentRevision.objects.create(
        document=doc, revision="01", prepared_by=users["author"],
        change_summary="v1",
    )
    with pytest.raises(ValidationError):
        acknowledge(r, user=users["reader"])
    r.status = DocumentRevision.Status.EFFECTIVE
    r.save()
    ack = acknowledge(r, user=users["reader"])
    assert ack.pk is not None
