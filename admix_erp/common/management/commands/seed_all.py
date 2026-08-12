"""Master seed komutu — tüm örnek verileri ve referansları tek elden yükler.

Kullanım:
    python manage.py seed_all
    python manage.py seed_all --admin-password Secret123!  # otomatik superuser
"""
from __future__ import annotations

import datetime as dt

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction


SEED_SEQUENCE = [
    ("seed_roles", "User roles (13 groups)"),
    ("seed_demo", "Master data + ADX-100 recipe"),
    ("seed_qc", "QC parameters (EN 934)"),
    ("seed_ghs", "GHS pictograms + H/P + hazard incompatibility"),
    ("seed_ehs", "PPE items + Algerian legal references"),
    ("seed_equipment", "Equipment + PM + calibration schedules"),
    ("seed_scf", "Algerian SCF chart of accounts + TVA + journals"),
]


class Command(BaseCommand):
    help = "Tüm modüller için başlangıç seed'lerini tek komutla yükler."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--admin-username", default="admin",
            help="Oluşturulacak superuser kullanıcı adı",
        )
        parser.add_argument(
            "--admin-password", default=None,
            help="Verilirse superuser otomatik oluşturulur/güncellenir",
        )
        parser.add_argument(
            "--fiscal-year", type=int, default=None,
            help="Oluşturulacak mali yıl (varsayılan: cari yıl)",
        )

    @transaction.atomic
    def handle(self, *args, admin_username, admin_password,
               fiscal_year, **_) -> None:
        for cmd, desc in SEED_SEQUENCE:
            self.stdout.write(f"->{cmd} ({desc})")
            call_command(cmd)

        # Mali yıl (accounting)
        from accounting.models import FiscalYear
        year = fiscal_year or dt.date.today().year
        fy, created = FiscalYear.objects.get_or_create(
            year=year,
            defaults={
                "start_date": dt.date(year, 1, 1),
                "end_date": dt.date(year, 12, 31),
            },
        )
        self.stdout.write(
            f"->FiscalYear {year} " + ("created" if created else "exists")
        )

        # Opsiyonel superuser
        if admin_password:
            user, u_created = User.objects.get_or_create(
                username=admin_username,
                defaults={"is_staff": True, "is_superuser": True},
            )
            user.is_staff = True
            user.is_superuser = True
            user.set_password(admin_password)
            user.save()
            self.stdout.write(
                f"->Superuser '{admin_username}' " +
                ("created" if u_created else "updated")
            )

        self.stdout.write(self.style.SUCCESS("All seeds completed."))
