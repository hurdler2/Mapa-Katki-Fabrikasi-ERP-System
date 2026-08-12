# ADMIX-ERP

Sıvı beton katkısı (concrete admixture) fabrikası için tam kapsamlı ERP.
Django 5.1 · PostgreSQL 16 · Docker · **137 test yeşil**.

## Kapsam

| Alan | İçerik |
|---|---|
| Üretim | Reçete versiyonlama, ölçekleme, parti + izlenebilirlik (backward/forward), SCADA köprüsü (OPC UA / Modbus / MQTT) |
| Kalite | EN 934-2 QC (yoğunluk/pH/katı%/klorür/viskozite), COA, CoC + AVCP System 2+ + CE marking |
| Stok | FEFO lot tahsisi, mal kabul → PENDING lot → QC serbest, stok hareketi (audit) |
| Kimya | GHS piktogram + H/P + 16 bölümlü SDS (Reg EU 2020/878), tehlike depolama uyumsuzluğu, retention numune, raf ömrü alertı |
| Satın alma/Satış | PO → GR → lot; SO → sevkiyat → müşteri; forward trace müşteriye uzanır |
| Muhasebe (Cezayir SCF) | PCN 2010 hesap planı (81 hesap), yevmiye/mizan/Grand Livre, TVA %19 + G50 beyan, sabit kıymet + amortisman |
| QMS (ISO 9001) | NCR, CAPA, sapma, müşteri şikayeti, doküman kontrolü (SOP/WI), iç denetim, yönetim gözden geçirme, risk & fırsat |
| EHS (ISO 14001/45001) | İSG olay, PPE + maruziyet, çevresel yön/ölçüm, yasal uyum, JSA, iş izin sistemi |
| CMMS | Ekipman envanteri, PM planı, iş emri, kalibrasyon (§7.1.5.2), MTBF/MTTR |
| MRP + HR | Talep tahmini, brüt/net ihtiyaç, requisition; vardiya, eğitim → yetkinlik, izin |
| Bildirim + API | Görev kutusu (inbox), REST API + JWT, PDF şablonları (fatura/irsaliye/iş izin/SDS/COA) |
| BI + ISO paketi | OEE, fire trendi, tedarikçi skorkartı, şikayet trendi, ISO denetim paketi (PDF/JSON/ZIP) |
| LIMS | Örnek talep push + sonuç pull → QC test otomatik üretimi |

## Kurulum (Yerel)

```bash
cd admix_erp
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Linux/Mac: .venv/bin/pip

python manage.py migrate
python manage.py seed_all --admin-password Secret123!
python manage.py runserver
```

Ana ekran: `http://localhost:8000/` (giriş: `admin` / `Secret123!`)

## Kurulum (Docker + PostgreSQL)

```bash
cp .env.example .env       # DB_ENGINE=postgres olarak ayarla
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py seed_all --admin-password Secret123!
```

## Erişim Noktaları

| Yol | Açıklama |
|---|---|
| `/` | Ana ekran — KPI özet + modül kartları |
| `/admin/` | Django Admin (tüm modeller) |
| `/reporting/dashboard/` | Üretim dashboard (fire, hammadde tüketimi) |
| `/analytics/bi/` | BI Dashboard (OEE, tedarikçi, şikayet, Chart.js) |
| `/analytics/iso-audit/` | ISO denetim paketi (PDF / JSON / ZIP) |
| `/accounting/balance/` | Mizan (SCF) |
| `/accounting/ledger/<id>/` | Grand Livre |
| `/notifications/` | Bildirim inbox |
| `/api/v1/` | REST API |
| `/api/v1/auth/token/` | JWT token al |

## Ana Kavramlar

### Uçtan uca üretim akışı

```
Satın alma emri (PO)
   ↓
Mal kabul (GR) → RawMaterialLot (PENDING)
   ↓
QC test → release_lot → RELEASED
   ↓
Üretim emri (PO) → create_batch_from_order → ProductionBatch (PLANNED)
   ↓  (opsiyonel: SCADA'dan reçete indir)
IN_PROGRESS → dozaj (FEFO + tolerans kontrolü)
   ↓
COMPLETED → QC batch test → release_batch → RELEASED
   ↓
generate_coa → COA yayımlanır
   ↓
OutputContainer (IBC) → create_shipment → müşteriye sevk
   ↓
create_sales_invoice_from_shipment → yevmiye (JV) → tahsilat → mizan
```

### İzlenebilirlik

- `backward_trace(batch)` → **parti → tüketilen tüm hammadde lotları + tedarikçi + COA**
- `forward_trace(lot)` → **hammadde lotu → giren parti → doldurulan IBC → müşteri + sevk tarihi**

Recall (geri çağırma) senaryosunda tek çağrı ile etkilenen tüm partiler ve müşteriler listelenir.

### RBAC (13 rol)

`python manage.py seed_roles` — Django Groups + izin matrisi:

