"""Faz C tests — ControlledCode register: format validator, seed, import, UI, FK."""
from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse

from registry.models import (
    ControlledCode,
    ControlledCodeRevision,
    controlled_code_validator,
)


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_code(**overrides) -> ControlledCode:
    defaults = dict(
        full_code="MAPA-IMS-FRM-NCR-001",
        short_alias="NCR-001",
        title="Uygunsuzluk Kaydi",
        type=ControlledCode.Type.FRM,
        level=ControlledCode.Level.L4,
        function=ControlledCode.Function.IMS,
        status=ControlledCode.Status.ISSUED,
        owner_role="QA/IMS Manager",
        activation_gate="SOP + egitim + kabul edilmis kayit",
        objective_evidence_rule="Bos sablon evidence degildir",
    )
    defaults.update(overrides)
    return ControlledCode.objects.create(**defaults)


def _grant_view_perm(user: User) -> None:
    perm = Permission.objects.get(codename="view_controlledcode")
    user.user_permissions.add(perm)


# ---------------------------------------------------------------------------
# Format validator (CDD-001 §9.2 kodlama standardi)
# ---------------------------------------------------------------------------

class TestFormatValidator:
    @pytest.mark.parametrize("valid_code", [
        "MAPA-CDD-001",                # kurumsal CDD (subject yok)
        "MAPA-IMS-FRM-NCR-001",        # tam form
        "MAPA-PRD-FRM-BMR-001",        # uretim BMR
        "MAPA-IT-REG-004",             # IT register (subject yok)
        "MAPA-QMS-PRO-DOC-001",        # prosedur
        "MAPA-COMMS-POL-001",          # 5 harfli fonksiyon (COMMS)
        "MAPA-HR-REG-002",             # 2 harfli fonksiyon
        "MAPA-IMS-FRM-CAPA-001",       # 4 harfli subject
        "MAPA-PRD-FRM-BMR01-001",      # subject alfanumerik
    ])
    def test_valid_codes_pass(self, valid_code):
        controlled_code_validator(valid_code)  # should not raise

    @pytest.mark.parametrize("invalid_code", [
        "MAPA-ims-frm-ncr-001",    # kucuk harf
        "MAPA-IMS-FRM-001-NCR",    # yanlis sirala (seq once)
        "mapa-IMS-FRM-NCR-001",    # kucuk mapa
        "IMS-FRM-NCR-001",         # MAPA prefiks yok
        "MAPA-IMS-FRM-NCR-1",      # seq 3 haneli degil
        "MAPA-A-FRM-NCR-001",      # function 1 harf
        "MAPA-IMS-FRM-NCR-EXT-001", # 4 segment (max 3)
    ])
    def test_invalid_codes_rejected(self, invalid_code):
        with pytest.raises(ValidationError):
            controlled_code_validator(invalid_code)

    def test_model_full_clean_enforces_format(self):
        c = ControlledCode(
            full_code="bogus-format",
            title="x",
            type=ControlledCode.Type.FRM,
            level=ControlledCode.Level.L4,
            function=ControlledCode.Function.IMS,
            owner_role="x",
            activation_gate="x",
            objective_evidence_rule="x",
        )
        with pytest.raises(ValidationError):
            c.full_clean()


# ---------------------------------------------------------------------------
# Unique + basic model contracts
# ---------------------------------------------------------------------------

