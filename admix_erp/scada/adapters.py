"""SCADA/PLC adapter arayüzleri.

Gerçek OT bağımlılıkları (asyncua / pymodbus / paho-mqtt) opsiyoneldir; kurulmadıysa
adapter oluşturulurken açık ImportError verilir. Testler MockAdapter kullanır.

Faz 6 iskeleti — üretim bağlantısında entegratörün tesise özgü tag haritalaması
(item namespace, register offset, MQTT topic yapısı) buradaki `send_recipe` ve
`poll_weighments` sözleşmelerini uygular.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Protocol


@dataclass
class WeighmentSample:
    """Adapter'ın döndüreceği ham örnek: <batch_number>.<material_code> = weight."""

    tag: str
    weight: Decimal
    plc_timestamp: datetime | None = None
    raw: dict = field(default_factory=dict)


class PLCAdapter(Protocol):
    """Tüm adapter'ların uygulaması gereken sözleşme."""

    def send_recipe(self, payload: dict) -> str:
        """Reçeteyi PLC'ye indir; PLC yanıtını döner (string)."""

    def poll_weighments(self) -> Iterable[WeighmentSample]:
        """PLC'den yeni tartım örneklerini çeker (poll modeli)."""


# ---------------------------------------------------------------------------
# Mock — testler ve dry-run için varsayılan
# ---------------------------------------------------------------------------

class MockAdapter:
    """DB'ye dokunmadan tag-weight çiftleri döndüren adapter.

    Kullanım (test): `MockAdapter(samples=[WeighmentSample('BATCH-1.SP', Decimal('175'))])`
    """

    def __init__(self, samples: list[WeighmentSample] | None = None) -> None:
        self._samples = list(samples or [])
        self.sent_payloads: list[dict] = []

    def send_recipe(self, payload: dict) -> str:
        self.sent_payloads.append(payload)
        return "MOCK_ACK"

    def poll_weighments(self) -> list[WeighmentSample]:
        out, self._samples = self._samples, []
        return out


# ---------------------------------------------------------------------------
# OPC UA (asyncua) — üretim
# ---------------------------------------------------------------------------

class OpcUaAdapter:
    """OPC UA istemcisi. `pip install asyncua` gerekir."""

    def __init__(self, endpoint_url: str, username: str = "", password: str = "") -> None:
        try:
            from asyncua.sync import Client  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "OPC UA adapter için 'asyncua' paketi kurulu olmalı: pip install asyncua"
            ) from e
        self._Client = Client
        self._endpoint_url = endpoint_url
        self._username = username
        self._password = password

    def send_recipe(self, payload: dict) -> str:  # pragma: no cover
        client = self._Client(self._endpoint_url)
        if self._username:
            client.set_user(self._username)
            client.set_password(self._password)
        client.connect()
        try:
            # Tesise özgü: reçete node'una yaz. NodeId entegratör tarafından verilir.
            recipe_node = client.get_node("ns=2;s=Recipe.Download")
            recipe_node.write_value(payload)
            return "OK"
        finally:
            client.disconnect()

    def poll_weighments(self) -> list[WeighmentSample]:  # pragma: no cover
        client = self._Client(self._endpoint_url)
        client.connect()
        try:
            weighments_node = client.get_node("ns=2;s=Weighments.Queue")
            raw = weighments_node.read_value() or []
            samples = []
            for item in raw:
                samples.append(WeighmentSample(
                    tag=item["tag"], weight=Decimal(str(item["weight"])),
                    plc_timestamp=item.get("ts"), raw=item,
                ))
            return samples
        finally:
            client.disconnect()


# ---------------------------------------------------------------------------
# Modbus TCP (pymodbus) — üretim
# ---------------------------------------------------------------------------

class ModbusTcpAdapter:
    """Modbus TCP istemcisi. `pip install pymodbus` gerekir.

    Tesise özgü register haritası entegratör tarafından verilir; bu iskelet
    yalnız sözleşmeyi karşılar.
    """

    def __init__(self, host: str, port: int = 502, unit_id: int = 1) -> None:
        try:
            from pymodbus.client import ModbusTcpClient  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "Modbus adapter için 'pymodbus' paketi kurulu olmalı: pip install pymodbus"
            ) from e
        self._ModbusTcpClient = ModbusTcpClient
        self._host = host
        self._port = port
        self._unit_id = unit_id

    def send_recipe(self, payload: dict) -> str:  # pragma: no cover
        # Reçete parametreleri holding register'lara yazılır. Adres haritası tesise özgü.
        client = self._ModbusTcpClient(self._host, port=self._port)
        try:
            client.connect()
            # Örnek: her satırın (address, value) çiftleri payload'da olmalı.
            for addr, value in payload.get("registers", {}).items():
                client.write_register(int(addr), int(value), slave=self._unit_id)
            return "OK"
        finally:
            client.close()

    def poll_weighments(self) -> list[WeighmentSample]:  # pragma: no cover
        # Modbus'ta struct'lı queue nadir; genelde son değer register'ından okunur.
        return []


# ---------------------------------------------------------------------------
# MQTT (paho-mqtt) — üretim
# ---------------------------------------------------------------------------

class MqttAdapter:
    """MQTT adapter — reçete publish + weighment subscribe.

    `pip install paho-mqtt` gerekir. Kuyruklama için gelen mesajlar bir deque'te tutulur;
    `poll_weighments` bu deque'i drenaj eder.
    """

    def __init__(self, host: str, port: int = 1883, topic_recipe: str = "erp/recipe",
                 topic_weighments: str = "erp/weighments/#") -> None:
        try:
            import paho.mqtt.client as mqtt  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "MQTT adapter için 'paho-mqtt' paketi kurulu olmalı: pip install paho-mqtt"
            ) from e
        self._mqtt = mqtt
        self._host = host
        self._port = port
        self._topic_recipe = topic_recipe
        self._topic_weighments = topic_weighments

    def send_recipe(self, payload: dict) -> str:  # pragma: no cover
        import json
        client = self._mqtt.Client()
        client.connect(self._host, self._port, 30)
        info = client.publish(self._topic_recipe, json.dumps(payload), qos=1)
        info.wait_for_publish()
        client.disconnect()
        return f"MID={info.mid}"

    def poll_weighments(self) -> list[WeighmentSample]:  # pragma: no cover
        # Basit poll: MQTT normalde push modelidir; bu iskelette bir listener kurulup
        # deque doldurulmalı. Üretimde uzun-yaşayan bir servis olmalı.
        return []


# ---------------------------------------------------------------------------
# Adapter factory
# ---------------------------------------------------------------------------

def build_adapter(endpoint) -> PLCAdapter:
    """PLCEndpoint modelinden protokole göre adapter üretir."""
    from django.conf import settings

    from .models import PLCEndpoint

    if not getattr(settings, "SCADA_ENABLED", False):
        return MockAdapter()

    proto = endpoint.protocol
    if proto == PLCEndpoint.Protocol.MOCK:
        return MockAdapter()
    if proto == PLCEndpoint.Protocol.OPC_UA:
        import os
        creds = os.environ.get(endpoint.credentials_env or "", ":")
        user, _, pw = creds.partition(":")
        return OpcUaAdapter(endpoint.endpoint_url, user, pw)
    if proto == PLCEndpoint.Protocol.MODBUS_TCP:
        return ModbusTcpAdapter(endpoint.host, endpoint.port or 502)
    if proto == PLCEndpoint.Protocol.MQTT:
        return MqttAdapter(endpoint.host, endpoint.port or 1883)
    raise ValueError(f"Bilinmeyen protokol: {proto}")
