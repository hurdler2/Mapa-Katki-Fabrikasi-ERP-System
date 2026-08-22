# Node-RED SCADA — MAPA Katkı Dozaj Hattı

**Platform:** Node-RED 3.x + Node-RED Dashboard 2.x (veya @flowfuse/node-red-dashboard 3.x)
**Bağlantı:** Modbus TCP (PLC ↔ Node-RED)
**Veritabanı:** PostgreSQL (ADMIX-ERP ile ortak)

---

## Genel Mimari

```
[Siemens S7-1215C]
     │
     │  Modbus TCP · port 502
     ▼
[Node-RED sunucu]  ────REST──▶  [ADMIX-ERP Django]
     │                             │
     │  WebSocket                  │  PostgreSQL
     ▼                             ▼
[Web Dashboard]              [ProductionBatch,
 (telefon/tablet/PC)          QCTestResult,
                              MaterialConsumption]
```

---

## Neden Node-RED?

| Avantaj | Not |
|---------|-----|
| **Ücretsiz** | MIT lisans, ticari kullanım OK |
| **Görsel programlama** | Flow-based, kolay bakım |
| **Modbus + OPC UA + MQTT** | Hazır node'lar var |
| **Web dashboard** | Chart, gauge, table, alarm — hazır |
| **REST API** | ADMIX-ERP'ye HTTP POST kolay |
| **Historian** | PostgreSQL/InfluxDB'ye direkt yazım |

---

## Kurulum (Ubuntu 22.04 sunucu)

```bash
# 1. Node.js kur (LTS)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 2. Node-RED kur
sudo npm install -g --unsafe-perm node-red

# 3. Systemd servisi
sudo npm install -g node-red-admin
sudo bash -c "$(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)"

# 4. Node-RED palet ek modülleri
cd ~/.node-red
npm install node-red-dashboard              # UI dashboard
npm install node-red-contrib-modbus         # Siemens Modbus TCP
npm install node-red-contrib-postgresql     # PostgreSQL (ADMIX-ERP DB)
npm install node-red-node-email             # Alarm bildirimi

# 5. Servisi başlat
sudo systemctl enable nodered.service
sudo systemctl start nodered.service

# 6. Erişim
# http://192.168.1.100:1880/         → Editor
# http://192.168.1.100:1880/ui        → Dashboard
```

---

## Modbus Adres Haritası (PLC ↔ Node-RED)

PLC'de "Modbus TCP Server" aktif edilir; Node-RED "Modbus Client" olur.

### Holding Registers (Read/Write, 16-bit)

| Register | Tip | Anlam |
|----------|-----|-------|
| `40001` | INT | Batch state (0..99) |
| `40002` | INT | Aktif reçete versiyonu |
| `40003` | INT | Alarm bit alanı |
| `40010` | REAL (2 reg) | R01 ağırlık kg |
| `40012` | REAL | R01 sıcaklık °C |
| `40014` | REAL | R01 pH |
| `40016` | REAL | R01 klorür ppm |
| `40018` | REAL | Tank 1 ağırlık |
| `40020` | REAL | Tank 2 ağırlık |
| `40022` | REAL | Tank 3 ağırlık |
| `40024` | REAL | Tank 4 ağırlık |
| `40026` | REAL | Tank 5 ağırlık |
| `40028` | REAL | Su tankı ağırlık |
| `40040` | REAL | Hedef batch kg (reçeteden) |
| `40100` | REAL | Reçete rm1_kg yazım |
| `40102` | REAL | Reçete rm2_kg yazım |
| ...      | ...  | (reçete gönderim) |

### Coil (Read/Write, 1-bit)

| Coil | Anlam |
|------|-------|
| `00001` | Start komutu (Node-RED → PLC) |
| `00002` | Stop komutu |
| `00003` | Reset komutu |
| `00010` | Vana 1 durumu (PLC → Node-RED) |
| `00011` | Vana 2 durumu |
| ...      | ... |
| `00020` | Pompa 1 durumu |
| ...      | ... |
| `00030` | Mixer durumu |
| `00040` | Batch tamamlandı bit |
| `00041` | Alarm var bit |

---

## Dashboard Ekranları

| Ekran | Amaç |
|-------|------|
| **Ana Ekran** | Reaktör ağırlığı canlı + batch state + start/stop butonları |
| **Reçete** | Aktif reçete gösterim + reçete seçim/gönderme |
| **Trend** | Ağırlık + pH + T + Cl canlı grafik (son 1 saat) |
| **Alarm** | Aktif alarm listesi + geçmiş |
| **Batch Geçmişi** | Son 30 batch (ADMIX-ERP DB'den) |
| **Kalite** | pH/T/Cl QC sonuçları + trend |

---

## Dosyalar

- [`flows/main_flow.json`](flows/main_flow.json) — Ana Node-RED flow (Modbus + Dashboard + ERP bridge)
- [`flows/dashboard_layout.md`](flows/dashboard_layout.md) — Dashboard ekran taslakları

---

## ADMIX-ERP Entegrasyonu

Batch tamamlandığında Node-RED → ADMIX-ERP HTTP POST:

```
POST /api/v1/production/batches/from-scada/
Authorization: Token XXXXXX
Content-Type: application/json

{
  "batch_number": "BATCH-20260915-042",
  "recipe_code": "ADX-100-v3",
  "target_kg": 1000.0,
  "actual_kg": 999.7,
  "started_at": "2026-09-15T14:23:07Z",
  "completed_at": "2026-09-15T15:03:12Z",
  "consumptions": [
    {"code": "W",  "target": 600.0, "actual": 600.2},
    {"code": "M1", "target": 250.0, "actual": 249.8},
    {"code": "M2", "target": 80.0,  "actual": 80.1},
    {"code": "IN", "target": 15.0,  "actual": 14.9},
    {"code": "ZT", "target": 8.0,   "actual": 8.0},
    {"code": "BZ", "target": 47.0,  "actual": 47.1}
  ],
  "qc_results": [
    {"parameter": "PH", "value": 5.8, "verdict": "PASS"},
    {"parameter": "TEMP", "value": 32.5, "verdict": "PASS"},
    {"parameter": "CHLORIDE", "value": 245.0, "verdict": "PASS"}
  ]
}
```

Bu ADMIX-ERP tarafında `ProductionBatch` + `MaterialConsumption` + `QCTestResult` kayıtlarına dönüşür.
Django tarafında yeni endpoint yazacağız (`admix_erp/api/views.py`).
