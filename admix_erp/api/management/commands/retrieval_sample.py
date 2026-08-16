"""MCOS Faz F — Aylik retrieval ornekleme cronu.

Aylik 20 rastgele MCOS kimligi ornekler; her biri icin retrieval endpoint'ini
cagirir (dahili), sureyi olcer, SLA (2 dk) icinde mi kontrol eder.

FAIL/SLOW/NOT_FOUND → EHS bildirimi olusturulabilir (opsiyonel).

Kullanim:
    python manage.py retrieval_sample --n 20
"""
from __future__ import annotations

import random
import time
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import RetrievalSampleReport
from api.retrieval import RETRIEVAL_SLA_MS, _resolve_ref
from records.models import Case, Decision, Evidence, RecordInstance


def _collect_pool() -> list[str]:
    """Ornekleme havuzu — tum MCOS kimlik alanlari."""
    pool: list[str] = []
    pool += list(Case.objects.values_list("case_id", flat=True))
    pool += list(RecordInstance.objects.values_list("record_id", flat=True))
    pool += list(Evidence.objects.values_list("evidence_id", flat=True))
    pool += list(Decision.objects.values_list("decision_id", flat=True))
    try:
        from gates.models import Gate
        pool += list(Gate.objects.values_list("gate_id", flat=True))
    except Exception:
        pass
    try:
        from production.models import ProductionBatch
        pool += list(ProductionBatch.objects.values_list("batch_number", flat=True))
    except Exception:
        pass
    try:
        from inventory.models import RawMaterialLot
        pool += list(RawMaterialLot.objects.values_list("lot_number", flat=True))
    except Exception:
        pass
    return [p for p in pool if p]


class Command(BaseCommand):
    help = "Aylik retrieval SLA ornekleme (00_MCO_1 sinav kriteri)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--n", type=int, default=20,
                             help="Ornek sayisi (varsayilan 20)")

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        n = options["n"]
        pool = _collect_pool()
        if not pool:
            self.stdout.write(self.style.WARNING("Ornekleme havuzu bos."))
            return

        picks = random.sample(pool, min(n, len(pool)))
        passed = slow = notfound = error = 0

        for ref in picks:
            t0 = time.perf_counter()
            try:
                resolved_type, obj = _resolve_ref(ref)
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                if obj is None:
                    result = RetrievalSampleReport.Result.NOT_FOUND
                    notfound += 1
                elif elapsed_ms > RETRIEVAL_SLA_MS:
                    result = RetrievalSampleReport.Result.SLOW
                    slow += 1
                else:
                    result = RetrievalSampleReport.Result.PASS
                    passed += 1
                RetrievalSampleReport.objects.create(
                    ref=ref, resolved_type=resolved_type or "",
                    result=result, elapsed_ms=elapsed_ms,
                )
            except Exception as e:  # noqa: BLE001
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                RetrievalSampleReport.objects.create(
                    ref=ref, result=RetrievalSampleReport.Result.ERROR,
                    elapsed_ms=elapsed_ms, error_note=str(e)[:500],
                )
                error += 1

        self.stdout.write(self.style.SUCCESS(
            f"Sample n={len(picks)} · PASS={passed} SLOW={slow} "
            f"NOT_FOUND={notfound} ERROR={error}"
        ))
