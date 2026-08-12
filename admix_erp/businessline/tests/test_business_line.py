"""Faz A tests — BusinessLine model, backfill, rol scope, portal integrasyonu."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import RequestFactory
from django.urls import reverse

from businessline.models import BusinessLine, RoleBusinessLineScope
from businessline.services import (
    business_lines_for,
    get_active_bl,
    set_active_bl_code,
    user_has_bl_access,
)


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def test_business_line_unique_code():
    BusinessLine.objects.create(
        code="MCS", name="MAPA Concrete Solutions",
        operational_scope="Kimyasal katki",
    )
    with pytest.raises(Exception):
        BusinessLine.objects.create(
            code="MCS", name="Duplicate",
            operational_scope="X",
        )


def test_business_line_choices_restrict_code():
    """MCS/MPT/MFT/MLTS dışı kod yasak — model tanımı Choices ile enforce."""
    bl = BusinessLine(code="ZZZ", name="Invalid", operational_scope="X")
    with pytest.raises(Exception):
        bl.full_clean()


def test_seed_business_lines_creates_four(db):
    call_command("seed_business_lines")
    codes = set(BusinessLine.objects.values_list("code", flat=True))
    assert codes == {"MCS", "MPT", "MFT", "MLTS"}


def test_seed_business_lines_idempotent(db):
    call_command("seed_business_lines")
    call_command("seed_business_lines")
    assert BusinessLine.objects.filter(code="MCS").count() == 1


# ---------------------------------------------------------------------------
# Backfill: mevcut master data MCS'e taşınır
# ---------------------------------------------------------------------------

def test_backfill_moves_existing_products_to_mcs(db):
    from masterdata.models import Product, UnitOfMeasure
    unit = UnitOfMeasure.objects.create(code="kg", name="Kilogram")
    p = Product.objects.create(code="ADX-100", name="ADX 100", unit=unit)
    assert p.business_line_id is None

    call_command("seed_business_lines", "--backfill")

    p.refresh_from_db()
    assert p.business_line is not None
    assert p.business_line.code == "MCS"


def test_backfill_does_not_touch_already_assigned(db):
    from masterdata.models import Product, UnitOfMeasure
    call_command("seed_business_lines")
    mpt = BusinessLine.objects.get(code="MPT")
    unit = UnitOfMeasure.objects.create(code="kg", name="Kilogram")
    p = Product.objects.create(code="PRECAST-01", name="Precast", unit=unit,
                                 business_line=mpt)

    call_command("seed_business_lines", "--backfill")

    p.refresh_from_db()
    assert p.business_line == mpt  # değişmedi


# ---------------------------------------------------------------------------
# Rol × BL Scope
# ---------------------------------------------------------------------------

def test_business_lines_for_no_scope_returns_all(db):
    """Hiç RoleBusinessLineScope yok → geçiş dönemi → tüm BL'ler."""
    call_command("seed_business_lines")
    u = User.objects.create_user("op", password="pw")
    bls = business_lines_for(u)
    assert bls.count() == 4


def test_business_lines_for_scoped_user_returns_only_scoped(db):
    call_command("seed_business_lines")
    g = Group.objects.create(name="OP_MCS")
    mcs = BusinessLine.objects.get(code="MCS")
    RoleBusinessLineScope.objects.create(group=g, business_line=mcs)

    u = User.objects.create_user("op_mcs", password="pw")
    u.groups.add(g)

    bls = business_lines_for(u)
    assert bls.count() == 1
    assert bls.first().code == "MCS"


def test_superuser_sees_all_business_lines(db):
    call_command("seed_business_lines")
    su = User.objects.create_superuser("root", password="pw")
    bls = business_lines_for(su)
    assert bls.count() == 4


def test_user_has_bl_access_denied_for_unscoped(db):
    call_command("seed_business_lines")
    g = Group.objects.create(name="OP_MPT")
    mpt = BusinessLine.objects.get(code="MPT")
    RoleBusinessLineScope.objects.create(group=g, business_line=mpt)

    u = User.objects.create_user("op_mpt", password="pw")
    u.groups.add(g)

    assert user_has_bl_access(u, mpt) is True
    mcs = BusinessLine.objects.get(code="MCS")
    assert user_has_bl_access(u, mcs) is False


def test_user_has_bl_access_none_target_always_true(db):
    """business_line=None (geçiş dönemi) → herkese erişim var."""
    u = User.objects.create_user("op", password="pw")
    assert user_has_bl_access(u, None) is True


# ---------------------------------------------------------------------------
# Session BL selector
# ---------------------------------------------------------------------------

def test_switch_business_line_sets_session(client, db):
    call_command("seed_business_lines")
    User.objects.create_user("u", password="pw")
    client.login(username="u", password="pw")

    resp = client.post(reverse("portal:switch_bl"), {"bl_code": "MCS"})
    assert resp.status_code in (301, 302)
    assert client.session["active_bl_code"] == "MCS"


def test_switch_business_line_clears_session(client, db):
    call_command("seed_business_lines")
    User.objects.create_user("u", password="pw")
    client.login(username="u", password="pw")
    session = client.session
    session["active_bl_code"] = "MCS"
    session.save()

    client.post(reverse("portal:switch_bl"), {"bl_code": ""})
    assert "active_bl_code" not in client.session


def test_switch_business_line_denies_unauthorized_bl(client, db):
    call_command("seed_business_lines")
    g = Group.objects.create(name="OP_MCS_ONLY")
    RoleBusinessLineScope.objects.create(
        group=g, business_line=BusinessLine.objects.get(code="MCS"))
    u = User.objects.create_user("u", password="pw")
    u.groups.add(g)
    client.login(username="u", password="pw")

    # MPT'ye geçmeye çalış — reddedilir
    client.post(reverse("portal:switch_bl"), {"bl_code": "MPT"})
    assert "active_bl_code" not in client.session


# ---------------------------------------------------------------------------
# Portal integrasyonu: sidebar'da available_business_lines görünür
# ---------------------------------------------------------------------------

def test_portal_context_includes_business_lines(client, db, settings):
    settings.MCOS_ENABLE_BUSINESSLINE = True
    call_command("seed_roles")
    call_command("seed_business_lines")
    u = User.objects.create_user("u", password="pw", is_staff=True)
    u.groups.add(Group.objects.get(name="ACCOUNTING_MANAGER"))
    client.login(username="u", password="pw")

    resp = client.get("/portal/muhasebe/")
    assert resp.status_code == 200
    # BL selector formu ve MCS opsiyon içerikte
    content = resp.content.decode("utf-8")
    assert "İş Kolu" in content
    assert "MCS" in content


def test_portal_context_hidden_when_flag_disabled(client, db, settings):
    settings.MCOS_ENABLE_BUSINESSLINE = False
    call_command("seed_roles")
    call_command("seed_business_lines")
    u = User.objects.create_user("u", password="pw", is_staff=True)
    u.groups.add(Group.objects.get(name="ACCOUNTING_MANAGER"))
    client.login(username="u", password="pw")

    resp = client.get("/portal/muhasebe/")
    assert resp.status_code == 200
    # Feature flag kapalı iken selector görünmez
    assert 'name="bl_code"' not in resp.content.decode("utf-8")
