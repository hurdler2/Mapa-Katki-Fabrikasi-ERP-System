"""Bir üretim emrini PLC'ye reçete olarak indirir.

Kullanım:
    python manage.py scada_download --endpoint PLC-1 --order PO-001
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from production.models import ProductionOrder
from scada.models import PLCEndpoint
from scada.services import download_recipe


class Command(BaseCommand):
    help = "Üretim emrini PLC'ye reçete olarak indirir."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--endpoint", required=True, help="PLCEndpoint.code")
        parser.add_argument("--order", required=True, help="ProductionOrder.order_number")

    def handle(self, *args, endpoint: str, order: str, **_) -> None:
        try:
            ep = PLCEndpoint.objects.get(code=endpoint, is_active=True)
        except PLCEndpoint.DoesNotExist as e:
            raise CommandError(f"Endpoint bulunamadı: {endpoint}") from e
        try:
            po = ProductionOrder.objects.get(order_number=order)
        except ProductionOrder.DoesNotExist as e:
            raise CommandError(f"Emir bulunamadı: {order}") from e

        dl = download_recipe(ep, po)
        self.stdout.write(self.style.SUCCESS(
            f"İndirildi: order={po.order_number} → endpoint={ep.code} "
            f"batch={dl.batch.batch_number if dl.batch else '-'} status={dl.status}"
        ))
