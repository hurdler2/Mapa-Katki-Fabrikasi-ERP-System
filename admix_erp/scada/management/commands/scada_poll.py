"""PLC'den tartım örneklerini çeker ve ingest eder.

Kullanım:
    python manage.py scada_poll --endpoint PLC-1 [--once]

`SCADA_ENABLED=1` ayarlı değilse MockAdapter kullanılır (boş kuyruk döner).
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand, CommandError

from scada.models import PLCEndpoint
from scada.services import poll_and_ingest


class Command(BaseCommand):
    help = "PLC endpoint'inden tartım örneklerini çeker ve MaterialConsumption'a işler."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--endpoint", required=True, help="PLCEndpoint.code")
        parser.add_argument("--once", action="store_true", help="Tek sefer çalış, sonra çık")
        parser.add_argument("--interval", type=float, default=2.0, help="Poll aralığı (sn)")

    def handle(self, *args, endpoint: str, once: bool, interval: float, **_) -> None:
        try:
            ep = PLCEndpoint.objects.get(code=endpoint, is_active=True)
        except PLCEndpoint.DoesNotExist as e:
            raise CommandError(f"Endpoint bulunamadı: {endpoint}") from e

        while True:
            events = poll_and_ingest(ep)
            if events:
                for ev in events:
                    self.stdout.write(f"[{ev.status}] {ev.tag}={ev.weight}")
            if once:
                break
            time.sleep(interval)
