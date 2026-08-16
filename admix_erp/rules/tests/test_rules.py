"""Faz H tests — 12 Non-Negotiable Rules Enforcer.

Her kural için pozitif (geçer) ve negatif (blok/log) test.
Test'lerde `settings.MCOS_ENABLE_RULES_ENFORCER=True` set edilir; production
default kapalı (mevcut 320+ testi bozmasın diye).

NOT: Bloklu kurallar (R01-R11) `RuleViolationError` yükseltir. Bu, `pre_save`
signal'i içinde raise edildiği için Django outer transaction'ı rollback eder ve
RuleViolation DB kaydı da geri alınır. Testte sadece `pytest.raises` doğrulanır;
log persistence'i integration-level bir konudur (view'da try/except ile yakalayıp
log yazılır). R12 log-only olduğu için raise yok → log persist eder.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.utils import timezone

from iam.models import Role
from rules.enforcer import RuleViolationError
from rules.models import RuleViolation


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixture: feature flag açık — Faz H testleri için
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _enable_rules(settings):
    settings.MCOS_ENABLE_RULES_ENFORCER = True


@pytest.fixture
def alice(db):
    return User.objects.create_user("alice", password="pw")


# ---------------------------------------------------------------------------
# R01 — Onaysız reçete ile üretim yok
# ---------------------------------------------------------------------------

class TestRule01BatchApprovedRecipe:
    def test_active_recipe_batch_saves(self, order, recipe, reactor):
        from production.models import ProductionBatch
        assert recipe.is_active is True
        b = ProductionBatch.objects.create(
            batch_number="B-R01-OK", production_order=order, recipe=recipe,
            target_qty=Decimal("500"), reactor=reactor,
        )
        assert b.pk

    def test_inactive_recipe_batch_blocked(self, order, recipe, reactor):
        recipe.is_active = False
        recipe.save()
        from production.models import ProductionBatch
        with pytest.raises(RuleViolationError):
            ProductionBatch.objects.create(
                batch_number="B-R01-BAD", production_order=order, recipe=recipe,
                target_qty=Decimal("500"), reactor=reactor,
            )


# ---------------------------------------------------------------------------
# R02 — HOLD/REJECT malzeme kullanılamaz veya sevk edilemez
# ---------------------------------------------------------------------------

class TestRule02Consumption:
    def test_released_lot_can_be_consumed(self, order, recipe, released_lots, reactor):
        from production.models import MaterialConsumption, ProductionBatch
        b = ProductionBatch.objects.create(
            batch_number="B-R02-OK", production_order=order, recipe=recipe,
            target_qty=Decimal("500"), reactor=reactor,
        )
        # Basit MaterialConsumption oluştur — model alanları için gerekli minimum
        lot = released_lots["W"]
        mc = MaterialConsumption(
            batch=b, lot=lot, raw_material=lot.raw_material,
            target_weight=Decimal("100"),
        )
        mc.save()
        assert mc.pk

    def test_hold_lot_consumption_blocked(self, order, recipe, released_lots, reactor):
        from inventory.models import RawMaterialLot
        from production.models import MaterialConsumption, ProductionBatch
        lot = released_lots["W"]
        lot.qc_status = RawMaterialLot.QCStatus.QUARANTINE
        lot.save()
        b = ProductionBatch.objects.create(
            batch_number="B-R02-BAD", production_order=order, recipe=recipe,
            target_qty=Decimal("500"), reactor=reactor,
        )
        with pytest.raises(RuleViolationError):
            MaterialConsumption(
                batch=b, lot=lot, raw_material=lot.raw_material,
                target_weight=Decimal("100"),
            ).save()


# ---------------------------------------------------------------------------
# R03 — Geçerli numune + review olmadan release yok
# ---------------------------------------------------------------------------

class TestRule03ReleaseNeedsQC:
    def test_release_without_qc_blocked(self, order, recipe, reactor):
        from production.models import ProductionBatch
        b = ProductionBatch.objects.create(
            batch_number="B-R03-BAD", production_order=order, recipe=recipe,
            target_qty=Decimal("500"), reactor=reactor,
        )
        b.qc_status = ProductionBatch.QCStatus.RELEASED
        with pytest.raises(RuleViolationError):
            b.save()


# ---------------------------------------------------------------------------
# R04 — QC ölçümü geçerli kalibrasyon olmadan kabul edilmez
# Equipment.calibration_valid_until modelde yok — kural opt-in NoOp
# ---------------------------------------------------------------------------

class TestRule04CalibrationOptional:
    def test_qc_result_saves_without_equipment_field(self, alice, order, recipe, reactor):
        from production.models import ProductionBatch
        from quality.models import QCParameter, QCTestResult
        b = ProductionBatch.objects.create(
            batch_number="B-R04", production_order=order, recipe=recipe,
            target_qty=Decimal("500"), reactor=reactor,
        )
        param = QCParameter.objects.create(
            code="Density", name="Yoğunluk", unit="g/cm3",
        )
        r = QCTestResult.objects.create(
            parameter=param, batch=b,
            value=Decimal("1.2"),
            verdict=QCTestResult.Verdict.PASS,
            tester=alice.username,
        )
        assert r.pk


# ---------------------------------------------------------------------------
# R05 — Kayıt geriye dönük oluşturulmaz
# ---------------------------------------------------------------------------

class TestRule05NoBackdating:
    def test_current_record_saves(self, alice):
        from records import services as rs
        from records.models import Case
        from registry.models import ControlledCode
        case = rs.open_case(
            case_id="CASE-R05-OK", family=Case.Family.INCIDENT,
            title="X", description="Y", detected_by=alice,
            severity=Case.Severity.SEV3,
        )
        code = ControlledCode.objects.create(
            full_code="MAPA-R05-FRM-001", title="R05",
            type=ControlledCode.Type.FRM, level=ControlledCode.Level.L4,
            function=ControlledCode.Function.IMS,
            owner_role="QA/IMS Manager",
            activation_gate="x", objective_evidence_rule="y",
        )
        r = rs.create_record(record_id="REC-R05-OK", controlled_code=code,
                              case=case, preparer=alice)
        assert r.pk

    def test_backdated_record_blocked(self, alice):
        from records import services as rs
        from records.models import Case
        from registry.models import ControlledCode
        # Case tarihini geleceğe çek — record onun öncesinde başlıyor gibi görünsün
        future = timezone.now() + dt.timedelta(days=10)
        case = rs.open_case(
            case_id="CASE-R05-BAD", family=Case.Family.INCIDENT,
            title="X", description="Y", detected_by=alice,
            detected_at=future,
            severity=Case.Severity.SEV3,
        )
        code = ControlledCode.objects.create(
            full_code="MAPA-R05-FRM-002", title="R05-bad",
            type=ControlledCode.Type.FRM, level=ControlledCode.Level.L4,
            function=ControlledCode.Function.IMS,
            owner_role="QA/IMS Manager",
            activation_gate="x", objective_evidence_rule="y",
        )
        with pytest.raises(RuleViolationError):
            rs.create_record(record_id="REC-R05-BAD",
                              controlled_code=code, case=case, preparer=alice)


# ---------------------------------------------------------------------------
# R06 — MOC olmadan aktif reçete değişmez (opt-in — Recipe modelde
# change_notice_ref alanı yok → kural NoOp)
# ---------------------------------------------------------------------------

class TestRule06RecipeMoc:
    def test_recipe_edit_without_moc_field_ok(self, recipe):
        # change_notice_ref alanı model'de yok → kural atlanır
        recipe.base_batch_size = Decimal("1500")
        recipe.save()
        assert recipe.base_batch_size == Decimal("1500")


# ---------------------------------------------------------------------------
# R07 — QA veto ticari baskıyla bypass edilemez
# ---------------------------------------------------------------------------

class TestRule07QAVeto:
    def test_veto_prevents_later_approved(self, alice, db):
        from django.contrib.contenttypes.models import ContentType
        from portal.models import ApprovalRequest

        call_command("seed_roles")
        target_user = User.objects.create_user("target", password="pw")
        ct = ContentType.objects.get_for_model(User)

        # 1) İlk talep veto edilmiş halde kaydedilir
        ApprovalRequest.objects.create(
            kind=ApprovalRequest.Kind.OTHER,
            title="Vetolu", content_type=ct, object_id=target_user.pk,
            requested_by=alice, required_role=Role.OPERATIONS_MANAGER,
            decision_level="D2",
            status=ApprovalRequest.Status.REJECTED,
            decision_reason="[VETO by HSE_OFFICER] Guvensiz",
        )
        # 2) Aynı hedefe yeni PENDING talep — geçmeli
        new_ar = ApprovalRequest.objects.create(
            kind=ApprovalRequest.Kind.OTHER,
            title="Yeni talep", content_type=ct, object_id=target_user.pk,
            requested_by=alice, required_role=Role.OPERATIONS_MANAGER,
            decision_level="D2",
            status=ApprovalRequest.Status.PENDING,
        )
        # 3) APPROVED'e transition — R07 bloklar
        new_ar.status = ApprovalRequest.Status.APPROVED
        with pytest.raises(RuleViolationError):
            new_ar.save()


# ---------------------------------------------------------------------------
# R08 — Emniyetsiz iş bypass edilemez
# ---------------------------------------------------------------------------

class TestRule08HSESevereClose:
    def test_severe_incident_close_without_case_blocked(self, alice):
        from ehs.models import Incident
        inc = Incident.objects.create(
            incident_number="INC-R08-BAD", type=Incident.Type.INJURY,
            severity=Incident.Severity.MAJOR,
            occurred_at=timezone.now(),
            location="Reaktor 1", description="ciddi olay",
            reported_by=alice,
        )
        # Case yok → CLOSED transition R08 bloklamalı
        inc.status = "CLOSED"
        with pytest.raises(RuleViolationError):
            inc.save()

    def test_severe_incident_close_with_case_ok(self, alice):
        from ehs.models import Incident
        from records import services as rs
        from records.models import Case
        c = rs.open_case(case_id="CASE-R08-OK", family=Case.Family.INCIDENT,
                          title="X", description="Y", detected_by=alice,
                          severity=Case.Severity.SEV3)
        inc = Incident.objects.create(
            incident_number="INC-R08-OK", type=Incident.Type.INJURY,
            severity=Incident.Severity.MAJOR,
            occurred_at=timezone.now(),
            location="Reaktor 1", description="olay",
            reported_by=alice, case=c,
        )
        inc.status = "CLOSED"
        inc.save()
        assert inc.status == "CLOSED"


# ---------------------------------------------------------------------------
# R09 — Kritik görev yetkisiz kişi tarafından yürütülemez
# ---------------------------------------------------------------------------

class TestRule09DecisionAuthority:
    def test_gm_can_make_d4_decision(self, alice):
        from records import services as rs
        from records.models import Case, Decision
        call_command("seed_roles")
        alice.groups.add(Group.objects.get(name=Role.GENERAL_MANAGER))
        c = rs.open_case(case_id="CASE-R09-OK", family=Case.Family.INCIDENT,
                          title="X", description="Y", detected_by=alice,
                          severity=Case.Severity.SEV3)
        d = rs.record_decision(
            decision_id="DEC-R09-OK", case=c, level=Decision.Level.D4,
            status=Decision.Status.PASS, decision_maker=alice,
            options_considered="A", rationale="B")
        assert d.pk

    def test_warehouse_cannot_make_d3_decision(self, alice):
        from records import services as rs
        from records.models import Case, Decision
        call_command("seed_roles")
        alice.groups.add(Group.objects.get(name=Role.WAREHOUSE))
        c = rs.open_case(case_id="CASE-R09-BAD", family=Case.Family.INCIDENT,
                          title="X", description="Y", detected_by=alice,
                          severity=Case.Severity.SEV3)
        with pytest.raises(RuleViolationError):
            rs.record_decision(
                decision_id="DEC-R09-BAD", case=c, level=Decision.Level.D3,
                status=Decision.Status.PASS, decision_maker=alice,
                options_considered="A", rationale="B")

    def test_delegated_authority_bypasses_r09(self, alice):
        from records import services as rs
        from records.models import Case, Decision
        c = rs.open_case(case_id="CASE-R09-DEL", family=Case.Family.INCIDENT,
                          title="X", description="Y", detected_by=alice,
                          severity=Case.Severity.SEV3)
        d = rs.record_decision(
            decision_id="DEC-R09-DEL", case=c, level=Decision.Level.D4,
            status=Decision.Status.PASS, decision_maker=alice,
            options_considered="A", rationale="B",
            delegated_authority="GM tarafından bu vaka için yetkilendirildi",
        )
        assert d.pk


# ---------------------------------------------------------------------------
# R10 — CAPA sadece aksiyon yapıldı diye kapanmaz
# ---------------------------------------------------------------------------

class TestRule10CAPAEffectiveness:
    def test_capa_close_without_verified_at_blocked(self, alice):
        from qms.models import CAPA
        capa = CAPA.objects.create(
            capa_number="CAPA-R10-BAD",
            type=CAPA.Type.CORRECTIVE,
            title="X", description="Y",
            action_plan="Z",
            owner=alice,
        )
        capa.status = CAPA.Status.CLOSED
        with pytest.raises(RuleViolationError):
            capa.save()

    def test_capa_close_with_verified_at_ok(self, alice):
        from qms.models import CAPA
        capa = CAPA.objects.create(
            capa_number="CAPA-R10-OK",
            type=CAPA.Type.CORRECTIVE,
            title="X", description="Y",
            action_plan="Z",
            owner=alice,
            verified_at=timezone.now(),
        )
        capa.status = CAPA.Status.CLOSED
        capa.save()
        assert capa.status == "CLOSED"


# ---------------------------------------------------------------------------
# R11 — ControlledCode sahibi olmadan yayımlanmaz
# ---------------------------------------------------------------------------

class TestRule11ControlledCodeOwner:
    def test_draft_without_owner_ok(self):
        from registry.models import ControlledCode
        c = ControlledCode.objects.create(
            full_code="MAPA-R11-FRM-001", title="draft",
            type=ControlledCode.Type.FRM, level=ControlledCode.Level.L4,
            function=ControlledCode.Function.IMS,
            owner_role="",
            activation_gate="x", objective_evidence_rule="y",
            status=ControlledCode.Status.DRAFT,
        )
        assert c.pk

    def test_issued_without_owner_blocked(self):
        from registry.models import ControlledCode
        with pytest.raises(RuleViolationError):
            ControlledCode.objects.create(
                full_code="MAPA-R11-FRM-002", title="bad",
                type=ControlledCode.Type.FRM, level=ControlledCode.Level.L4,
                function=ControlledCode.Function.IMS,
                owner_role="",  # boş → ISSUED için yasak
                activation_gate="x", objective_evidence_rule="y",
                status=ControlledCode.Status.ISSUED,
            )


# ---------------------------------------------------------------------------
# R12 — Ciddi risk log-only (block etmez, log persist eder)
# ---------------------------------------------------------------------------

class TestRule12SevereEscalation:
    def test_sev3_case_no_escalation_log(self, alice):
        from records import services as rs
        from records.models import Case
        rs.open_case(case_id="CASE-R12-SEV3", family=Case.Family.INCIDENT,
                      title="X", description="Y", detected_by=alice,
                      severity=Case.Severity.SEV3)
        assert not RuleViolation.objects.filter(rule_no=12).exists()

    def test_sev1_case_creates_escalation_log(self, alice):
        from records import services as rs
        from records.models import Case
        c = rs.open_case(case_id="CASE-R12-SEV1", family=Case.Family.INCIDENT,
                          title="Kritik", description="Y", detected_by=alice,
                          severity=Case.Severity.SEV1)
        # SEV1 → log alınmalı ama blocked=False (kayıt geçmiş olmalı)
        assert c.pk
        v = RuleViolation.objects.filter(rule_no=12).first()
        assert v is not None
        assert v.blocked is False


# ---------------------------------------------------------------------------
# Feature flag KAPALI iken kural tetiklenmez
# ---------------------------------------------------------------------------

class TestFeatureFlagOff:
    def test_flag_off_bypasses_all_rules(self, settings, alice):
        """settings.MCOS_ENABLE_RULES_ENFORCER=False → kayıt geçer, log yok."""
        settings.MCOS_ENABLE_RULES_ENFORCER = False
        from registry.models import ControlledCode
        # R11 tetiklemesi gereken kayıt — flag kapalı olduğu için geçmeli
        c = ControlledCode.objects.create(
            full_code="MAPA-FLAG-OFF-001", title="flag off",
            type=ControlledCode.Type.FRM, level=ControlledCode.Level.L4,
            function=ControlledCode.Function.IMS,
            owner_role="",
            activation_gate="x", objective_evidence_rule="y",
            status=ControlledCode.Status.ISSUED,
        )
        assert c.pk
        assert not RuleViolation.objects.filter(rule_no=11).exists()


# ---------------------------------------------------------------------------
# Portal + rol matrisi
# ---------------------------------------------------------------------------

class TestPortalUI:
    def test_violation_list_requires_login(self, client):
        resp = client.get("/portal/kurallar/")
        assert resp.status_code in (301, 302)

    def test_violation_list_forbidden_without_perm(self, client):
        User.objects.create_user("nobody", password="pw")
        client.login(username="nobody", password="pw")
        resp = client.get("/portal/kurallar/")
        assert resp.status_code == 403

    def test_violation_list_ok_for_superuser(self, client):
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/kurallar/")
        assert resp.status_code == 200

    def test_catalog_shows_all_12_rules(self, client):
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/kurallar/katalog/")
        assert resp.status_code == 200
        for n in range(1, 13):
            assert f"R{n:02d}".encode() in resp.content


class TestRoleMatrix:
    def test_ims_qa_manager_sees_rules_menu(self):
        from portal.menu import filter_menu_for
        call_command("seed_roles")
        u = User.objects.create_user("qa", password="pw")
        u.groups.add(Group.objects.get(name=Role.IMS_QA_MANAGER))
        sections = filter_menu_for(u)
        labels = [item["label"] for s in sections for item in s["items"]]
        assert "Kural İhlalleri" in labels
        assert "12 Kural Kataloğu" in labels

    def test_warehouse_role_cannot_see_rules_menu(self):
        from portal.menu import filter_menu_for
        call_command("seed_roles")
        u = User.objects.create_user("wh", password="pw")
        u.groups.add(Group.objects.get(name=Role.WAREHOUSE))
        sections = filter_menu_for(u)
        labels = [item["label"] for s in sections for item in s["items"]]
        assert "Kural İhlalleri" not in labels
