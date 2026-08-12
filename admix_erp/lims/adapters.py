"""LIMS adapter arayüzleri: Mock + REST (HTTP JSON).

Gerçek LIMS bağlantısı için `pip install requests` gerekir; opsiyonel.
`build_adapter(endpoint)` factory testlerde MockLimsAdapter döner.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Iterable, Protocol


@dataclass
class SampleRequestPayload:
    """LIMS'e gönderilecek örnek yapısı."""
    request_number: str
    target_type: str  # "BATCH" | "LOT"
    target_reference: str
    parameters: list[str]  # parameter codes
    priority: str = "NORMAL"
    metadata: dict = field(default_factory=dict)


@dataclass
class LimsResultPayload:
    """LIMS'ten gelen bir ölçüm sonucu."""
    request_number: str  # ERP tarafındaki referans
    parameter_code: str
    value: float | None
    unit: str
    verdict: str | None = None  # PASS/FAIL/NA (LIMS'te değerlendirildiyse)
    tester: str = ""
    tested_at: str = ""  # ISO datetime string
    lims_reference: str = ""
    raw: dict = field(default_factory=dict)


class LimsAdapter(Protocol):
    def send_sample_request(self, payload: SampleRequestPayload) -> str:
        """LIMS'e örnek talebini gönderir; LIMS iç referansını döner."""

    def pull_results(self) -> Iterable[LimsResultPayload]:
        """Bekleyen tamamlanmış sonuçları çeker."""


# ---------------------------------------------------------------------------
# Mock — testler ve dry-run
# ---------------------------------------------------------------------------

class MockLimsAdapter:
    def __init__(self, canned_results: list[LimsResultPayload] | None = None) -> None:
        self._results = list(canned_results or [])
        self.sent: list[SampleRequestPayload] = []
        self._counter = 0

    def send_sample_request(self, payload: SampleRequestPayload) -> str:
        self.sent.append(payload)
        self._counter += 1
        return f"MOCK-LIMS-{self._counter:05d}"

    def pull_results(self) -> list[LimsResultPayload]:
        out, self._results = self._results, []
        return out


# ---------------------------------------------------------------------------
# REST adapter (JSON HTTP)
# ---------------------------------------------------------------------------

class RestLimsAdapter:
    """HTTP JSON tabanlı LIMS. Üretimde `requests` paketi kurulu olmalı."""

    def __init__(self, endpoint_url: str, api_key: str = "") -> None:
        try:
            import requests  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "REST LIMS adapter için 'requests' paketi gerekli: pip install requests"
            ) from e
        self._requests = requests
        self._url = endpoint_url.rstrip("/")
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    def send_sample_request(self, payload: SampleRequestPayload) -> str:  # pragma: no cover
        body = {
            "request_number": payload.request_number,
            "target_type": payload.target_type,
            "target_reference": payload.target_reference,
            "parameters": payload.parameters,
            "priority": payload.priority,
            "metadata": payload.metadata,
        }
        r = self._requests.post(
            f"{self._url}/sample-requests", json=body,
            headers=self._headers, timeout=30,
        )
        r.raise_for_status()
        return r.json().get("lims_reference", "")

    def pull_results(self) -> list[LimsResultPayload]:  # pragma: no cover
        r = self._requests.get(
            f"{self._url}/results/pending", headers=self._headers, timeout=30,
        )
        r.raise_for_status()
        items = r.json().get("results", [])
        return [
            LimsResultPayload(
                request_number=i["request_number"],
                parameter_code=i["parameter_code"],
                value=i.get("value"),
                unit=i.get("unit", ""),
                verdict=i.get("verdict"),
                tester=i.get("tester", ""),
                tested_at=i.get("tested_at", ""),
                lims_reference=i.get("lims_reference", ""),
                raw=i,
            )
            for i in items
        ]


def build_adapter(endpoint) -> LimsAdapter:
    """LimsEndpoint modelinden protokole göre adapter üretir."""
    from django.conf import settings

    from .models import LimsEndpoint

    if not getattr(settings, "LIMS_ENABLED", False):
        return MockLimsAdapter()

    if endpoint.protocol == LimsEndpoint.Protocol.MOCK:
        return MockLimsAdapter()
    if endpoint.protocol == LimsEndpoint.Protocol.REST:
        api_key = os.environ.get(endpoint.credentials_env or "", "")
        return RestLimsAdapter(endpoint.endpoint_url, api_key)
    # File / HL7 iskeletleri üretimde eklenir
    raise ValueError(f"Desteklenmeyen protokol: {endpoint.protocol}")
