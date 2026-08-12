"""EN 934 kapsamında tipik QC parametreleri ve ADX-100 için spec seed'i."""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from masterdata.models import Product
from quality.models import QCParameter, QCSpec


PARAMETERS = [
    # (code, name, unit, method)
    ("DENSITY", "Yoğunluk (20°C)", "g/cm³", QCParameter.Method.EN_ISO_758),
    ("PH", "pH", "", QCParameter.Method.EN_934_2),
    ("SOLIDS", "Katı madde", "%", QCParameter.Method.EN_480_8),
    ("CHLORIDE", "Klorür", "%", QCParameter.Method.EN_480_10),
    ("VISCOSITY", "Viskozite", "mPa·s", QCParameter.Method.INTERNAL),
]

# ADX-100 için tipik spec'ler (referans, gerçek üretim değerleriyle güncellenmeli)
ADX_100_SPECS = [
    # (code, min, max, target, mandatory)
    ("DENSITY", Decimal("1.05"), Decimal("1.15"), Decimal("1.10"), True),
    ("PH", Decimal("4.0"), Decimal("7.0"), Decimal("5.5"), True),
    ("SOLIDS", Decimal("35.0"), Decimal("42.0"), Decimal("38.0"), True),
    ("CHLORIDE", None, Decimal("0.10"), Decimal("0.01"), True),
    ("VISCOSITY", Decimal("30"), Decimal("150"), Decimal("80"), False),
]


class Command(BaseCommand):
    help = "QC parametreleri (EN 934) ve ADX-100 spec'lerini yükler (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        params: dict[str, QCParameter] = {}
        for code, name, unit, method in PARAMETERS:
            obj, _ = QCParameter.objects.update_or_create(
                code=code,
                defaults={"name": name, "unit": unit, "method": method, "is_active": True},
            )
            params[code] = obj

        product = Product.objects.filter(code="ADX-100").first()
        if product is None:
            self.stdout.write(self.style.WARNING(
                "ADX-100 ürünü bulunamadı. Önce `seed_demo` çalıştırın."
            ))
        else:
            for code, mn, mx, tgt, mand in ADX_100_SPECS:
                QCSpec.objects.update_or_create(
                    parameter=params[code], product=product,
                    defaults={
                        "min_value": mn, "max_value": mx,
                        "target_value": tgt, "is_mandatory": mand,
                    },
                )

        self.stdout.write(self.style.SUCCESS(
            f"QC seed tamam: {len(params)} parametre, "
            f"{QCSpec.objects.filter(product__code='ADX-100').count()} ADX-100 spec."
        ))
