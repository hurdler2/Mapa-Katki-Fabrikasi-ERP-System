"""IAM testleri: rol seed, e-imza doğrulama, yetki kontrolü."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command

from iam.models import ESignature, Role
from iam.services import sign, signatures_for, user_has_role


pytestmark = pytest.mark.django_db


def test_seed_roles_creates_all_groups():
    call_command("seed_roles")
    for role in Role.ALL:
        assert Group.objects.filter(name=role).exists()


def test_seed_roles_idempotent():
    call_command("seed_roles")
    call_command("seed_roles")
    assert Group.objects.filter(name__in=Role.ALL).count() == len(Role.ALL)


def test_user_has_role():
    call_command("seed_roles")
    user = User.objects.create_user("alice", password="pw")
    qa = Group.objects.get(name=Role.IMS_QA_MANAGER)
    user.groups.add(qa)
    assert user_has_role(user, Role.IMS_QA_MANAGER)
    assert not user_has_role(user, Role.OPERATIONS_SUPERVISOR)
    assert user_has_role(user, Role.OPERATIONS_SUPERVISOR, Role.IMS_QA_MANAGER)


def test_superuser_bypasses_role_check():
    su = User.objects.create_superuser("root", password="pw")
    assert user_has_role(su, Role.IMS_QA_MANAGER)


def test_sign_requires_correct_password():
    user = User.objects.create_user("bob", password="secret123")
    target = User.objects.create_user("dummy_target", password="x")

    with pytest.raises(PermissionDenied):
        sign(user=user, target=target, meaning=ESignature.Meaning.APPROVED,
             reason="Test", password="wrong")

    sig = sign(user=user, target=target, meaning=ESignature.Meaning.APPROVED,
               reason="Test onay", password="secret123")
    assert sig.pk is not None
    assert sig.reason == "Test onay"


def test_sign_requires_reason():
    user = User.objects.create_user("carol", password="pw")
    target = User.objects.create_user("d2", password="x")
    with pytest.raises(ValidationError):
        sign(user=user, target=target, meaning=ESignature.Meaning.SIGNED_OFF,
             reason="", password="pw")


def test_signatures_for_returns_all():
    user = User.objects.create_user("dan", password="pw")
    target = User.objects.create_user("d3", password="x")
    sign(user=user, target=target, meaning=ESignature.Meaning.REVIEWED,
         reason="R1", password="pw")
    sign(user=user, target=target, meaning=ESignature.Meaning.APPROVED,
         reason="A1", password="pw")
    sigs = list(signatures_for(target))
    assert len(sigs) == 2
    assert [s.meaning for s in sigs] == ["REVIEWED", "APPROVED"]
