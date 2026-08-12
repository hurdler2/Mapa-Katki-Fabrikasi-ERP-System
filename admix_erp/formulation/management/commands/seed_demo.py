"""Örnek veri yükleyici.

Kullanım: python manage.py seed_demo
- Ölçü birimleri (kg, L)
- Hammaddeler: W, G, SP, HD
- Kaplar: TANK-W1, IBC-SP-01, REACTOR-1, IBC-OUT-01
- Ürün: ADX-100
- Reçete v1 (aktif) ve satırları
- 1 tedarikçi
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from formulation.models import Recipe, RecipeLine
from masterdata.models import (
    Container,
    Customer,
    Product,
    RawMaterial,
    Supplier,
    UnitOfMeasure,
)


class Command(BaseCommand):
    help = "Örnek master data + reçete yükler (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        kg, _ = UnitOfMeasure.objects.get_or_create(code="kg", defaults={"name": "Kilogram"})
        litre, _ = UnitOfMeasure.objects.get_or_create(code="L", defaults={"name": "Litre"})

        # Hammaddeler
        rm_defs = [
            ("W", "Su", RawMaterial.MaterialType.WATER, litre, Decimal("1.0000")),
            ("G", "Sodyum glukonat", RawMaterial.MaterialType.RETARDER, kg, None),
            ("SP", "Süperplastikleştirici (PCE)", RawMaterial.MaterialType.SUPERPLASTICIZER, kg, Decimal("1.0800")),
            ("HD", "Katkı bileşeni", RawMaterial.MaterialType.ADDITIVE, kg, None),
        ]
        raws: dict[str, RawMaterial] = {}
        for code, name, mtype, unit, density in rm_defs:
            obj, _ = RawMaterial.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "material_type": mtype,
                    "unit": unit,
                    "density": density,
                    "shelf_life_days": 365,
                    "is_active": True,
                },
            )
            raws[code] = obj

        # Kaplar
        containers = [
            ("TANK-W1", "Su tankı", Container.ContainerType.TANK, Decimal("10000.0000"), litre),
            ("IBC-SP-01", "SP IBC 01", Container.ContainerType.IBC, Decimal("1000.0000"), litre),
            ("REACTOR-1", "Reaktör 1", Container.ContainerType.REACTOR, Decimal("2000.0000"), litre),
            ("IBC-OUT-01", "Mamul IBC 01", Container.ContainerType.IBC, Decimal("1000.0000"), litre),
        ]
        for code, name, ctype, cap, unit in containers:
            Container.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "container_type": ctype,
                    "capacity": cap,
                    "unit": unit,
                    "is_active": True,
                },
            )

        # Ürün
        product, _ = Product.objects.update_or_create(
            code="ADX-100",
            defaults={
                "name": "ADX-100 Süperplastikleştirici Katkı",
                "unit": kg,
                "description": "Örnek beton katkı mamulü.",
                "is_active": True,
            },
        )

        # Tedarikçi + Müşteri
        Supplier.objects.update_or_create(
            code="SUP-001",
            defaults={"name": "Örnek Kimya A.Ş.", "contact": "info@ornek.com", "is_active": True},
        )
        Customer.objects.update_or_create(
            code="CUS-001",
            defaults={"name": "Beton İnşaat Ltd.", "contact": "satinalma@beton.com", "is_active": True},
        )

        # Reçete v1 (aktif) — base_batch_size = 1000 kg
        recipe, created = Recipe.objects.get_or_create(
            product=product,
            version=1,
            defaults={
                "base_batch_size": Decimal("1000.0000"),
                "unit": kg,
                "is_active": True,
                "notes": "Örnek reçete v1.",
            },
        )
        if created or not recipe.lines.exists():
            recipe.lines.all().delete()
            line_defs = [
                (1, raws["W"], Decimal("600.0000"), Decimal("0.50")),
                (2, raws["G"], Decimal("15.0000"), Decimal("1.00")),
                (3, raws["SP"], Decimal("350.0000"), Decimal("0.50")),
                (4, raws["HD"], Decimal("35.0000"), Decimal("1.00")),
            ]
            for seq, rm, qty, tol in line_defs:
                RecipeLine.objects.create(
                    recipe=recipe, sequence=seq, raw_material=rm, quantity=qty, tolerance_pct=tol
                )

        self.stdout.write(self.style.SUCCESS("Seed tamam: ADX-100 v1 reçete + master data yüklendi."))
