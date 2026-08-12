"""Ortak fixtures: temel master data + reçete + lotlar + emir."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from formulation.models import Recipe, RecipeLine
from inventory.models import RawMaterialLot
from masterdata.models import Container, Product, RawMaterial, Supplier, UnitOfMeasure
from production.models import ProductionOrder


@pytest.fixture
def uom_kg(db):
    return UnitOfMeasure.objects.create(code="kg", name="Kilogram")


@pytest.fixture
def uom_l(db):
    return UnitOfMeasure.objects.create(code="L", name="Litre")


@pytest.fixture
def supplier(db):
    return Supplier.objects.create(code="SUP-001", name="Test Kimya A.Ş.")


@pytest.fixture
def raws(uom_kg, uom_l):
    return {
        "W": RawMaterial.objects.create(
            code="W", name="Su", material_type=RawMaterial.MaterialType.WATER, unit=uom_l
        ),
        "G": RawMaterial.objects.create(
            code="G", name="Glukonat", material_type=RawMaterial.MaterialType.RETARDER, unit=uom_kg
        ),
        "SP": RawMaterial.objects.create(
            code="SP", name="PCE", material_type=RawMaterial.MaterialType.SUPERPLASTICIZER, unit=uom_kg
        ),
        "HD": RawMaterial.objects.create(
            code="HD", name="HD", material_type=RawMaterial.MaterialType.ADDITIVE, unit=uom_kg
        ),
    }


@pytest.fixture
def reactor(uom_l):
    return Container.objects.create(
        code="REACTOR-1", name="Reaktör 1",
        container_type=Container.ContainerType.REACTOR,
        capacity=Decimal("2000"), unit=uom_l,
    )


@pytest.fixture
def ibc(uom_l):
    return Container.objects.create(
        code="IBC-OUT-01", name="Mamul IBC 01",
        container_type=Container.ContainerType.IBC,
        capacity=Decimal("1000"), unit=uom_l,
    )


@pytest.fixture
def product(uom_kg):
    return Product.objects.create(code="ADX-100", name="ADX-100", unit=uom_kg)


@pytest.fixture
def recipe(product, uom_kg, raws):
    r = Recipe.objects.create(
        product=product, version=1, base_batch_size=Decimal("1000"),
        unit=uom_kg, is_active=True,
    )
    RecipeLine.objects.create(recipe=r, sequence=1, raw_material=raws["W"], quantity=Decimal("600"), tolerance_pct=Decimal("0.50"))
    RecipeLine.objects.create(recipe=r, sequence=2, raw_material=raws["G"], quantity=Decimal("15"), tolerance_pct=Decimal("1.00"))
    RecipeLine.objects.create(recipe=r, sequence=3, raw_material=raws["SP"], quantity=Decimal("350"), tolerance_pct=Decimal("0.50"))
    RecipeLine.objects.create(recipe=r, sequence=4, raw_material=raws["HD"], quantity=Decimal("35"), tolerance_pct=Decimal("1.00"))
    return r


@pytest.fixture
def order(product, recipe, uom_kg, reactor):
    return ProductionOrder.objects.create(
        order_number="PO-001", product=product, recipe=recipe,
        target_qty=Decimal("500"), unit=uom_kg, reactor=reactor,
    )


@pytest.fixture
def released_lots(raws, supplier):
    """Her hammadde için RELEASED, bol miktarlı, yakın tarihli tek lot."""
    lots = {}
    today = dt.date.today()
    plans = [
        ("W", "LOT-W-001", Decimal("5000"), Decimal("0.10")),
        ("G", "LOT-G-001", Decimal("500"), Decimal("8.00")),
        ("SP", "LOT-SP-001", Decimal("2000"), Decimal("4.00")),
        ("HD", "LOT-HD-001", Decimal("500"), Decimal("12.00")),
    ]
    for code, lot_no, qty, cost in plans:
        lots[code] = RawMaterialLot.objects.create(
            lot_number=lot_no, raw_material=raws[code], supplier=supplier,
            received_date=today, expiry_date=today + dt.timedelta(days=180),
            received_qty=qty, remaining_qty=qty,
            qc_status=RawMaterialLot.QCStatus.RELEASED,
            coa_reference=f"COA-{lot_no}",
            unit_cost=cost,
        )
    return lots