class TestControlledCodeModel:
    def test_full_code_is_unique(self):
        _make_code()
        with pytest.raises(Exception):
            _make_code()  # ayni full_code ile ikinci — unique violation

    def test_str_shows_code_and_title(self):
        c = _make_code(full_code="MAPA-IMS-FRM-NCR-002")
        assert c.full_code in str(c)
        assert c.title in str(c)

    def test_revision_default_r0(self):
        c = _make_code(full_code="MAPA-IMS-FRM-NCR-003")
        assert c.revision == "R0"

    def test_history_tracks_status_change(self):
        c = _make_code(full_code="MAPA-IMS-FRM-NCR-004",
                       status=ControlledCode.Status.DRAFT)
        c.status = ControlledCode.Status.ISSUED
        c.save()
        # simple-history — >=2 kayit (create + update)
        assert c.history.count() >= 2

    def test_revision_history_ordered_and_unique(self):
        import datetime as dt
        c = _make_code(full_code="MAPA-IMS-FRM-NCR-005")
        ControlledCodeRevision.objects.create(
            code=c, revision="R0", revision_date=dt.date(2026, 1, 1),
            change_summary="Ilk taslak")
        ControlledCodeRevision.objects.create(
            code=c, revision="R1.0", revision_date=dt.date(2026, 6, 1),
            change_summary="Onay sonrasi")
        with pytest.raises(Exception):
            ControlledCodeRevision.objects.create(
                code=c, revision="R1.0", revision_date=dt.date(2026, 7, 1),
                change_summary="dup")


# ---------------------------------------------------------------------------
# seed_mcos_codes — core baseline
# ---------------------------------------------------------------------------

class TestSeedCommand:
    def test_seed_creates_core_codes(self):
        call_command("seed_mcos_codes")
        # En az CDD-001 + IMS-NAV-001 + IMS-FRM-CAPA-001 + PRD-FRM-BMR-001 var
        assert ControlledCode.objects.filter(full_code="MAPA-CDD-001").exists()
        assert ControlledCode.objects.filter(full_code="MAPA-IMS-NAV-001").exists()
        assert ControlledCode.objects.filter(full_code="MAPA-PRD-FRM-BMR-001").exists()

    def test_seed_is_idempotent(self):
        call_command("seed_mcos_codes")
        count1 = ControlledCode.objects.count()
        call_command("seed_mcos_codes")
        count2 = ControlledCode.objects.count()
        assert count1 == count2

    def test_seed_codes_pass_validator(self):
        call_command("seed_mcos_codes")
        for c in ControlledCode.objects.all():
            controlled_code_validator(c.full_code)


# ---------------------------------------------------------------------------
# Business line M2M
# ---------------------------------------------------------------------------

class TestBusinessLineLinkage:
    def test_empty_business_lines_means_corporate(self):
        c = _make_code(full_code="MAPA-COR-CDD-999")
        assert c.business_lines.count() == 0

    def test_can_link_multiple_business_lines(self):
        from businessline.models import BusinessLine
        call_command("seed_business_lines")
        c = _make_code(full_code="MAPA-PRD-FRM-BMR-999")
        c.business_lines.add(BusinessLine.objects.get(code="MCS"))
        c.business_lines.add(BusinessLine.objects.get(code="MPT"))
        assert set(c.business_lines.values_list("code", flat=True)) == {"MCS", "MPT"}


# ---------------------------------------------------------------------------
# Portal UI: liste + detay + izin kontrolu
# ---------------------------------------------------------------------------

