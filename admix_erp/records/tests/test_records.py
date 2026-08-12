"""Faz D tests — 5-Katman ID Modeli: Case/RecordInstance/Evidence/Decision/Sign."""
from __future__ import annotations

import datetime as dt
import io

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.utils import timezone

from records.models import (
    Case,
    Decision,
    DecisionSignature,
    Evidence,
    RecordInstance,
)
from records import services
from registry.models import ControlledCode


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def alice(db):
    return User.objects.create_user("alice", password="pw", email="a@x.com")


@pytest.fixture
def bob(db):
    return User.objects.create_user("bob", password="pw", email="b@x.com")


@pytest.fixture
def carol(db):
    return User.objects.create_user("carol", password="pw", email="c@x.com")


@pytest.fixture
def code(db):
    return ControlledCode.objects.create(
        full_code="MAPA-IMS-FRM-NCR-001",
        title="NCR Formu",
        type=ControlledCode.Type.FRM,
        level=ControlledCode.Level.L4,
        function=ControlledCode.Function.IMS,
        owner_role="QA/IMS Manager",
        activation_gate="SOP+egitim",
        objective_evidence_rule="Bos sablon evidence degildir",
    )


@pytest.fixture
def case(alice):
    return services.open_case(
        case_id="INCIDENT-001",
        family=Case.Family.INCIDENT,
        title="Reaktor uc sicaklik anomalisi",
        description="T4 recovery gerekli.",
        detected_by=alice,
        severity=Case.Severity.SEV2,
        gate="GATE-001",
    )


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------

class TestCase:
    def test_open_case_creates_row(self, alice):
        c = services.open_case(
            case_id="INCIDENT-100", family=Case.Family.INCIDENT,
            title="X", description="Y", detected_by=alice)
        assert c.pk is not None
        assert c.status == Case.Status.OPEN

    def test_case_id_is_unique_and_not_reusable(self, alice):
        services.open_case(case_id="INCIDENT-101", family=Case.Family.INCIDENT,
                           title="X", description="Y", detected_by=alice)
        with pytest.raises(ValidationError):
            services.open_case(case_id="INCIDENT-101",
                               family=Case.Family.INCIDENT,
                               title="X2", description="Y2", detected_by=alice)

    def test_mark_case_phase_sets_timestamps(self, case):
        services.mark_case_phase(case, "T1")
        case.refresh_from_db()
        assert case.contained_at is not None
        assert case.status == Case.Status.INVESTIGATING

    def test_mark_case_phase_close_sets_closed_status(self, case):
        services.mark_case_phase(case, "CLOSED")
        case.refresh_from_db()
        assert case.closed_at is not None
        assert case.status == Case.Status.CLOSED

    def test_mark_case_phase_invalid_raises(self, case):
        with pytest.raises(ValidationError):
            services.mark_case_phase(case, "TX")

    def test_case_history_tracks_status(self, case):
        case.status = Case.Status.INVESTIGATING
        case.save()
        assert case.history.count() >= 2


# ---------------------------------------------------------------------------
# RecordInstance + SoD
# ---------------------------------------------------------------------------

