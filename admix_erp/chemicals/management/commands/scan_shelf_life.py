"""Raf ömrü tarayıcı — cron ile günlük çalıştırılır.

Kullanım: python manage.py scan_shelf_life
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from chemicals.services import scan_shelf_life


class Command(BaseCommand):
    help = "Tüm hammadde lotlarının son kullanma tarihini tarar ve alert üretir."

    def handle(self, *args, **options) -> None:
        alerts = scan_shelf_life()
        by_sev: dict[str, int] = {}
        for a in alerts:
            by_sev[a.severity] = by_sev.get(a.severity, 0) + 1
        parts = [f"{k}={v}" for k, v in sorted(by_sev.items())]
        self.stdout.write(self.style.SUCCESS(
            f"Shelf life scan: {len(alerts)} new alerts. " +
            (" ".join(parts) if parts else "No expiring lots.")
        ))
