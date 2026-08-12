"""Faz B tests — MCOS Rol Refactor: 6 yeni rol + D1-D4 + Veto."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command

from iam.models import Role
from portal.models import ApprovalRequest
from portal.services import approve, request_approval, veto


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Rol tanımları
# ---------------------------------------------------------------------------

class TestRoleDefinitions:
    def test_role_all_has_16_entries(self):
        assert len(Role.ALL) == 16

    def test_new_roles_present(self):
        for r in ("RDT_ENGINEER", "MLTS_ANALYST", "HSE_OFFICER",
                  "INTERNAL_AUDITOR", "MAINTENANCE_TECH", "COMMERCIAL_ENG"):
            assert r in Role.ALL
            assert r in Role.LABELS
            assert r in Role.MCOS_FUNCTION
            assert r in Role.DEFAULT_DECISION_LEVEL

    def test_mcos_function_mapping_covers_all_roles(self):
        # Her rol bir MCOS fonksiyonuna eşleşmeli
        assert set(Role.MCOS_FUNCTION.keys()) == set(Role.ALL)

    def test_hse_officer_is_veto_holder(self):
        assert Role.is_veto_holder(Role.HSE_OFFICER)

    def test_ims_qa_manager_is_veto_holder(self):
        assert Role.is_veto_holder(Role.IMS_QA_MANAGER)

    def test_purchasing_is_not_veto_holder(self):
        assert not Role.is_veto_holder(Role.PURCHASING)

    def test_seed_roles_creates_all_16(self):
        call_command("seed_roles")
        assert Group.objects.filter(name__in=Role.ALL).count() == 16


# ---------------------------------------------------------------------------
# Karar seviyesi (D1-D4)
# ---------------------------------------------------------------------------

class TestDecisionLevel:
    def test_gm_can_decide_at_d4(self, db):
        call_command("seed_roles")
        u = User.objects.create_user("gm", password="pw")
        u.groups.add(Group.objects.get(name=Role.GENERAL_MANAGER))
        assert Role.user_can_decide_at(u, "D4") is True

    def test_warehouse_cannot_decide_at_d3(self, db):
        call_command("seed_roles")
        u = User.objects.create_user("wh", password="pw")
        u.groups.add(Group.objects.get(name=Role.WAREHOUSE))
        assert Role.user_can_decide_at(u, "D3") is False

    def test_ims_manager_can_decide_at_d3_but_not_d4(self, db):
        call_command("seed_roles")
        u = User.objects.create_user("qa", password="pw")
        u.groups.add(Group.objects.get(name=Role.IMS_QA_MANAGER))
        assert Role.user_can_decide_at(u, "D3") is True
        assert Role.user_can_decide_at(u, "D4") is False

    def test_superuser_can_decide_at_any_level(self, db):
        su = User.objects.create_superuser("root", email="", password="pw")
        for lvl in ("D1", "D2", "D3", "D4"):
            assert Role.user_can_decide_at(su, lvl) is True


# ---------------------------------------------------------------------------
# Approval — decision_level enforce
# ---------------------------------------------------------------------------

def _make_approval(*, requester, required_role: str, decision_level: str,
                    veto_role: str = "") -> ApprovalRequest:
    """Onay talebi için target olarak requester'ın kendisi (basit fixture)."""
    return request_approval(
        kind=ApprovalRequest.Kind.OTHER,
        target=requester,  # ContentType lookup çalışsın diye User target
        requested_by=requester,
        required_role=required_role,
        title="Test onay talebi",
        description="detay",
        decision_level=decision_level,
        veto_holder_role=veto_role,
    )


class TestApprovalDecisionLevelEnforced:
    def test_warehouse_role_rejected_at_d3(self, db):
        call_command("seed_roles")
        requester = User.objects.create_user("req", password="pw")
        approver = User.objects.create_user("wh", password="pw")
        approver.groups.add(Group.objects.get(name=Role.WAREHOUSE))

        # WAREHOUSE required_role olarak ayarlanır ama D3 talep edilir
        ar = _make_approval(requester=requester,
                             required_role=Role.WAREHOUSE,
                             decision_level="D3")
        with pytest.raises(PermissionDenied):
            approve(ar, user=approver)

    def test_gm_can_approve_at_d4(self, db):
        call_command("seed_roles")
        requester = User.objects.create_user("req2", password="pw")
        approver = User.objects.create_user("gm", password="pw")
        approver.groups.add(Group.objects.get(name=Role.GENERAL_MANAGER))

        ar = _make_approval(requester=requester,
                             required_role=Role.GENERAL_MANAGER,
                             decision_level="D4")
        result = approve(ar, user=approver, reason="ok")
        assert result.status == ApprovalRequest.Status.APPROVED


# ---------------------------------------------------------------------------
# Veto
# ---------------------------------------------------------------------------

class TestVeto:
    def test_veto_by_holder_role_marks_rejected(self, db):
        call_command("seed_roles")
        requester = User.objects.create_user("req3", password="pw")
        veto_user = User.objects.create_user("hse", password="pw")
        veto_user.groups.add(Group.objects.get(name=Role.HSE_OFFICER))

        ar = _make_approval(requester=requester,
                             required_role=Role.OPERATIONS_MANAGER,
                             decision_level="D2",
                             veto_role=Role.HSE_OFFICER)
        veto(ar, user=veto_user, reason="Guvenlik riski")
        ar.refresh_from_db()
        assert ar.status == ApprovalRequest.Status.REJECTED
        assert "VETO" in ar.decision_reason

    def test_veto_by_non_holder_denied(self, db):
        call_command("seed_roles")
        requester = User.objects.create_user("req4", password="pw")
        wh_user = User.objects.create_user("wh2", password="pw")
        wh_user.groups.add(Group.objects.get(name=Role.WAREHOUSE))

        ar = _make_approval(requester=requester,
                             required_role=Role.OPERATIONS_MANAGER,
                             decision_level="D2",
                             veto_role=Role.HSE_OFFICER)
        with pytest.raises(PermissionDenied):
            veto(ar, user=wh_user, reason="X")

    def test_veto_requires_reason(self, db):
        call_command("seed_roles")
        requester = User.objects.create_user("req5", password="pw")
        veto_user = User.objects.create_user("qa2", password="pw")
        veto_user.groups.add(Group.objects.get(name=Role.IMS_QA_MANAGER))

        ar = _make_approval(requester=requester,
                             required_role=Role.OPERATIONS_MANAGER,
                             decision_level="D2",
                             veto_role=Role.IMS_QA_MANAGER)
        with pytest.raises(ValidationError):
            veto(ar, user=veto_user, reason="   ")

    def test_request_approval_rejects_non_veto_holder_role(self, db):
        call_command("seed_roles")
        requester = User.objects.create_user("req6", password="pw")
        # PURCHASING veto listesinde değil — request_approval reddetmeli
        with pytest.raises(ValidationError):
            _make_approval(requester=requester,
                            required_role=Role.OPERATIONS_MANAGER,
                            decision_level="D2",
                            veto_role=Role.PURCHASING)