class TestRecordInstance:
    def test_create_record_working_status(self, code, case, alice):
        r = services.create_record(
            record_id="NCR-G001-001", controlled_code=code,
            case=case, preparer=alice)
        assert r.status == RecordInstance.Status.WORKING
        assert r.working_started_at is not None

    def test_record_id_not_reusable(self, code, case, alice):
        services.create_record(record_id="NCR-G001-102", controlled_code=code,
                               case=case, preparer=alice)
        with pytest.raises(ValidationError):
            services.create_record(record_id="NCR-G001-102",
                                    controlled_code=code, case=case,
                                    preparer=alice)

    def test_sod_reviewer_cannot_be_preparer(self, code, case, alice):
        r = services.create_record(record_id="NCR-G001-103",
                                    controlled_code=code, case=case,
                                    preparer=alice)
        with pytest.raises(ValidationError):
            services.submit_for_review(r, reviewer=alice)

    def test_sod_approver_cannot_be_preparer(self, code, case, alice, bob):
        r = services.create_record(record_id="NCR-G001-104",
                                    controlled_code=code, case=case,
                                    preparer=alice)
        services.submit_for_review(r, reviewer=bob)
        with pytest.raises(ValidationError):
            services.approve_record(r, approver=alice)

    def test_sod_approver_cannot_be_reviewer(self, code, case, alice, bob):
        r = services.create_record(record_id="NCR-G001-105",
                                    controlled_code=code, case=case,
                                    preparer=alice)
        services.submit_for_review(r, reviewer=bob)
        with pytest.raises(ValidationError):
            services.approve_record(r, approver=bob)

    def test_full_workflow_working_review_approved(self, code, case, alice, bob, carol):
        r = services.create_record(record_id="NCR-G001-106",
                                    controlled_code=code, case=case,
                                    preparer=alice)
        services.submit_for_review(r, reviewer=bob)
        assert r.status == RecordInstance.Status.REVIEW
        assert r.reviewer == bob
        services.approve_record(r, approver=carol)
        r.refresh_from_db()
        assert r.status == RecordInstance.Status.APPROVED
        assert r.approver == carol
        assert r.approved_at is not None

    def test_finalize_record_copy_only_from_approved(self, code, case, alice, bob, carol):
        r = services.create_record(record_id="NCR-G001-107",
                                    controlled_code=code, case=case,
                                    preparer=alice)
        with pytest.raises(ValidationError):
            services.finalize_record_copy(r, path="/MCOS/x/")
        services.submit_for_review(r, reviewer=bob)
        services.approve_record(r, approver=carol)
        services.finalize_record_copy(r, path="/MCOS/RECORDS/NCR-G001-107/")
        r.refresh_from_db()
        assert r.status == RecordInstance.Status.RECORD_COPY
        assert r.record_copy_path.startswith("/MCOS/")

    def test_record_copy_is_immutable(self, code, case, alice, bob, carol):
        r = services.create_record(record_id="NCR-G001-108",
                                    controlled_code=code, case=case,
                                    preparer=alice)
        services.submit_for_review(r, reviewer=bob)
        services.approve_record(r, approver=carol)
        services.finalize_record_copy(r)
        with pytest.raises(ValidationError):
            services.submit_for_review(r, reviewer=alice)

    def test_approve_requires_review_state(self, code, case, alice, carol):
        r = services.create_record(record_id="NCR-G001-109",
                                    controlled_code=code, case=case,
                                    preparer=alice)
        with pytest.raises(ValidationError):
            services.approve_record(r, approver=carol)


# ---------------------------------------------------------------------------
# Evidence + SHA-256 + ALCOA+
# ---------------------------------------------------------------------------

class TestEvidence:
    def test_add_evidence_without_file(self, case, alice):
        e = services.add_evidence(
            evidence_id="EVD-G001-001", case=case,
            kind=Evidence.Kind.LOG, title="System log",
            collected_by=alice)
        assert e.sha256 == ""
        assert e.is_contemporaneous is True
        assert e.is_original is True

    def test_add_evidence_with_file_hashes_sha256(self, case, alice):
        from django.core.files.uploadedfile import SimpleUploadedFile
        content = b"hello mcos evidence"
        f = SimpleUploadedFile("audit.log", content, content_type="text/plain")
        e = services.add_evidence(
            evidence_id="EVD-G001-002", case=case,
            kind=Evidence.Kind.RAW_DATA, title="Audit log",
            collected_by=alice, file=f)
        # sha256(b"hello mcos evidence")
        import hashlib
        assert e.sha256 == hashlib.sha256(content).hexdigest()

    def test_evidence_id_unique(self, case, alice):
        services.add_evidence(evidence_id="EVD-G001-003", case=case,
                               kind=Evidence.Kind.LOG, title="X",
                               collected_by=alice)
        with pytest.raises(ValidationError):
            services.add_evidence(evidence_id="EVD-G001-003", case=case,
                                   kind=Evidence.Kind.LOG, title="Y",
                                   collected_by=alice)

    def test_alcoa_derivative_flag(self, case, alice):
        e = services.add_evidence(evidence_id="EVD-G001-004", case=case,
                                   kind=Evidence.Kind.SIGNED_REPORT,
                                   title="Turev rapor", collected_by=alice,
                                   is_original=False,
                                   derivative_note="EVD-G001-001'den PDF cikarim")
        assert e.is_original is False
        assert "EVD-G001-001" in e.derivative_note


# ---------------------------------------------------------------------------
# Decision + Self-approval + NAV-002 §4 zorunlu alanlar
# ---------------------------------------------------------------------------

