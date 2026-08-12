"""Ana sayfa hub + seed_all master komut testleri."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.urls import reverse


pytestmark = pytest.mark.django_db


def test_home_requires_login(client):
    resp = client.get("/")
    assert resp.status_code in (301, 302)  # login sayfasına yönlendirir


def test_home_redirects_authenticated_user_to_portal(client):
    """Faz 14 sonrası: / → /portal/ redirect (rol tabanlı dispatcher)."""
    User.objects.create_user("home_user", password="pw", is_staff=True)
    client.login(username="home_user", password="pw")
    resp = client.get("/")
    assert resp.status_code in (301, 302)
    assert "/portal/" in resp.url


def test_portal_dispatches_role_to_correct_dashboard(client):
    """Rol atanmış kullanıcı ilgili portala yönlendirilir."""
    from django.contrib.auth.models import Group
    call_command("seed_roles")
    u = User.objects.create_user("acc_test", password="pw", is_staff=True)
    u.groups.add(Group.objects.get(name="ACCOUNTING_MANAGER"))
    client.login(username="acc_test", password="pw")
    resp = client.get("/portal/")
    assert resp.status_code in (301, 302)
    assert "/portal/muhasebe/" in resp.url


def test_portal_no_role_shows_no_role_page(client):
    """Rolü olmayan kullanıcı 'rol yok' sayfası görür."""
    User.objects.create_user("norole", password="pw", is_staff=True)
    client.login(username="norole", password="pw")
    resp = client.get("/portal/")
    assert resp.status_code == 200
    assert b"rol" in resp.content.lower() or b"Rol" in resp.content


def test_seed_all_runs_all_seeds(db):
    """Master seed komutu tüm alt seed'leri sırayla çalıştırır."""
    call_command("seed_all", "--admin-password", "TestPw123!")
    from accounting.models import Account, FiscalYear, JournalCode, TVARate
    from cmms.models import CalibrationSchedule, Equipment, MaintenancePlan
    from chemicals.models import HazardStatement, Pictogram
    from ehs.models import LegalRequirement, PPEItem
    from formulation.models import Recipe
    from iam.models import Role
    from masterdata.models import Product, RawMaterial
    from quality.models import QCParameter

    # Roller
    assert Group.objects.filter(name=Role.IMS_QA_MANAGER).exists()
    # Master data
    assert Product.objects.filter(code="ADX-100").exists()
    assert RawMaterial.objects.filter(code="SP").exists()
    assert Recipe.objects.filter(product__code="ADX-100", is_active=True).exists()
    # QC
    assert QCParameter.objects.filter(code="DENSITY").exists()
    # GHS
    assert Pictogram.objects.filter(code="GHS05").exists()
    assert HazardStatement.objects.filter(code="H315").exists()
    # EHS
    assert PPEItem.objects.filter(code="KKD-EYE-01").exists()
    assert LegalRequirement.objects.filter(code="DZ-OHS-01").exists()
    # CMMS
    assert Equipment.objects.filter(equipment_number="EQ-REACT-1").exists()
    assert MaintenancePlan.objects.filter(plan_code="PM-BAL-01-W").exists()
    assert CalibrationSchedule.objects.filter(
        equipment__equipment_number="EQ-BAL-01").exists()
    # SCF
    assert Account.objects.filter(code="411").exists()
    assert TVARate.objects.filter(code="TVA19").exists()
    assert JournalCode.objects.filter(code="JV").exists()
    assert FiscalYear.objects.exists()
    # Admin user
    admin = User.objects.get(username="admin")
    assert admin.is_superuser and admin.is_staff


def test_seed_all_idempotent(db):
    """İkinci çağrı hata vermez, ekstra yeni kayıt yaratmaz."""
    call_command("seed_all")
    from masterdata.models import Product
    call_command("seed_all")
    assert Product.objects.filter(code="ADX-100").count() == 1
