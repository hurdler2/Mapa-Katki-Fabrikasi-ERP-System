"""SCADA entegrasyon endpoint'lerinin testleri."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from formulation.models import Recipe, RecipeLine
from masterdata.models import Container, Product, RawMaterial, UnitOfMeasure
from quality.models import QCParameter, QCSpec


pytestmark = pytest.mark.django_db


@pytest.fixture
def scada_user():
    """SCADA bridge user + tam yetki."""
    User = get_user_model()
    user = User.objects.create_user(
        username="scada_bridge_test", password="x",
        first_name="SCADA", last_name="Test",
    )
    group, _ = Group.objects.get_or_create(name="SCADA_BRIDGE")
    perms = Permission.objects.filter(
        content_type__app_label__in=["production", "quality", "formulation",
                                     "masterdata"],
    )
    group.permissions.set(perms)
    user.groups.add(group)
    return user


@pytest.fixture
def scada_token(scada_user):
    return Token.objects.create(user=scada_user)


@pytest.fixture
def scada_client(scada_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {scada_token.key}")
    return client


@pytest.fixture
def uom():
    return UnitOfMeasure.objects.get_or_create(
        code="kg", defaults={"name": "Kilogram"},
    )[0]


@pytest.fixture
def uom_l():
    return UnitOfMeasure.objects.get_or_create(
        code="l", defaults={"name": "Litre"},
    )[0]


@pytest.fixture
def product(uom):
    return Product.objects.create(code="ADX-100", name="Superplasticizer PCE",
                                  unit=uom)


@pytest.fixture
def reactor(uom_l):
    return Container.objects.create(
        code="R-01", name="Reactor 1", container_type=Container.ContainerType.REACTOR,
        capacity=Decimal("3000"), unit=uom_l,
    )


@pytest.fixture
def raw_materials(uom):
    return {
        "W": RawMaterial.objects.create(code="W", name="Su", unit=uom),
        "M1": RawMaterial.objects.create(code="M1", name="Monomer A", unit=uom),
        "M2": RawMaterial.objects.create(code="M2", name="Monomer B", unit=uom),
    }


@pytest.fixture
def active_recipe(product, uom, raw_materials, reactor):
    recipe = Recipe.objects.create(
        product=product, version=3, base_batch_size=Decimal("1000"),
        unit=uom, is_active=True,
    )
    RecipeLine.objects.create(
        recipe=recipe, sequence=1, raw_material=raw_materials["W"],
        quantity=Decimal("600"), tolerance_pct=Decimal("0.5"),
        is_complement=True,
    )
    RecipeLine.objects.create(
        recipe=recipe, sequence=2, raw_material=raw_materials["M1"],
        quantity=Decimal("250"), tolerance_pct=Decimal("0.5"),
    )
    RecipeLine.objects.create(
        recipe=recipe, sequence=3, raw_material=raw_materials["M2"],
        quantity=Decimal("150"), tolerance_pct=Decimal("0.5"),
    )
    return recipe


@pytest.fixture
def qc_params():
    ph = QCParameter.objects.create(code="PH", name="pH", unit="")
    temp = QCParameter.objects.create(code="TEMP", name="Sıcaklık", unit="°C")
    cl = QCParameter.objects.create(code="CHLORIDE", name="Klor", unit="ppm")
    return {"PH": ph, "TEMP": temp, "CHLORIDE": cl}


# ===========================================================================
# 1) POST /batches/from-scada/
# ===========================================================================

def test_scada_post_batch_creates_records(
    scada_client, active_recipe, raw_materials, qc_params, reactor,
):
    payload = {
        "batch_number": "BATCH-20260915-042",
        "recipe_code": "ADX-100-v3",
        "target_kg": 1000.0,
        "actual_kg": 999.7,
        "started_at": "2026-09-15T14:23:07Z",
        "completed_at": "2026-09-15T15:03:12Z",
        "operator": "Mohamed Belaidi",
        "consumptions": [
            {"code": "W", "target": 600.0, "actual": 600.2},
            {"code": "M1", "target": 250.0, "actual": 249.8},
            {"code": "M2", "target": 150.0, "actual": 150.1},
        ],
        "qc_results": [
            {"parameter": "PH", "value": 5.8, "verdict": "PASS"},
            {"parameter": "TEMP", "value": 32.5, "verdict": "PASS"},
            {"parameter": "CHLORIDE", "value": 245.0, "verdict": "PASS"},
        ],
    }
    r = scada_client.post(
        "/api/v1/production/batches/from-scada/", payload, format="json",
    )
    assert r.status_code == 201
    data = r.json()
    assert data["batch_number"] == "BATCH-20260915-042"
    assert len(data["consumption_ids"]) == 3
    assert len(data["qc_result_ids"]) == 3

    from production.models import ProductionBatch
    b = ProductionBatch.objects.get(batch_number="BATCH-20260915-042")
    assert b.actual_qty == Decimal("999.7")
    assert b.operator == "Mohamed Belaidi"


def test_scada_post_batch_idempotent(
    scada_client, active_recipe, raw_materials, qc_params, reactor,
):
    payload = {
        "batch_number": "BATCH-DUP-01",
        "recipe_code": "ADX-100-v3",
        "target_kg": 1000.0,
        "actual_kg": 1000.0,
        "started_at": "2026-09-15T14:00:00Z",
        "completed_at": "2026-09-15T14:30:00Z",
        "consumptions": [],
        "qc_results": [],
    }
    r1 = scada_client.post(
        "/api/v1/production/batches/from-scada/", payload, format="json",
    )
    assert r1.status_code == 201

    # İkinci POST — aynı batch_number
    r2 = scada_client.post(
        "/api/v1/production/batches/from-scada/", payload, format="json",
    )
    assert r2.status_code == 200
    assert r2.json()["duplicate"] is True


def test_scada_post_missing_fields_400(scada_client):
    r = scada_client.post(
        "/api/v1/production/batches/from-scada/",
        {"batch_number": "X"},
        format="json",
    )
    assert r.status_code == 400
    assert "Zorunlu alan eksik" in r.json()["error"]


def test_scada_post_unknown_recipe_404(scada_client, reactor):
    payload = {
        "batch_number": "BATCH-X",
        "recipe_code": "UNKNOWN-v99",
        "target_kg": 1000.0,
        "actual_kg": 1000.0,
        "started_at": "2026-09-15T14:00:00Z",
    }
    r = scada_client.post(
        "/api/v1/production/batches/from-scada/", payload, format="json",
    )
    assert r.status_code == 404


def test_scada_post_no_auth_401():
    """Token olmadan istek reddedilir."""
    client = APIClient()
    r = client.post(
        "/api/v1/production/batches/from-scada/",
        {"batch_number": "X"}, format="json",
    )
    assert r.status_code in (401, 403)


# ===========================================================================
# 2) GET /active-recipe/
# ===========================================================================

def test_scada_get_active_recipe(scada_client, active_recipe, raw_materials):
    r = scada_client.get("/api/v1/production/active-recipe/")
    assert r.status_code == 200
    data = r.json()
    assert data["product_code"] == "ADX-100"
    assert data["version"] == 3
    assert data["recipe_code"] == "ADX-100-v3"
    assert data["base_batch_size"] == 1000.0
    assert len(data["lines"]) == 3
    # Su satırı complement bayraklı gelmeli
    water_line = next(l for l in data["lines"] if l["code"] == "W")
    assert water_line["is_complement"] is True


def test_scada_get_active_recipe_with_product_code(
    scada_client, active_recipe,
):
    r = scada_client.get(
        "/api/v1/production/active-recipe/", {"product_code": "ADX-100"},
    )
    assert r.status_code == 200
    assert r.json()["product_code"] == "ADX-100"


def test_scada_get_active_recipe_not_found(scada_client):
    r = scada_client.get("/api/v1/production/active-recipe/")
    assert r.status_code == 404


# ===========================================================================
# 3) GET /scada/status/
# ===========================================================================

def test_scada_status_healthy(scada_client):
    r = scada_client.get("/api/v1/production/scada/status/")
    assert r.status_code == 200
    data = r.json()
    assert data["erp_status"] == "OK"
    assert "server_time" in data
    assert data["authenticated_as"] == "scada_bridge_test"
    assert "stats" in data
    assert data["stats"]["scada_batches_today"] == 0
    assert data["recent_batches"] == []


def test_scada_status_after_batch(
    scada_client, active_recipe, raw_materials, qc_params, reactor,
):
    # 1 batch POST et
    scada_client.post(
        "/api/v1/production/batches/from-scada/",
        {
            "batch_number": "BATCH-STATUS-01",
            "recipe_code": "ADX-100-v3",
            "target_kg": 1000.0,
            "actual_kg": 998.0,
            "started_at": "2026-09-15T14:00:00Z",
            "completed_at": "2026-09-15T14:30:00Z",
        },
        format="json",
    )
    r = scada_client.get("/api/v1/production/scada/status/")
    data = r.json()
    assert data["stats"]["scada_batches_today"] == 1
    assert len(data["recent_batches"]) == 1
    assert data["recent_batches"][0]["batch_number"] == "BATCH-STATUS-01"