- Operatör · Vardiya Amiri · Üretim Planlayıcı
- QC Analist · QA Müdürü
- Depo · Satın Alma · Satış · Muhasebe
- Bakım · EHS · Yönetim · BT Yönetici

### E-imza (21 CFR Part 11 esinli)

```python
from iam.services import sign
sign(user=user, target=batch, meaning="RELEASED", reason="QC geçti", password="…")
```

Kritik onaylarda parola yeniden doğrulaması + değişmez audit kaydı.

### Audit Trail

`django-simple-history` ile 12+ kritik modelin tüm değişiklikleri:
- ProductionBatch, MaterialConsumption, RawMaterialLot
- Recipe, CertificateOfAnalysis
- Nonconformance, CAPA, Deviation, CustomerComplaint
- Invoice, JournalEntry, FixedAsset
- ControlledDocument, DocumentRevision
- Incident, JobSafetyAnalysis, WorkPermit
- Equipment, WorkOrder, CalibrationRecord
- RiskItem, InternalAudit, ManagementReview
- ChemicalProfile, SafetyDataSheet, CertificateOfConformity

## Yönetim Komutları

```bash
python manage.py seed_all --admin-password Secret123!  # tümü tek komutta

# Bireysel seed'ler:
python manage.py seed_roles       # Django Groups
python manage.py seed_demo        # ADX-100 reçete + master data
python manage.py seed_qc          # EN 934 QC parametreleri
python manage.py seed_ghs         # GHS piktogram + H/P + uyumsuzluk
python manage.py seed_ehs         # PPE + Cezayir yasal referanslar
python manage.py seed_equipment   # 10 ekipman + PM + kalibrasyon
python manage.py seed_scf         # 81 hesap + TVA + yevmiye

# İşletim komutları (cron):
python manage.py scan_shelf_life           # raf ömrü tarama (günlük)
python manage.py scada_download --endpoint PLC-1 --order PO-001
python manage.py scada_poll --endpoint PLC-1 --once
python manage.py lims_pull --endpoint LAB-1
```

## Standart Uyumluluğu

| Standart | Kapsam |
|---|---|
| ISO 9001:2015 | QMS, doküman, denetim, MR, NCR/CAPA, risk, kalibrasyon |
| ISO 14001:2015 | Çevresel yön, yasal uyum, ölçüm |
| ISO 45001:2018 | Tehlike (JSA), iş izin, PPE, olay, maruziyet |
| EN 934-2:2009+A1:2012 | Ürün spec + AVCP System 2+ + FPC + CoC + CE |
| CLP / REACH 2020/878 | 16 bölümlü SDS + GHS piktogram + H/P |
| 21 CFR Part 11 | E-imza (parola + reason), audit trail |
| Cezayir SCF (2010) | PCN 2010 hesap planı, yevmiye, TVA, G50 |

## Test

```bash
python -m pytest -v
python -m pytest -q --tb=short          # kısa özet
python -m pytest production/tests/ -v   # tek app
```

## Mimari

22 app · 80+ model · 11 seed komutu · 137 test.

```
config/           # Django settings + urls
common/           # TimeStamped, ana ekran, PDF helper, seed_all
iam/              # RBAC + Department + Competency + ESignature
masterdata/       # RawMaterial, Product, Supplier, Customer, Container, UOM
formulation/      # Recipe + RecipeLine + scaled_lines
inventory/        # RawMaterialLot (FEFO) + StockMovement
production/       # ProductionOrder, Batch, Consumption, OutputContainer
                  # + backward_trace, forward_trace, record_dosing
quality/          # QCParameter, QCSpec, QCTestResult, CertificateOfAnalysis
purchasing/       # PurchaseOrder + GoodsReceipt → RawMaterialLot
sales/            # SalesOrder + Shipment → OutputContainer eşleşme
reporting/        # batch_cost, mass_balance, production_summary, dashboard
scada/            # PLCEndpoint, adapter (Mock/OPC UA/Modbus/MQTT)
qms/              # NCR, CAPA, Deviation, CustomerComplaint
docs/             # ControlledDocument + Revision (onay zinciri)
governance/       # RiskItem, InternalAudit, ManagementReview
chemicals/        # ChemicalProfile, SDS 16 bölüm, StorageZone, CoC, retention, ShelfLifeAlert
ehs/              # Incident, PPE, ExposureMeasurement, JSA, WorkPermit
cmms/             # Equipment, MaintenancePlan, WorkOrder, Calibration
accounting/       # SCF Account, Journal, Invoice, Payment, FixedAsset, TVA
mrp/              # DemandForecast, MRPRun, MaterialRequirement, Requisition
hr/               # Shift, TrainingCourse/Session/Record, LeaveRequest
notifications/    # Notification + inbox + notify_group
api/              # DRF ViewSets + JWT + trace action'ları
analytics/        # BI (OEE, fire, tedarikçi, şikayet) + ISO paketi
lims/             # LimsEndpoint, SampleRequest, adapter push/pull
```

## Lisans

Bu proje `ADMIX_ERP_SPEC.md` şartnamesine göre inşa edilmiştir.
