"""Standart PPE kalemleri + tipik Cezayir yasal referansları seed'i."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from ehs.models import LegalRequirement, PPEItem


PPE_ITEMS = [
    ("KKD-HEAD-01", "Baret", PPEItem.Category.HEAD, "EN 397", 730),
    ("KKD-EYE-01", "Kimyasal koruma gözlüğü", PPEItem.Category.EYE, "EN 166 3", 365),
    ("KKD-EAR-01", "Kulak tıkacı", PPEItem.Category.EAR, "EN 352-2 SNR 33dB", 30),
    ("KKD-RESP-01", "Yarım yüz maske (A2P3)", PPEItem.Category.RESPIRATORY,
        "EN 140 / EN 14387 A2P3", 90),
    ("KKD-HAND-01", "Nitril kimyasal eldiven", PPEItem.Category.HAND,
        "EN 374 / EN 388", 30),
    ("KKD-HAND-02", "Neopren asit eldiveni", PPEItem.Category.HAND,
        "EN 374 J-K-L", 60),
    ("KKD-FOOT-01", "Kimyasal koruma çizmesi (PVC)", PPEItem.Category.FOOT,
        "EN 13832-3", 365),
    ("KKD-FOOT-02", "S3 iş güvenlik ayakkabısı", PPEItem.Category.FOOT,
        "EN ISO 20345 S3", 365),
    ("KKD-BODY-01", "Kimyasal tulum (Tip 4)", PPEItem.Category.BODY,
        "EN 14605 / EN 13034", None),
    ("KKD-FALL-01", "Paraşüt tipi kemer", PPEItem.Category.FALL_PROTECTION,
        "EN 361", 730),
]


LEGAL_REQUIREMENTS = [
    ("DZ-OHS-01", "Loi n° 88-07 du 26 janvier 1988",
        "Hygiène, sécurité et médecine du travail", "OHS",
        "İşyerinde hijyen, güvenlik ve iş hekimliği zorunluluğu"),
    ("DZ-ENV-01", "Loi n° 03-10 du 19 juillet 2003",
        "Protection de l'environnement dans le cadre du développement durable",
        "ENV",
        "Sürdürülebilir kalkınma çerçevesinde çevrenin korunması"),
    ("DZ-ENV-02", "Décret exécutif n° 06-198 du 31 mai 2006",
        "Cadre réglementaire des installations classées pour la protection "
        "de l'environnement (ICPE)", "ENV",
        "Sınıflandırılmış tesislere yönetmelik çerçevesi"),
    ("DZ-CHEM-01", "Décret exécutif n° 03-451 du 1er décembre 2003",
        "Réglementation des substances chimiques dangereuses", "CHEMICAL",
        "Tehlikeli kimyasalların düzenlenmesi"),
    ("DZ-LAB-01", "Loi n° 90-11 du 21 avril 1990",
        "Relations de travail", "LABOR",
        "Çalışma ilişkileri kanunu"),
    ("EN-934-2", "EN 934-2:2009+A1:2012",
        "Concrete admixtures — definitions, requirements, conformity, marking",
        "CHEMICAL",
        "AB standardı — beton katkısı ürün uygunluk"),
]


class Command(BaseCommand):
    help = "Standart PPE kalemleri ve Cezayir yasal yükümlülükleri seed'i."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        for code, name, cat, std, days in PPE_ITEMS:
            PPEItem.objects.update_or_create(
                code=code,
                defaults={
                    "name": name, "category": cat, "standard": std,
                    "replacement_days": days, "is_active": True,
                },
            )
        for code, ref, title, dom, desc in LEGAL_REQUIREMENTS:
            LegalRequirement.objects.update_or_create(
                code=code,
                defaults={
                    "reference": ref, "title": title, "domain": dom,
                    "description": desc, "compliance_status":
                        LegalRequirement.Status.PENDING,
                },
            )

        self.stdout.write(self.style.SUCCESS(
            f"EHS seed: {PPEItem.objects.count()} PPE items, "
            f"{LegalRequirement.objects.count()} legal requirements."
        ))
