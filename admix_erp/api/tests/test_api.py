"""REST API testleri: JWT auth + kritik endpoint'ler + trace action'ları."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_user(db):
    return User.objects.create_user("api_user", password="secret123",
                                     is_staff=True)


@pytest.fixture
def api_client(api_user):
    client = APIClient()
    # JWT token al
    resp = client.post(
        reverse("token_obtain_pair"),
        {"username": "api_user", "password": "secret123"}, format="json",
    )
    assert resp.status_code == 200
    token = resp.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def test_jwt_auth_flow(db):
    User.objects.create_user("jwt_u", password="pw")
    c = APIClient()
    r = c.post(reverse("token_obtain_pair"),
               {"username": "jwt_u", "password": "pw"}, format="json")
    assert r.status_code == 200
    assert "access" in r.json() and "refresh" in r.json()


def test_unauthenticated_returns_401():
    c = APIClient()
    r = c.get("/api/v1/products/")
    assert r.status_code == 401


def test_list_products_via_api(api_client, product):
    r = api_client.get("/api/v1/products/")
    assert r.status_code == 200
    data = r.json()
    codes = [p["code"] for p in data["results"]]
    assert "ADX-100" in codes


def test_create_customer_via_api(api_client):
    r = api_client.post("/api/v1/customers/", {
        "code": "CUS-API-1", "name": "API Test Müşteri",
        "contact": "", "tax_no": "", "is_active": True,
    }, format="json")
    assert r.status_code == 201
    from masterdata.models import Customer
    assert Customer.objects.filter(code="CUS-API-1").exists()


def test_batch_backward_trace_action(api_client, order, released_lots):
    from production.services import create_batch_from_order, record_dosing
    batch = create_batch_from_order(order, batch_number="BATCH-API-1")
    c = batch.consumptions.get(raw_material__code="SP")
    record_dosing(c, actual_weight=Decimal("175"))

    r = api_client.get(f"/api/v1/batches/{batch.pk}/backward-trace/")
    assert r.status_code == 200
    body = r.json()
    assert body["batch_number"] == "BATCH-API-1"
    codes = {i["raw_material"] for i in body["consumptions"]}
    assert "SP" in codes


def test_lot_forward_trace_action(api_client, order, released_lots, ibc):
    from production.models import OutputContainer
    from production.services import create_batch_from_order, record_dosing
    batch = create_batch_from_order(order, batch_number="BATCH-API-FWD")
    c = batch.consumptions.get(raw_material__code="SP")
    record_dosing(c, actual_weight=Decimal("175"))
    OutputContainer.objects.create(batch=batch, container=ibc,
                                     quantity=Decimal("500"))

    lot_id = released_lots["SP"].pk
    r = api_client.get(f"/api/v1/lots/{lot_id}/forward-trace/")
    assert r.status_code == 200
    body = r.json()
    assert body["lot_number"] == "LOT-SP-001"
    assert len(body["batches"]) == 1
