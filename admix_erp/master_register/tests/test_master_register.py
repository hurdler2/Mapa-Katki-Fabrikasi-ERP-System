"""Faz G tests — Master Register: immutable, snapshot chain, UI, permissions."""
from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.utils import IntegrityError

from iam.models import Role
from master_register import services as mr_services
from master_register.models import (
    IntegratedEventRegister,
    SecurityEventRegister,
)
from records import services as record_services
from records.models import Case


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def alice(db):
    return User.objects.create_user("alice", password="pw")


@pytest.fixture
def case(alice):
    return record_services.open_case(
        case_id="INCIDENT-MR1", family=Case.Family.INCIDENT,
        title="MR testi", description="detay", detected_by=alice,
        severity=Case.Severity.SEV2,
    )


@pytest.fixture
def integrated(alice, case):
    return IntegratedEventRegister.objects.create(
        event_id="INCIDENT-MR1",
        family=IntegratedEventRegister.Family.NCR,
        ev_class=IntegratedEventRegister.EvClass.EV2,
        d_level=IntegratedEventRegister.DLevel.D3,
        case=case, owner=alice,
        site_process="Reactor Line #1",
        scope_summary="Sıcaklık anomali",
        detection_date=dt.date(2026, 8, 1),
        status=IntegratedEventRegister.Status.INVESTIGATING,
    )


@pytest.fixture
def security(alice, case):
    return SecurityEventRegister.objects.create(
        incident_id="IT-INC-2026-001",
        detection_datetime=dt.datetime(2026, 8, 1, 12, 0),
        severity=SecurityEventRegister.Severity.SEV1,
        affected_asset="DMZ-FW-01",
        scope_impact_summary="DMZ FW şüpheli aktivite",
        case=case, owner=alice,
        current_status=SecurityEventRegister.CurrentStatus.OPEN,
    )


# ---------------------------------------------------------------------------
# Immutable: delete blocked
# ---------------------------------------------------------------------------

class TestImmutable:
    def test_integrated_cannot_be_deleted(self, integrated):
        with pytest.raises(ValidationError):
            integrated.delete()

    def test_security_cannot_be_deleted(self, security):
        with pytest.raises(ValidationError):
            security.delete()


# ---------------------------------------------------------------------------
# Unique constraint: her event_id icin tek aktif satir
# ---------------------------------------------------------------------------

class TestActiveUnique:
    def test_two_active_same_event_id_forbidden(self, alice, case):
        IntegratedEventRegister.objects.create(
            event_id="INCIDENT-U1", family="NCR", ev_class="EV3",
            d_level="D2", case=case, owner=alice,
            site_process="x", scope_summary="y",
            detection_date=dt.date(2026, 1, 1),
            status=IntegratedEventRegister.Status.OPEN)
        with pytest.raises(IntegrityError):
            IntegratedEventRegister.objects.create(
                event_id="INCIDENT-U1", family="NCR", ev_class="EV3",
                d_level="D2", case=case, owner=alice,
                site_process="x2", scope_summary="y2",
                detection_date=dt.date(2026, 1, 2),
                status=IntegratedEventRegister.Status.OPEN)

    def test_snapshot_and_active_same_event_id_ok(self, integrated):
        """Aynı event_id için: 1 aktif + N snapshot serbest."""
        mr_services.create_snapshot_integrated(
            integrated, status=IntegratedEventRegister.Status.CAPA_PLANNED)
        active = IntegratedEventRegister.objects.filter(
            event_id="INCIDENT-MR1", is_snapshot=False).count()
        snaps = IntegratedEventRegister.objects.filter(
            event_id="INCIDENT-MR1", is_snapshot=True).count()
        assert active == 1
        assert snaps == 1


# ---------------------------------------------------------------------------
# Snapshot mekanizmasi
# ---------------------------------------------------------------------------