class TestDecision:
    def test_record_decision_creates_row(self, case, alice, bob):
        d = services.record_decision(
            decision_id="DEC-001", case=case,
            level=Decision.Level.D3, status=Decision.Status.CONDITIONAL,
            decision_maker=alice,
            options_considered="Option A: Rollback; Option B: Hotfix",
            rationale="Kanit EVD-001 hotfix'i destekliyor",
            independent_reviewers=[bob],
            delegated_authority="IT Manager per CDD-002",
            veto_holder_role="QA/QC",
            conditions="24 saat izle",
        )
        assert d.pk is not None
        assert d.status == Decision.Status.CONDITIONAL
        assert bob in d.independent_reviewers.all()

    def test_self_approval_forbidden(self, case, alice):
        with pytest.raises(ValidationError):
            services.record_decision(
                decision_id="DEC-002", case=case,
                level=Decision.Level.D3, status=Decision.Status.PASS,
                decision_maker=alice,
                options_considered="A", rationale="B",
                independent_reviewers=[alice])  # alice hem karar veren hem inceleyen

    def test_decision_id_unique(self, case, alice):
        services.record_decision(
            decision_id="DEC-003", case=case, level=Decision.Level.D2,
            status=Decision.Status.PASS, decision_maker=alice,
            options_considered="A", rationale="B")
        with pytest.raises(ValidationError):
            services.record_decision(
                decision_id="DEC-003", case=case, level=Decision.Level.D2,
                status=Decision.Status.PASS, decision_maker=alice,
                options_considered="A2", rationale="B2")

    def test_decisions_are_separate_by_t_phase(self, case, alice, bob):
        """Recovery ≠ RTS ≠ CAPA effectiveness ≠ gate close — hepsi ayrı karar."""
        dec_recovery = services.record_decision(
            decision_id="DEC-T4-REC", case=case, level=Decision.Level.D3,
            status=Decision.Status.PASS, decision_maker=alice,
            options_considered="A", rationale="Recovery kabul")
        dec_rts = services.record_decision(
            decision_id="DEC-T5-RTS", case=case, level=Decision.Level.D3,
            status=Decision.Status.PASS, decision_maker=alice,
            options_considered="A", rationale="RTS kabul")
        dec_capa = services.record_decision(
            decision_id="DEC-T6-CAPA", case=case, level=Decision.Level.D3,
            status=Decision.Status.PASS, decision_maker=bob,
            options_considered="A", rationale="CAPA effectiveness")
        assert case.decisions.count() == 3
        assert {d.decision_id for d in case.decisions.all()} == {
            "DEC-T4-REC", "DEC-T5-RTS", "DEC-T6-CAPA"}


# ---------------------------------------------------------------------------
# E-signature (21 CFR Part 11 tarzı)
# ---------------------------------------------------------------------------

class TestSignature:
    def test_sign_decision_with_correct_password(self, case, alice, bob):
        d = services.record_decision(
            decision_id="DEC-100", case=case, level=Decision.Level.D3,
            status=Decision.Status.PASS, decision_maker=alice,
            options_considered="A", rationale="B")
        sig = services.sign_decision(
            d, signer=bob, password="pw",
            meaning=DecisionSignature.Meaning.REVIEWED,
            reason="Bagimsiz gozden gecirdim")
        assert sig.pk is not None
        assert sig.decision == d

    def test_sign_decision_with_wrong_password_raises(self, case, alice, bob):
        d = services.record_decision(
            decision_id="DEC-101", case=case, level=Decision.Level.D3,
            status=Decision.Status.PASS, decision_maker=alice,
            options_considered="A", rationale="B")
        with pytest.raises(PermissionDenied):
            services.sign_decision(d, signer=bob, password="wrong-pw",
                                    meaning=DecisionSignature.Meaning.APPROVED,
                                    reason="X")

    def test_sign_decision_invalid_meaning_raises(self, case, alice, bob):
        d = services.record_decision(
            decision_id="DEC-102", case=case, level=Decision.Level.D3,
            status=Decision.Status.PASS, decision_maker=alice,
            options_considered="A", rationale="B")
        with pytest.raises(ValidationError):
            services.sign_decision(d, signer=bob, password="pw",
                                    meaning="INVALID", reason="X")


# ---------------------------------------------------------------------------
# Full end-to-end workflow (Case → Record → Evidence → Decision → Sign)
# ---------------------------------------------------------------------------

class TestFullWorkflow:
    def test_gate001_full_flow(self, code, alice, bob, carol):
        # T0 Case açılır
        c = services.open_case(
            case_id="INCIDENT-999", family=Case.Family.INCIDENT,
            title="Sistem anomalisi", description="Detay...",
            detected_by=alice, gate="GATE-001",
            severity=Case.Severity.SEV1)

        # T1 Containment
        services.mark_case_phase(c, "T1")

        # Evidence toplanır
        ev = services.add_evidence(evidence_id="EVD-999-001", case=c,
                                    kind=Evidence.Kind.RAW_DATA,
                                    title="Log dump", collected_by=alice)

        # Record: NCR formu doldurulur
        r = services.create_record(record_id="NCR-999-001",
                                    controlled_code=code, case=c,
                                    preparer=alice)
        services.submit_for_review(r, reviewer=bob)
        services.approve_record(r, approver=carol)

        # Decision: T5 RTS
        d = services.record_decision(
            decision_id="DEC-999-RTS", case=c, level=Decision.Level.D3,
            status=Decision.Status.PASS, decision_maker=carol,
            options_considered="Reject / Accept / Conditional",
            rationale="Recovery kabul edildi",
            record_instance=r,
            evidence_reviewed=[ev],
            independent_reviewers=[bob],
            veto_holder_role="QA/QC")

        # E-imza (Part 11)
        services.sign_decision(d, signer=bob, password="pw",
                                meaning=DecisionSignature.Meaning.REVIEWED,
                                reason="Bagimsiz gozden gecirdim")

        services.mark_case_phase(c, "CLOSED")
        c.refresh_from_db()

        assert c.status == Case.Status.CLOSED
        assert c.records.count() == 1
        assert c.evidence_set.count() == 1
        assert c.decisions.count() == 1
        assert d.signatures.count() == 1