class TestRegistryPortal:
    def test_list_requires_login(self, client):
        resp = client.get("/portal/registry/")
        assert resp.status_code in (302, 301)  # login redirect

    def test_list_forbidden_without_perm(self, client):
        u = User.objects.create_user("nobody", password="pw")
        client.login(username="nobody", password="pw")
        resp = client.get("/portal/registry/")
        assert resp.status_code == 403

    def test_list_ok_for_user_with_perm(self, client):
        _make_code()
        u = User.objects.create_user("qa", password="pw")
        _grant_view_perm(u)
        client.login(username="qa", password="pw")
        resp = client.get("/portal/registry/")
        assert resp.status_code == 200
        assert b"MAPA-IMS-FRM-NCR-001" in resp.content

    def test_list_superuser_ok(self, client):
        _make_code()
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/registry/")
        assert resp.status_code == 200

    def test_list_search_filters_by_query(self, client):
        _make_code(full_code="MAPA-IMS-FRM-NCR-101", title="Uygunsuzluk formu")
        _make_code(full_code="MAPA-PRD-FRM-BMR-101", title="Batch Manufacturing Record")
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/registry/?q=BMR")
        assert resp.status_code == 200
        assert b"MAPA-PRD-FRM-BMR-101" in resp.content
        assert b"MAPA-IMS-FRM-NCR-101" not in resp.content

    def test_list_filters_by_function(self, client):
        _make_code(full_code="MAPA-IMS-FRM-NCR-201",
                   function=ControlledCode.Function.IMS)
        _make_code(full_code="MAPA-PRD-FRM-BMR-201",
                   function=ControlledCode.Function.PRD)
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/registry/?function=PRD")
        assert resp.status_code == 200
        assert b"MAPA-PRD-FRM-BMR-201" in resp.content
        assert b"MAPA-IMS-FRM-NCR-201" not in resp.content

    def test_detail_shows_full_code_and_title(self, client):
        c = _make_code(full_code="MAPA-IMS-FRM-NCR-301", title="NCR Formu")
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get(f"/portal/registry/{c.pk}/")
        assert resp.status_code == 200
        assert b"MAPA-IMS-FRM-NCR-301" in resp.content
        assert "NCR Formu".encode("utf-8") in resp.content

    def test_detail_404_for_unknown(self, client):
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/registry/99999/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# IMS_QA_MANAGER rolu registry gorebilir (seed_roles matrisi)
# ---------------------------------------------------------------------------

class TestRoleMatrix:
    def test_ims_qa_manager_can_view_registry(self, client):
        call_command("seed_roles")
        _make_code()
        u = User.objects.create_user("qa_mgr", password="pw")
        u.groups.add(Group.objects.get(name="IMS_QA_MANAGER"))
        client.login(username="qa_mgr", password="pw")
        resp = client.get("/portal/registry/")
        assert resp.status_code == 200

    def test_warehouse_role_cannot_view_registry(self, client):
        call_command("seed_roles")
        u = User.objects.create_user("wh", password="pw")
        u.groups.add(Group.objects.get(name="WAREHOUSE"))
        client.login(username="wh", password="pw")
        resp = client.get("/portal/registry/")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Menu integration
# ---------------------------------------------------------------------------

class TestMenuIntegration:
    def test_menu_shows_registry_for_qa_manager(self):
        from portal.menu import filter_menu_for
        call_command("seed_roles")
        u = User.objects.create_user("qa_mgr2", password="pw")
        u.groups.add(Group.objects.get(name="IMS_QA_MANAGER"))
        sections = filter_menu_for(u)
        labels = [item["label"] for section in sections for item in section["items"]]
        assert "Kontrollü Kod Register" in labels

    def test_menu_hides_registry_for_warehouse(self):
        from portal.menu import filter_menu_for
        call_command("seed_roles")
        u = User.objects.create_user("wh2", password="pw")
        u.groups.add(Group.objects.get(name="WAREHOUSE"))
        sections = filter_menu_for(u)
        labels = [item["label"] for section in sections for item in section["items"]]
        assert "Kontrollü Kod Register" not in labels


# ---------------------------------------------------------------------------
# FK entegrasyonu — mevcut modellerde controlled_code alan var mi?
# ---------------------------------------------------------------------------

class TestForeignKeyIntegration:
    def test_ncr_can_reference_controlled_code(self, db):
        from qms.models import Nonconformance
        assert hasattr(Nonconformance, "controlled_code"), (
            "Nonconformance modelinde controlled_code FK olmali (Faz C)"
        )

    def test_capa_can_reference_controlled_code(self, db):
        from qms.models import CAPA
        assert hasattr(CAPA, "controlled_code")

    def test_document_can_reference_controlled_code(self, db):
        from docs.models import ControlledDocument
        assert hasattr(ControlledDocument, "controlled_code")

    def test_batch_can_reference_controlled_code(self, db):
        from production.models import ProductionBatch
        assert hasattr(ProductionBatch, "controlled_code")

    def test_coa_can_reference_controlled_code(self, db):
        from quality.models import CertificateOfAnalysis
        assert hasattr(CertificateOfAnalysis, "controlled_code")
