"""LIMS'ten bekleyen sonuçları çeker ve QC test sonuçlarına işler.

Kullanım: python manage.py lims_pull --endpoint LAB-1
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from lims.models import LimsEndpoint
from lims.services import pull_results


class Command(BaseCommand):
    help = "LIMS'ten bekleyen QC sonuçlarını çeker ve ERP'ye işler."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--endpoint", required=True, help="LimsEndpoint.code")

    def handle(self, *args, endpoint: str, **_) -> None:
        try:
            ep = LimsEndpoint.objects.get(code=endpoint, is_active=True)
        except LimsEndpoint.DoesNotExist as e:
            raise CommandError(f"LIMS endpoint bulunamadı: {endpoint}") from e

        stats = pull_results(ep)
        self.stdout.write(self.style.SUCCESS(
            f"LIMS pull: processed={stats['processed']} "
            f"unmatched={stats['unmatched']}"
        ))