# ---------------------------------------------------------------------------
# FK entegrasyonu — NCR/CAPA/Incident case FK'sı var mı?
# ---------------------------------------------------------------------------

class TestExistingModelFKs:
    def test_ncr_has_case_fk(self):
        from qms.models import Nonconformance
        assert hasattr(Nonconformance, "case")

    def test_capa_has_case_and_record_fk(self):
        from qms.models import CAPA
        assert hasattr(CAPA, "case")
        assert hasattr(CAPA, "record_instance")

    def test_incident_has_case_fk(self):
        from ehs.models import Incident
        assert hasattr(Incident, "case")


# ---------------------------------------------------------------------------
# Portal UI
# ---------------------------------------------------------------------------

class TestPortalUI:
    def test_case_list_requires_login(self, client):
        resp = client.get("/portal/cases/")
        assert resp.status_code in (301, 302)

    def test_case_list_forbidden_without_perm(self, client):
        User.objects.create_user("nobody", password="pw")
        client.login(username="nobody", password="pw")
        resp = client.get("/portal/cases/")
        assert resp.status_code == 403

    def test_case_list_ok_for_superuser(self, client, case):
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/cases/")
        assert resp.status_code == 200
        assert b"INCIDENT-001" in resp.content

    def test_case_detail_page(self, client, case):
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get(f"/portal/cases/{case.case_id}/")
        assert resp.status_code == 200
        assert b"INCIDENT-001" in resp.content
        assert b"GATE-001" in resp.content

    def test_case_detail_404(self, client):
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/cases/NOSUCH/")
        assert resp.status_code == 404

    def test_record_detail_page(self, client, code, case, alice):
        r = services.create_record(record_id="RTS-G001-001",
                                    controlled_code=code, case=case,
                                    preparer=alice)
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get(f"/portal/records/{r.record_id}/")
        assert resp.status_code == 200
        assert b"RTS-G001-001" in resp.content

    def test_decision_detail_page(self, client, case, alice):
        d = services.record_decision(
            decision_id="DEC-UI-001", case=case, level=Decision.Level.D3,
            status=Decision.Status.PASS, decision_maker=alice,
            options_considered="A", rationale="B")
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get(f"/portal/decisions/{d.decision_id}/")
        assert resp.status_code == 200
        assert b"DEC-UI-001" in resp.content

    def test_case_list_filters_by_family(self, client, alice):
        services.open_case(case_id="NCR-2026-001", family=Case.Family.NCR,
                            title="X", description="Y", detected_by=alice)
        services.open_case(case_id="CHG-2026-001", family=Case.Family.CHANGE,
                            title="X2", description="Y2", detected_by=alice)
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/cases/?family=CHANGE")
        assert resp.status_code == 200
        assert b"CHG-2026-001" in resp.content
        assert b"NCR-2026-001" not in resp.content


# ---------------------------------------------------------------------------
# Rol matrisi
# ---------------------------------------------------------------------------

class TestRoleMatrix:
    def test_ims_qa_manager_sees_cases_menu(self):
        from portal.menu import filter_menu_for
        call_command("seed_roles")
        u = User.objects.create_user("qa", password="pw")
        u.groups.add(Group.objects.get(name="IMS_QA_MANAGER"))
        sections = filter_menu_for(u)
        labels = [item["label"] for s in sections for item in s["items"]]
        assert "Case'ler / Vakalar" in labels

    def test_warehouse_role_cannot_see_cases_menu(self):
        from portal.menu import filter_menu_for
        call_command("seed_roles")
        u = User.objects.create_user("wh", password="pw")
        u.groups.add(Group.objects.get(name="WAREHOUSE"))
        sections = filter_menu_for(u)
        labels = [item["label"] for s in sections for item in s["items"]]
        assert "Case'ler / Vakalar" not in labels
