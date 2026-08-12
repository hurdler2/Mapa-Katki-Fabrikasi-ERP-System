"""4 BL olustur + mevcut master datayi MCS altina tasi (backfill).

Referans: MAPA-IMS-NAV-001 sec3 Business-Line Entry Points.

Kullanim:
    python manage.py seed_business_lines
    python manage.py seed_business_lines --backfill   # mevcut kayitlari MCS'e tasi
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from businessline.models import BusinessLine


BL_SEED = [
    {
        "code": "MCS",
        "name": "MAPA Concrete Solutions",
        "operational_scope": (
            "Kimyasal katki (KRMIX ailesi dahil) uretimi, fabrika QC, "
            "urun serbest birakma ve teknik destek. NAV-001 sec3."
        ),
        "typical_entry": "Production/batch event",
        "qc_independence": (
            "MCS Production QC Laboratory uretimden bagimsizdir; "
            "hammadde, proses, nihai urun ve parti serbest birakma "
            "kararlarini bagimsiz yurutur."
        ),
        "release_authority": (
            "Yetkili urun serbest birakma rolu; uretim veya ticari hedeflerden "
            "bagimsiz. HOLD/REJECT/RELEASE kararlari uretim baskisiyla "
            "gecersiz kilinamaz."
        ),
        "external_certifications": "ISO 9001, ISO 14001, ISO 45001, EN 934-2 CE marking",
    },
    {
        "code": "MPT",
        "name": "MAPA Precast Technologies",
        "operational_scope": (
            "Prefabrik beton uretim, curing, kaldirma, depolama ve sevkiyat."
        ),
        "typical_entry": "Precast order / pour",
        "qc_independence": (
            "MPT QC bagimsiz; boyutsal, gorunum, dayanim testleri uretimden ayri."
        ),
        "release_authority": "MPT Yetkili Release Rolu",
        "external_certifications": "ISO 9001, EN 13369, EN 13225",
    },
    {
        "code": "MFT",
        "name": "MAPA Formwork Technologies",
        "operational_scope": (
            "Celik, tunel ve ozel sac kalip sistemleri; muhendislik, imalat, "
            "montaj ve teknik servis."
        ),
        "typical_entry": "Formwork job / fabrication",
        "qc_independence": (
            "MFT QC; MTC/heat izlenebilirligi, teknik resim ve boyutsal "
            "uygunluk, kaynak/NDT, kaplama ve final imalat dosyasini "
            "uretimden bagimsiz dogrular."
        ),
        "release_authority": "MFT Yetkili Release Rolu",
        "external_certifications": "ISO 9001, EN 1090 (kaynakli celik yapilar)",
    },
    {
        "code": "MLTS",
        "name": "MAPA Laboratory & Technical Services",
        "operational_scope": (
            "Dis musterilere yonelik ticari test, deneysel calisma ve "
            "teknik danismanlik. Yapı malzemeleri ve beton teknolojileri."
        ),
        "typical_entry": "Contract / sample / method",
        "qc_independence": (
            "MLTS Commercial Laboratory tarafsizlik + gizlilik + metot "
            "yetkinligi kurallariyla ayri yetki matrisiyle calisir. "
            "Ticari veya uretim baskisi sonuclari degistiremez."
        ),
        "release_authority": (
            "MLTS Report Approval Role; ISO/IEC 17025 tarafsizlik esasli."
        ),
        "external_certifications": "ISO/IEC 17025 (hazirlik), ALGERAC akreditasyonu",
    },
]


class Command(BaseCommand):
    help = "4 BL seed'i + opsiyonel master data backfill (MCS'e tasi)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--backfill", action="store_true",
            help="business_line=NULL olan mevcut kayitlari MCS'e tasi (idempotent)."
        )

    @transaction.atomic
    def handle(self, *args, backfill: bool = False, **_) -> None:
        # 1. BL kayitlari
        created = updated = 0
        bl_map = {}
        for original_spec in BL_SEED:
            spec = dict(original_spec)  # kopya — module-level BL_SEED bozulmasin
            code = spec.pop("code")
            bl, was_created = BusinessLine.objects.update_or_create(
                code=code, defaults=spec,
            )
            bl_map[code] = bl
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f"BusinessLines: {created} new, {updated} updated."
        ))

        if not backfill:
            self.stdout.write("Backfill atlandi (--backfill ile calistirin).")
            return

        # 2. Backfill: mevcut kayitlari MCS'e tasi
        mcs = bl_map["MCS"]
        stats = self._backfill_to_mcs(mcs)
        for name, n in stats.items():
            self.stdout.write(f"  {name}: {n} kayit MCS'e tasindi")

    def _backfill_to_mcs(self, mcs) -> dict[str, int]:
        from masterdata.models import Product
        from formulation.models import Recipe
        from inventory.models import RawMaterialLot
        from production.models import ProductionOrder, ProductionBatch
        from purchasing.models import PurchaseOrder
        from sales.models import SalesOrder
        from quality.models import CertificateOfAnalysis
        from chemicals.models import SafetyDataSheet
        from cmms.models import Equipment
        from qms.models import Nonconformance, CAPA
        from docs.models import ControlledDocument

        stats = {}
        for name, qs in [
            ("Product", Product.objects.filter(business_line__isnull=True)),
            ("Recipe", Recipe.objects.filter(business_line__isnull=True)),
            ("RawMaterialLot", RawMaterialLot.objects.filter(business_line__isnull=True)),
            ("ProductionOrder", ProductionOrder.objects.filter(business_line__isnull=True)),
            ("ProductionBatch", ProductionBatch.objects.filter(business_line__isnull=True)),
            ("PurchaseOrder", PurchaseOrder.objects.filter(business_line__isnull=True)),
            ("SalesOrder", SalesOrder.objects.filter(business_line__isnull=True)),
            ("CertificateOfAnalysis", CertificateOfAnalysis.objects.filter(business_line__isnull=True)),
            ("SafetyDataSheet", SafetyDataSheet.objects.filter(business_line__isnull=True)),
            ("Equipment", Equipment.objects.filter(business_line__isnull=True)),
            ("Nonconformance", Nonconformance.objects.filter(business_line__isnull=True)),
            ("CAPA", CAPA.objects.filter(business_line__isnull=True)),
            ("ControlledDocument", ControlledDocument.objects.filter(business_line__isnull=True)),
        ]:
            n = qs.update(business_line=mcs)
            stats[name] = n
        return stats
