"""Cezayir fabrikası organizasyonuna uygun 10 demo kullanıcı.

Kullanım: python manage.py seed_demo_users
Tüm demo kullanıcı parolası: Demo123!
"""
from __future__ import annotations

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

from iam.models import Role


DEMO_USERS = [
    # username, ad, soyad, unvan, rol(ler)
    ("gm.director",     "Karim",   "Bouzid",   "Genel Mudur",         [Role.GENERAL_MANAGER]),
    ("tm.director",     "Yassine", "Cherif",   "Teknik Mudur",        [Role.TECHNICAL_MANAGER]),
    ("op.manager",      "Amina",   "Belkacem", "Operasyon Muduru",    [Role.OPERATIONS_MANAGER]),
    ("qa.manager",      "Zeynep",  "Demir",    "IMS QA Muduru",       [Role.IMS_QA_MANAGER]),
    ("acc.manager",     "Ahmet",   "Kaya",     "Muhasebe Muduru",     [Role.ACCOUNTING_MANAGER]),
    ("lab.tech",        "Ayse",    "Arslan",   "Laboratuvar Uzmani",  [Role.LAB_QC]),
    ("shift.supervisor","Ali",     "Yildiz",   "Vardiya Supervizoru", [Role.OPERATIONS_SUPERVISOR]),
    ("warehouse.chief", "Fatma",   "Sahin",    "Depo Sefi",           [Role.WAREHOUSE]),
    ("purchase.officer","Kemal",   "Dogan",    "Satin Alma Sorumlusu",[Role.PURCHASING]),
    ("it.admin",        "Mustafa", "Ilmaz",    "BT Yoneticisi",       [Role.IT_ADMIN]),
]

# Eski kullanıcılar temizlenecek (yeni rol sistemine geçiş)
STALE_USERS = [
    "ahmet.kaya", "zeynep.demir", "mehmet.ozturk", "fatma.sahin",
    "ali.yildiz", "ayse.arslan", "hasan.aydin", "elif.polat",
    "kemal.dogan", "nur.celik", "okan.yilmaz", "sibel.can",
    "muhasebeci",
]


class Command(BaseCommand):
    help = "9 organizasyonel rol icin ornek demo kullanicilar (Demo123!)."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        # Eski demo kullanıcıları temizle
        User.objects.filter(username__in=STALE_USERS).delete()

        created = 0
        updated = 0
        for username, first, last, title, roles in DEMO_USERS:
            u, was_created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first, "last_name": last, "is_staff": True},
            )
            u.first_name, u.last_name = first, last
            u.is_staff = True
            u.set_password("Demo123!")
            u.save()
            groups = [Group.objects.get(name=r) for r in roles]
            u.groups.set(groups)
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Demo users: {len(DEMO_USERS)} total ({created} new, {updated} updated). "
            f"Password: Demo123!"
        ))