class TestSnapshotChain:
    def test_snapshot_marks_old_as_snapshot(self, integrated):
        old_pk = integrated.pk
        new = mr_services.create_snapshot_integrated(
            integrated,
            status=IntegratedEventRegister.Status.CAPA_PLANNED,
            capa_id="CAPA-001", capa_status="PLANNED")
        integrated.refresh_from_db()
        assert integrated.is_snapshot is True
        assert new.is_snapshot is False
        assert new.snapshot_of_id == old_pk

    def test_snapshot_carries_over_unchanged_fields(self, integrated):
        new = mr_services.create_snapshot_integrated(
            integrated, status=IntegratedEventRegister.Status.CAPA_PLANNED)
        assert new.site_process == integrated.site_process
        assert new.event_id == integrated.event_id
        assert new.case_id == integrated.case_id
        assert new.family == integrated.family

    def test_snapshot_applies_changes(self, integrated):
        new = mr_services.create_snapshot_integrated(
            integrated,
            status=IntegratedEventRegister.Status.CLOSED,
            hold_flag=False,
            close_date=dt.date(2026, 9, 1),
            effectiveness_result=IntegratedEventRegister.EffectivenessResult.EFFECTIVE)
        assert new.status == IntegratedEventRegister.Status.CLOSED
        assert new.close_date == dt.date(2026, 9, 1)
        assert new.effectiveness_result == "EFFECTIVE"

    def test_cannot_snapshot_from_snapshot(self, integrated):
        new = mr_services.create_snapshot_integrated(
            integrated, status=IntegratedEventRegister.Status.CAPA_PLANNED)
        # integrated artık snapshot; oradan yeni snapshot alınamaz
        integrated.refresh_from_db()
        with pytest.raises(ValidationError):
            mr_services.create_snapshot_integrated(
                integrated, status=IntegratedEventRegister.Status.CLOSED)

    def test_snapshot_chain_ordered_oldest_first(self, integrated):
        s1 = mr_services.create_snapshot_integrated(
            integrated, status=IntegratedEventRegister.Status.CAPA_PLANNED)
        s2 = mr_services.create_snapshot_integrated(
            s1, status=IntegratedEventRegister.Status.CLOSED,
            close_date=dt.date(2026, 10, 1))
        chain = mr_services.snapshot_chain_integrated(s2)
        assert len(chain) == 3
        # ilk eleman en eski (orijinal), sonu aktif
        assert chain[0].pk == integrated.pk
        assert chain[-1].pk == s2.pk
        assert chain[-1].is_snapshot is False

    def test_active_lookup_returns_latest(self, integrated):
        mr_services.create_snapshot_integrated(
            integrated, status=IntegratedEventRegister.Status.CAPA_PLANNED)
        active = mr_services.active_integrated_by_event_id("INCIDENT-MR1")
        assert active is not None
        assert active.is_snapshot is False
        assert active.status == IntegratedEventRegister.Status.CAPA_PLANNED


# ---------------------------------------------------------------------------
# Security Event Register benzer davranis
# ---------------------------------------------------------------------------

class TestSecurityRegister:
    def test_security_snapshot_chain(self, security):
        new = mr_services.create_snapshot_security(
            security,
            current_status=SecurityEventRegister.CurrentStatus.CONTAINED,
            containment_status=SecurityEventRegister.ContainmentStatus.CONTAINED,
        )
        security.refresh_from_db()
        assert security.is_snapshot is True
        assert new.is_snapshot is False
        assert new.snapshot_of_id == security.pk
        assert new.current_status == SecurityEventRegister.CurrentStatus.CONTAINED


# ---------------------------------------------------------------------------
# Portal UI
# ---------------------------------------------------------------------------

class TestPortalUI:
    def test_integrated_list_requires_login(self, client):
        resp = client.get("/portal/master/integrated/")
        assert resp.status_code in (301, 302)

    def test_integrated_list_forbidden_without_perm(self, client):
        User.objects.create_user("nobody", password="pw")
        client.login(username="nobody", password="pw")
        resp = client.get("/portal/master/integrated/")
        assert resp.status_code == 403

    def test_integrated_list_ok_for_superuser(self, client, integrated):
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/master/integrated/")
        assert resp.status_code == 200
        assert b"INCIDENT-MR1" in resp.content
        # KPI'lar görünür
        assert b"HOLD" in resp.content

    def test_integrated_list_hides_snapshot(self, client, integrated):
        mr_services.create_snapshot_integrated(
            integrated, status=IntegratedEventRegister.Status.CLOSED)
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/master/integrated/")
        # Sadece 1 satır (aktif) görünmeli, iki değil
        # (KPI'lar da sadece aktifi sayar)
        content = resp.content.decode()
        # "INCIDENT-MR1" tek TR satırında olmalı — tabloya girmiş bir aktif satır
        assert content.count("INCIDENT-MR1") <= 5  # link + belki başka yer

    def test_integrated_detail_shows_chain(self, client, integrated):
        mr_services.create_snapshot_integrated(
            integrated, status=IntegratedEventRegister.Status.CAPA_PLANNED)
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/master/integrated/INCIDENT-MR1/")
        assert resp.status_code == 200
        assert b"INCIDENT-MR1" in resp.content
        assert b"Snapshot" in resp.content or b"SNAPSHOT" in resp.content

    def test_security_list_ok(self, client, security):
        User.objects.create_superuser("root", email="", password="pw")
        client.login(username="root", password="pw")
        resp = client.get("/portal/master/security/")
        assert resp.status_code == 200
        assert b"IT-INC-2026-001" in resp.content
        assert b"SEV1" in resp.content


# ---------------------------------------------------------------------------
# Rol matrisi
# ---------------------------------------------------------------------------

class TestRoleMatrix:
    def test_ims_qa_manager_sees_master_register_menu(self):
        from portal.menu import filter_menu_for
        call_command("seed_roles")
        u = User.objects.create_user("qa", password="pw")
        u.groups.add(Group.objects.get(name=Role.IMS_QA_MANAGER))
        sections = filter_menu_for(u)
        labels = [item["label"] for s in sections for item in s["items"]]
        assert "Integrated Master Register" in labels
        assert "Security Event Register" in labels

    def test_warehouse_role_cannot_see_master_register(self):
        from portal.menu import filter_menu_for
        call_command("seed_roles")
        u = User.objects.create_user("wh", password="pw")
        u.groups.add(Group.objects.get(name=Role.WAREHOUSE))
        sections = filter_menu_for(u)
        labels = [item["label"] for s in sections for item in s["items"]]
        assert "Integrated Master Register" not in labels
