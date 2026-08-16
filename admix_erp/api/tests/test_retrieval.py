"""Faz F tests — MCOS Retrieval Endpoint (2 dk SLA)."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework.test import APIClient

from api.models import RetrievalSampleReport
from records import services as record_services
from records.models import Case, Decision, Evidence


pytestmark = pytest.mark.django_db


@pytest.fixture
def user(db):
    return User.objects.create_user("alice", password="pw")


@pytest.fixture
def api_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def case(user):
    return record_services.open_case(
        case_id="INCIDENT-R1", family=Case.Family.INCIDENT,
        title="Retrieval testi", description="detay",
        detected_by=user, gate="GATE-001",
        severity=Case.Severity.SEV2,
    )


@pytest.fixture
def code(db):
    from registry.models import ControlledCode
    return ControlledCode.objects.create(
        full_code="MAPA-IMS-FRM-NCR-001", title="NCR Formu",
        type=ControlledCode.Type.FRM, level=ControlledCode.Level.L4,
        function=ControlledCode.Function.IMS, owner_role="QA/IMS Manager",
        activation_gate="x", objective_evidence_rule="x",
    )


# ---------------------------------------------------------------------------
# Auth / hata durumlari
# ---------------------------------------------------------------------------

class TestRetrievalAuth:
    def test_anonymous_denied(self):
        c = APIClient()
        resp = c.get("/api/v1/retrieve/?ref=INCIDENT-1")
        assert resp.status_code in (401, 403)

    def test_missing_ref_returns_400(self, api_client):
        resp = api_client.get("/api/v1/retrieve/")
        assert resp.status_code == 400
        assert "ref" in resp.json().get("error", "").lower()

    def test_unknown_ref_returns_404(self, api_client):
        resp = api_client.get("/api/v1/retrieve/?ref=NOSUCH-999")
        assert resp.status_code == 404
        body = resp.json()
        assert "Kimlik bulunamadı" in body["error"]
        assert "searched" in body


# ---------------------------------------------------------------------------
# Farkli ID turleri ile retrieval
# ---------------------------------------------------------------------------

class TestRetrievalByType:
    def test_retrieve_case_returns_full_dossier(self, api_client, case):
        resp = api_client.get(f"/api/v1/retrieve/?ref={case.case_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["resolved_type"] == "Case"
        assert body["case"]["case_id"] == case.case_id
        assert body["case"]["family"] == "INCIDENT"
        assert isinstance(body["records"], list)
        assert isinstance(body["evidence"], list)
        assert isinstance(body["decisions"], list)
        assert "generation_time_ms" in body
        assert "generated_at" in body

    def test_retrieve_record_includes_case_dossier(self, api_client, case, code, user):
        r = record_services.create_record(
            record_id="NCR-R1-001", controlled_code=code, case=case,
            preparer=user)
        resp = api_client.get(f"/api/v1/retrieve/?ref={r.record_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["resolved_type"] == "RecordInstance"
        assert body["resolved_object"]["record_id"] == r.record_id
        # Bagli case dossier'i da gelmeli
        assert body["case"]["case_id"] == case.case_id
        assert len(body["records"]) >= 1

    def test_retrieve_evidence_includes_case_dossier(self, api_client, case, user):
        ev = record_services.add_evidence(
            evidence_id="EVD-R1-001", case=case, kind=Evidence.Kind.LOG,
            title="log", collected_by=user)
        resp = api_client.get(f"/api/v1/retrieve/?ref={ev.evidence_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["resolved_type"] == "Evidence"
        assert body["resolved_object"]["evidence_id"] == ev.evidence_id
        assert body["case"]["case_id"] == case.case_id
        # evidence LISTE olarak da gelmeli (case'in tüm evidence'ları)
        assert isinstance(body["evidence"], list)
        assert any(e["evidence_id"] == ev.evidence_id for e in body["evidence"])

    def test_retrieve_decision(self, api_client, case, user):
        d = record_services.record_decision(
            decision_id="DEC-R1-001", case=case, level=Decision.Level.D3,
            status=Decision.Status.PASS, decision_maker=user,
            options_considered="A", rationale="B")
        resp = api_client.get(f"/api/v1/retrieve/?ref={d.decision_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["resolved_type"] == "Decision"
        assert body["resolved_object"]["decision_id"] == d.decision_id
        assert body["case"]["case_id"] == case.case_id

    def test_retrieve_gate(self, api_client, case, user):
        from gates.services import open_gate
        g = open_gate(gate_id="GATE-R1-001", case=case, owner=user,
                       scope="test")
        resp = api_client.get(f"/api/v1/retrieve/?ref={g.gate_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["resolved_type"] == "Gate"
        assert body["resolved_object"]["gate_id"] == g.gate_id
        # 8 section
        assert len(body["resolved_object"]["sections"]) == 8

    def test_retrieve_lot(self, api_client, user):
        from decimal import Decimal
        import datetime as dt
        from inventory.models import RawMaterialLot
        from masterdata.models import RawMaterial, Supplier, UnitOfMeasure
        kg = UnitOfMeasure.objects.create(code="kg", name="Kilogram")
        rm = RawMaterial.objects.create(
            code="TEST-RM", name="Test",
            material_type=RawMaterial.MaterialType.ADDITIVE, unit=kg)
        sup = Supplier.objects.create(code="SUP-R1", name="Test Sup")
        lot = RawMaterialLot.objects.create(
            lot_number="LOT-R1-001", raw_material=rm, supplier=sup,
            received_date=dt.date.today(),
            received_qty=Decimal("100"), remaining_qty=Decimal("100"),
            qc_status=RawMaterialLot.QCStatus.RELEASED)
        resp = api_client.get(f"/api/v1/retrieve/?ref={lot.lot_number}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["resolved_type"] == "Lot"
        assert body["resolved_object"]["lot_number"] == "LOT-R1-001"


# ---------------------------------------------------------------------------
# SLA
# ---------------------------------------------------------------------------

class TestRetrievalSLA:
    def test_generation_time_within_sla(self, api_client, case):
        resp = api_client.get(f"/api/v1/retrieve/?ref={case.case_id}")
        assert resp.status_code == 200
        # SLA = 120000 ms. Dev DB'de saniyeler mertebesinde olmali.
        assert resp.json()["generation_time_ms"] < 120_000
        # warnings SLA icinde bos olmali
        assert resp.json()["warnings"] == []

    def test_case_with_records_evidence_decisions_returns_them(
            self, api_client, case, code, user):
        # 2 record + 1 evidence + 1 decision ekle
        r1 = record_services.create_record(
            record_id="NCR-R1-100", controlled_code=code, case=case,
            preparer=user)
        r2 = record_services.create_record(
            record_id="NCR-R1-101", controlled_code=code, case=case,
            preparer=user)
        record_services.add_evidence(
            evidence_id="EVD-R1-100", case=case, kind=Evidence.Kind.LOG,
            title="x", collected_by=user)
        record_services.record_decision(
            decision_id="DEC-R1-100", case=case, level=Decision.Level.D3,
            status=Decision.Status.PASS, decision_maker=user,
            options_considered="A", rationale="B")

        resp = api_client.get(f"/api/v1/retrieve/?ref={case.case_id}")
        body = resp.json()
        assert len(body["records"]) == 2
        assert len(body["evidence"]) == 1
        assert len(body["decisions"]) == 1


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------

class TestSampleCommand:
    def test_sample_creates_pass_report(self, case):
        call_command("retrieval_sample", "--n", "1")
        reports = RetrievalSampleReport.objects.all()
        assert reports.count() == 1
        r = reports.first()
        assert r.result in (RetrievalSampleReport.Result.PASS,
                             RetrievalSampleReport.Result.SLOW)
        assert r.resolved_type in ("Case", "RecordInstance", "Evidence",
                                    "Decision", "Gate", "Batch", "Lot")

    def test_sample_with_empty_pool_prints_warning(self):
        call_command("retrieval_sample", "--n", "5")
        assert RetrievalSampleReport.objects.count() == 0
