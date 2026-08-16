"""Faz E tests — 8-Part Gate Model: open/complete/close/reopen + UI."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command

from gates.models import Gate, GateSection
from gates import services as gate_services
from records import services as record_services
from records.models import Case, Decision, Evidence


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def alice(db):
    return User.objects.create_user("alice", password="pw")


@pytest.fixture
def bob(db):
    return User.objects.create_user("bob", password="pw")


@pytest.fixture
def case(alice):
    return record_services.open_case(
        case_id="INCIDENT-G1", family=Case.Family.INCIDENT,
        title="Gate testi", description="detay",
        detected_by=alice, gate="GATE-001",
        severity=Case.Severity.SEV2,
    )


@pytest.fixture
def gate(case, alice):
    return gate_services.open_gate(
        gate_id="GATE-001", case=case, owner=alice,
        scope="8-part gate testi kapsam",
    )


def _complete_all_pass(gate: Gate, reviewer: User, case: Case):
    """8 bölümü de PASS + evidence ile doldur (helper)."""
    for i, section in enumerate(Gate.ALL_SECTIONS, start=1):
        ev = record_services.add_evidence(
            evidence_id=f"EVD-G001-{i:03d}", case=case,
            kind=Evidence.Kind.LOG,
            title=f"section {section} evidence",
            collected_by=reviewer,
        )
        gate_services.complete_section(
            gate, section=section, status=Gate.Status.PASS,
            reviewer=reviewer, evidence=[ev])


def _add_decision(case: Case, decision_maker: User, decision_id="DEC-G1-001"):
    return record_services.record_decision(
        decision_id=decision_id, case=case,
        level=Decision.Level.D3, status=Decision.Status.PASS,
        decision_maker=decision_maker,
        options_considered="A", rationale="B")


# ---------------------------------------------------------------------------
# open_gate — 8 section auto-create
# ---------------------------------------------------------------------------

class TestOpenGate:
    def test_open_gate_creates_row(self, gate):
        assert gate.status == Gate.Status.OPEN

    def test_open_gate_creates_8_sections(self, gate):
        assert gate.sections.count() == 8

    def test_all_sections_start_open(self, gate):
        for gs in gate.sections.all():
            assert gs.completion_status == Gate.Status.OPEN

    def test_gate_id_not_reusable(self, gate, case, alice):
        with pytest.raises(ValidationError):
            gate_services.open_gate(
                gate_id="GATE-001", case=case, owner=alice,
                scope="dup")

    def test_gate_inherits_business_line_from_case(self, case, alice):
        from businessline.models import BusinessLine
        call_command("seed_business_lines")
        mcs = BusinessLine.objects.get(code="MCS")
        case.business_line = mcs
        case.save()
        g = gate_services.open_gate(
            gate_id="GATE-BL-01", case=case, owner=alice, scope="x")
        assert g.business_line == mcs


# ---------------------------------------------------------------------------
# complete_section
# ---------------------------------------------------------------------------

class TestCompleteSection:
    def test_marks_section_pass(self, gate, alice, case):
        ev = record_services.add_evidence(
            evidence_id="EVD-CS-001", case=case,
            kind=Evidence.Kind.LOG, title="x", collected_by=alice)
        gate_services.complete_section(
            gate, section=Gate.Section.OPERATION,
            status=Gate.Status.PASS, reviewer=alice, evidence=[ev])
        gs = gate.sections.get(section=Gate.Section.OPERATION)
        assert gs.completion_status == Gate.Status.PASS
        assert gs.reviewer == alice
        assert gs.reviewed_at is not None
        assert ev in gs.evidence.all()

    def test_gate_status_transitions_to_in_progress(self, gate, alice, case):
        ev = record_services.add_evidence(
            evidence_id="EVD-CS-002", case=case,
            kind=Evidence.Kind.LOG, title="x", collected_by=alice)
        gate_services.complete_section(
            gate, section=Gate.Section.OPERATION,
            status=Gate.Status.PASS, reviewer=alice, evidence=[ev])
        gate.refresh_from_db()
        assert gate.status == Gate.Status.IN_PROGRESS

    def test_invalid_status_rejected(self, gate, alice):
        with pytest.raises(ValidationError):
            gate_services.complete_section(
                gate, section=Gate.Section.OPERATION,
                status="INVALID", reviewer=alice)

    def test_unknown_section_rejected(self, gate, alice):
        with pytest.raises(ValidationError):
            gate_services.complete_section(
                gate, section="NOSUCH_SECTION",
                status=Gate.Status.PASS, reviewer=alice)


# ---------------------------------------------------------------------------
# close_gate — kapama koşulları
# ---------------------------------------------------------------------------

class TestCloseGate:
    def test_cannot_close_without_all_sections_pass(self, gate, alice):
        with pytest.raises(ValidationError):
            gate_services.close_gate(gate, closed_by=alice)

    def test_cannot_close_without_evidence(self, gate, alice, case):
        # Tüm bölümleri PASS et ama evidence bağlama
        for section in Gate.ALL_SECTIONS:
            gate_services.complete_section(
                gate, section=section, status=Gate.Status.PASS,
                reviewer=alice)
        _add_decision(case, alice)
        with pytest.raises(ValidationError):
            gate_services.close_gate(gate, closed_by=alice)

    def test_cannot_close_without_decision(self, gate, alice, case):
        _complete_all_pass(gate, alice, case)
        # Decision yok → kapanamaz
        with pytest.raises(ValidationError):
            gate_services.close_gate(gate, closed_by=alice)

    def test_close_ok_with_all_pass_and_decision(self, gate, alice, case):
        _complete_all_pass(gate, alice, case)
        _add_decision(case, alice)
        gate_services.close_gate(gate, closed_by=alice)
        gate.refresh_from_db()
        assert gate.status == Gate.Status.PASS
        assert gate.closed_at is not None
        assert gate.closed_by == alice

    def test_close_conditional_if_any_section_conditional(self, gate, alice, case):
        # 7 PASS + 1 CONDITIONAL
        for i, section in enumerate(Gate.ALL_SECTIONS, start=1):
            ev = record_services.add_evidence(
                evidence_id=f"EVD-COND-{i:03d}", case=case,
                kind=Evidence.Kind.LOG, title="x", collected_by=alice)
            status = Gate.Status.CONDITIONAL if i == 5 else Gate.Status.PASS
            gate_services.complete_section(
                gate, section=section, status=status,
                reviewer=alice, evidence=[ev])
        _add_decision(case, alice)
        gate_services.close_gate(gate, closed_by=alice)
        gate.refresh_from_db()
        assert gate.status == Gate.Status.CONDITIONAL

    def test_hold_forces_gate_fail(self, gate, alice, case):
        ev = record_services.add_evidence(
            evidence_id="EVD-HOLD-001", case=case,
            kind=Evidence.Kind.LOG, title="x", collected_by=alice)
        gate_services.complete_section(
            gate, section=Gate.Section.OPERATION,
            status=Gate.Status.HOLD, reviewer=alice, evidence=[ev])
        with pytest.raises(ValidationError):
            gate_services.close_gate(gate, closed_by=alice)
        gate.refresh_from_db()
        assert gate.status == Gate.Status.FAIL

    def test_cannot_close_twice(self, gate, alice, case):
        _complete_all_pass(gate, alice, case)
        _add_decision(case, alice)
        gate_services.close_gate(gate, closed_by=alice)
        with pytest.raises(ValidationError):
            gate_services.close_gate(gate, closed_by=alice)


# ---------------------------------------------------------------------------
# reopen_gate
# ---------------------------------------------------------------------------

class TestReopenGate:
    def test_reopen_pass_gate(self, gate, alice, bob, case):
        _complete_all_pass(gate, alice, case)
        _add_decision(case, alice)
        gate_services.close_gate(gate, closed_by=alice)
        gate_services.reopen_gate(
            gate, triggered_by=bob,
            trigger="Yeni celiskili evidence bulundu",
            note="EVD-G001-009 celisik")
        gate.refresh_from_db()
        assert gate.status == Gate.Status.REOPENED
        assert gate.closed_at is None
        assert len(gate.reopen_history) == 1
        assert gate.reopen_history[0]["by_user"] == "bob"
        assert gate.reopen_history[0]["prev_status"] == Gate.Status.PASS

    def test_cannot_reopen_open_gate(self, gate, bob):
        with pytest.raises(ValidationError):
            gate_services.reopen_gate(
                gate, triggered_by=bob, trigger="x")

    def test_reopen_requires_trigger(self, gate, alice, bob, case):
        _complete_all_pass(gate, alice, case)
        _add_decision(case, alice)
        gate_services.close_gate(gate, closed_by=alice)
        with pytest.raises(ValidationError):
            gate_services.reopen_gate(
                gate, triggered_by=bob, trigger="   ")

    def test_reopened_gate_can_be_closed_again(self, gate, alice, bob, case):
        _complete_all_pass(gate, alice, case)
        _add_decision(case, alice)
        gate_services.close_gate(gate, closed_by=alice)
        gate_services.reopen_gate(
            gate, triggered_by=bob, trigger="Yeni kanit")
        # Reopened durumdayken tekrar close_gate çalışmalı
        gate_services.close_gate(gate, closed_by=alice)
        gate.refresh_from_db()
        assert gate.status == Gate.Status.PASS


# ---------------------------------------------------------------------------
# Portal UI
# ---------------------------------------------------------------------------

class TestPortalUI:
    def test_gate_list_requires_login(self, client):
        resp = client.get("/portal/gates/")
        assert resp.status_code in (301, 302)

    def test_gate_list_forbidden_without_perm(self, client):
        User.objects.create_user("nobody", password="pw")
        client.login(username="nobody", password="pw")
        resp = client.get("/portal/gates/")
        assert resp.status_code == 403

    def test_gate_list_ok_for_superuser(self, client, gate):
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/gates/")
        assert resp.status_code == 200
        assert b"GATE-001" in resp.content

    def test_gate_detail_shows_8_sections(self, client, gate):
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get(f"/portal/gates/{gate.gate_id}/")
        assert resp.status_code == 200
        assert b"GATE-001" in resp.content
        # 8 bölümün başlıkları var mı?
        for label in (b"Operation", b"IMS Engine", b"Decision Architecture",
                      b"Objective Evidence", b"Management Review",
                      b"Lessons Learned", b"IMS Improvement", b"Gate Status"):
            assert label in resp.content

    def test_gate_detail_404(self, client):
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/gates/NOSUCH/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Rol matrisi
# ---------------------------------------------------------------------------

class TestRoleMatrix:
    def test_ims_qa_manager_sees_gates_menu(self):
        from portal.menu import filter_menu_for
        from iam.models import Role
        call_command("seed_roles")
        u = User.objects.create_user("qa", password="pw")
        u.groups.add(Group.objects.get(name=Role.IMS_QA_MANAGER))
        sections = filter_menu_for(u)
        labels = [item["label"] for s in sections for item in s["items"]]
        assert "8-Part Gate'ler" in labels

    def test_warehouse_role_cannot_see_gates_menu(self):
        from portal.menu import filter_menu_for
        from iam.models import Role
        call_command("seed_roles")
        u = User.objects.create_user("wh", password="pw")
        u.groups.add(Group.objects.get(name=Role.WAREHOUSE))
        sections = filter_menu_for(u)
        labels = [item["label"] for s in sections for item in s["items"]]
        assert "8-Part Gate'ler" not in labels
