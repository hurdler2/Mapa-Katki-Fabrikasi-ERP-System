# MCOS-ERP ALIGNMENT PLAN

**Doküman kodu:** ADMIX-ERP-PLAN-MCOS-001
**Versiyon / tarih:** V0.1 · 11 Ağustos 2026 · Taslak (onay bekliyor)
**Sahip:** ERP mimari sorumlusu
**Kapsam:** SARL MAPA ALGÉRIE MCOS Master Project Package-001 (GATE-001 READ FIRST) doküman setinin mevcut `admix_erp` sistemine yansıtılması

> **Amaç.** Bu plan, ADMIX-ERP'yi (17 app, 144 test) SARL MAPA ALGÉRIE'nin **MCOS Corporate Operating System** çerçevesine tam uyumlu hâle getirmek için gereken mimari değişiklikleri, model tasarımlarını, servis akışlarını ve migration stratejisini tanımlar. **Kod yazımına başlamadan önce genel müdürün onayı beklenir** (paket yaklaşımı: MCOS-NAV-001 aktivasyon sınırı).

---

## 0. Yönetici özeti (executive summary)

MCOS paketi 13 kontrollü belgeden oluşuyor. Toplu okuma sonucu ADMIX-ERP'nin MCOS'a uyumu için **8 fazlık bir refactor** gerekiyor. Fazların **A / C / D** kısmı **zorunlu iskelet** (multi-business-line + kontrollü kod register + 5-katmanlı ID modeli); **B / E / F / G / H** kısmı bu iskeletin üstüne oturan operasyonel katman. Toplamda:

| Metrik | Şu an | Plan sonrası |
|---|---:|---:|
| Django app sayısı | 22 | 30 (8 yeni) |
| Model sayısı | 80+ | ~110 |
| Test sayısı | 144 | ~250 |
| Kod uyum notu | %60 MCOS | %95+ MCOS |
| ISO 9001/17025 denetim hazır | Kısmi | **Tam** |

**Kritik nokta:** Mevcut kod hiçbir yerden silinmez. MCOS uyumu **ek katman** olarak eklenir; mevcut testler geçmeye devam eder. Her faz sonunda migration test edilir, kabul edilirse bir sonraki faza geçilir.

---

## 1. Kaynak paketin özeti (13 belge)

### 1.1 L1 Kurumsal (Ne yapıyoruz?)

| Kod | Belge | Ne var |
|---|---|---|
| `MAPA-CDD-001` | Company Design Document | 17 bölüm TR, kurumsal işletim modeli, 12 non-negotiable rule, G0-G6 kalite kapıları, ALCOA+, ISO 9001/14001/45001/10012/17025/19011/31000 uyumu |
| `MAPA-CDD-002` | Organization Design Document | 12 fonksiyon kodu (COR/OPS/QMS/QCL/RDT/PRD/SCM/WHL/MNT/HSE/COM/ADM), 5 seviye (M0-M4), RACI+V, D1-D4 karar hakları, 8 kurumsal kayıt (ORG-MST-001..ORG-MOC-001) |

### 1.2 L2 Navigasyon (Nasıl işletiyoruz?)

| Kod | Belge | Ne var |
|---|---|---|
| `MAPA-IMS-NAV-001` | IMS Navigation Map | 8 kapı (Operation → Gate Status), 5 doküman katmanı (L1-L5), 4 business-line (MCS/MPT/MFT/MLTS), 5 non-negotiable rule |
| `MAPA-IMS-NAV-002` | Decision Navigation Map | D1-D4 seviye, 6 hazır DEC-001..006, veto model, decision failure modes |
| `MAPA-IMS-NAV-003` | Investigation Navigation Map | 8 adımlı investigation, 5 branş (Product/HSE/IT-OT/Supplier/Customer), no-go & re-open triggers, closure test |

### 1.3 L3 Paket kontrol

| Kod | Belge | Ne var |
|---|---|---|
| `MAPA-IMS-NAV-SET-001` | READ FIRST Control Workbook | 11 sheet: package index, 3 nav sheet, CN-2026-0001 change notice, IA-2026-0001 impact analysis, revision log, GATE-001 handover, code preservation matrix, 11 QA checks |

### 1.4 L4 Eğitim + kod kataloğu

| Kod | Belge | Ne var |
|---|---|---|
| `SARL_MAPA_IMS_Trainer_Deck` | 21 slayt eğitim | 10 operasyon kapısı (O-G01..O-G10), 12 simülasyon kapısı, R/V/A ayrımı, 5 yasak kısayol |
| `00_MCO_1` | Form/Formül/Arşiv Eğitim Merkezi | **9 sheet, R15 = 247 kontrollü kod kimliği**, ID sistemi (5 katman), rol/yetki, tetik matrisi, 247-form envanteri (14 zorunlu sütun), formül şablonları, arşiv matrisi, yetkilendirme sınavı (8 kriter) |

### 1.5 L5 T-Faz örnek kayıtlar (GATE-001 doldurulmuş simülasyon)

| Dosya | Kontrollü kod | Kayıt ID | Ne var |
|---|---|---|---|
| `05_T5_...RTS...` | `MAPA-IT-FRM-006` | `RTS-G001-001` | Return-to-Service Reconciliation, 23 sütunlu karar formu, 4 karar hücresi (IT/Owner/QA/DPO), SoD enforcement |
| `06_T6__1` | `MAPA-IMS-FRM-CAPA-001` | `CAPA-G001-001` | Root cause + CAPA + effectiveness, 32 sütun, systemic cause, horizontal deployment |
| `07_CLO_1` | `MAPA-IT-REG-004` | Register satırı | Security event register, SEV1-3 severity, DPO/hukuki action, days open + escalation |
| `08_CLO_1` | `MAPA-IMS-REG-NCR-001` | Master register | **Integrated Event/CAPA Master Register** — NCR + IT incident + recovery + CAPA + effectiveness tek satırda |

### 1.6 GATE-001 T0→T6 kronolojisi (öğrendiğimiz iş modeli)

```
T0  Detect untrusted state       INCIDENT-001    + EVD-G001-001
T1  Containment / HOLD           CHK-G001-001    + DEC-001
T2  Scope freeze                                   EVD-G001-002
T3  Major Investigation class                      DEC-002
T4  Trusted recovery             REC-G001-001    + DEC-003
T5  Reconcile / RTS              RTS-G001-001    + DEC-004
T6  CAPA + horizontal deploy     CAPA-G001-001   + DEC-005
    Gate close PASS                                DEC-006
```

Her T-fazı **ayrı bir yetkili karar** üretir; recovery ≠ CAPA effectiveness ≠ RTS accept ≠ gate close.

### 1.7 5 katmanlı ID modeli (paketin özü)

| Katman | Örnek | Kural | Sabit mi? |
|---|---|---|---|
| Kontrollü doküman kodu | `MAPA-IT-FRM-006` | `MAPA-<Function>-<Type>-<Subject>-<Seq>` | Evet, sadece revizyonla değişir |
| Case / Event ID | `INCIDENT-001` | Bir kez üretilir, yeniden kullanılmaz | Case aç, kapatınca sabit |
| Record Instance ID | `RTS-G001-001` | Her karar/işlem için benzersiz; child → parent case | Sabit, yeniden adlandırılmaz |
| Evidence ID | `EVD-G001-004` | Paket içindeki kanıt sırası; dosya/ek versiyonlanır | Sabit |
| Decision ID | `DEC-004` | Yetki + reviewer + evidence + conditions + reopen | Karar değişirse yeni DEC + reopen |

### 1.8 5 non-negotiable rule (00_MCO_1 sheet 1)

1. **Önce tetikleyiciyi seç** — form seçimi 04_TETIK_MATRISI'nden
2. **Doküman kodu ≠ kayıt ID** — şablon kodunu değiştirerek yeni kayıt üretmek yasak
3. **Sarı girdi / mavi formül** — formül hücresine elle veri girmek yasak
4. **Evidence + review + approval** — tam alan tek başına kanıt değil
5. **Register ve arşiv** — final record salt okunur; retrieval testi zorunlu

### 1.9 Yetkilendirme kabul sınavı (00_MCO_1 sheet 9)

Kullanıcı bir role atansa da, aşağıdaki 8 kriteri **kanıtlamadan** yetkili sayılmaz:

1. Doğru form seçimi (verilen vaka için)
2. ID üretimi (5 katman ayrımı)
3. Girdi/formül ayrımı
4. ALCOA+ kayıt üretimi
5. No-go & escalation
6. Review/onay ayrılığı (self-approval yok)
7. Register güncelleme (source ↔ current-state uyumu)
8. **Arşiv/retrieval — 2 dakika içinde bulma** ← denetçi standardı

---

## 2. Mevcut ERP durumu ve gap analizi

### 2.1 Şu an ne var (17 app, 144 test)

| ✅ Karşılanan alan | Karşılık geldiği MCOS öğesi |
|---|---|
| Master data (Product, RawMaterial, Supplier, Customer, Container) | L5 Master Data (kısmi — kod formatı MCOS değil) |
| Recipe versiyonlama + aktif teklik | L5 Master Data, MOC etkisi (kısmi) |
| Batch + izlenebilirlik (backward/forward trace) | O-G07/08 operasyon kapıları |
| Quality (EN 934) + COA | O-G08 QC/QA + release |
| Purchasing (PO → GR → Lot PENDING) | O-G01..O-G05 satın alma zinciri |
| Sales + Shipment | O-G09 dispatch |
| Accounting (SCF/TVA/G50) | ADM shared services |
| QMS (NCR, CAPA, Deviation) | NAV-003 investigation route (kısmi) |
| Docs (SOP + revision + acknowledgement) | L3 SOP + doküman kontrolü (kısmi) |
| Governance (Risk + Audit + MR) | Yönetişim organları (kısmi) |
| Chemicals (SDS/GHS/EN 934-2 CoC) | RDT + ürün technical dossier |
| EHS (Incident + PPE + JSA + WorkPermit) | HSE stop-work + NAV-003 HSE branch |
| CMMS (Equipment + PM + WO + Calibration) | MNT + O-G kalibrasyon |
| MRP + HR + Notifications + REST API + Analytics + LIMS | Destek katman |
| Portal (10 rol, sidebar rol filtresi, 3 CRUD akışı) | Kullanıcı arayüzü |
| ApprovalRequest (6 kind, e-signature) | D1-D4 (kısmi — D-level yok) |
| RBAC (13 → 10 rol) + audit trail | RACI (kısmi — V yetkisi eksik) |

### 2.2 MCOS gereksinimlerinden **eksik** olanlar (bu planın kapsamı)

| # | Eksik | MCOS kaynağı | Öncelik |
|---|---|---|---|
| 1 | **Business Line ayrımı (MCS/MPT/MFT/MLTS)** | NAV-001 §3 | 🔴 Kritik |
| 2 | **Kontrollü kod register (247 identity)** | 00_MCO_1 sheet 6 | 🔴 Kritik |
| 3 | **5-katmanlı ID modeli (Doc/Case/Record/Evidence/Decision)** | 00_MCO_1 sheet 3, 05_T5 sheet 2 | 🔴 Kritik |
| 4 | **12 MCOS fonksiyon kodu (COR/OPS/QMS/QCL/RDT/PRD/SCM/WHL/MNT/HSE/COM/ADM)** | CDD-002 Ek A | 🟠 Yüksek |
| 5 | **D1-D4 karar seviyesi + V (Veto) yetkisi** | NAV-002 §3 | 🟠 Yüksek |
| 6 | **8-part Gate modeli (Operation..Gate Status)** | NAV-001 §4 | 🟠 Yüksek |
| 7 | **Retrieval endpoint (2 dk hedefi + yıllık örneklem)** | 00_MCO_1 sınav kriter 8 | 🟠 Yüksek |
| 8 | **Master Register (integrated event/CAPA)** | 08_CLO sheet 6 | 🟢 Orta |
| 9 | **Non-negotiable rules runtime enforcer** | CDD-001 §16 (12 kural) | 🟢 Orta |
| 10 | **T-faz kronolojisi (T0-T6) izleyici** | 00_MCO_1 sheet 2 | 🟢 Orta |
| 11 | **RTS-Reconciliation form modeli** | 05_T5 sheet 6 | 🟢 Orta |
| 12 | **CAPA effectiveness verification (owner ≠ verifier)** | 06_T6 sheet 6 | 🟢 Orta |
| 13 | **KRMIX = Product (şirket değil)** yeniden adlandırma + seed | NAV-001 §6 | 🟢 Orta |

---

## 3. Yeni mimari — 8 faz refactor

Fazlar bağımlılıklara göre sıralı. Faz A/B/C paralel yapılamaz — sırayla.

```
Faz A  Multi-Business-Line     ┐
       (BusinessLine + FK)     │  bağımsız iskelet
                                │
Faz C  ControlledCode Register ┤  → Faz D için ön koşul
       (247 kod + validator)    │
                                │
Faz D  5-Katman ID Modeli      ┘  → Faz E/F/G için ön koşul
       (Case/Record/Evidence/
        Decision)
                    ↓
Faz B  MCOS Rol Refactor
       (12 fonksiyon kodu + D-level + Veto)
                    ↓
Faz E  8-Part Gate Modeli
       (Batch release, PO release, Doküman aktivasyon)
                    ↓
Faz F  Retrieval Endpoint
       (2 dk hedefi + yıllık örneklem)
                    ↓
Faz G  Master Register
       (integrated event/CAPA snapshot)
                    ↓
Faz H  Non-Negotiable Rules Enforcer
       (12 kural runtime signal)
```

---

## 4. Faz A — Multi-BusinessLine

### 4.1 Model tasarımı

**Yeni app:** `businessline`

```python
class BusinessLine(TimeStamped):
    class Code(models.TextChoices):
        MCS = "MCS", "MAPA Concrete Solutions"
        MPT = "MPT", "MAPA Precast Technologies"
        MFT = "MFT", "MAPA Formwork Technologies"
        MLTS = "MLTS", "MAPA Laboratory & Technical Services"

    code = CharField(max_length=8, unique=True, choices=Code.choices)
    name = CharField(max_length=120)
    operational_scope = TextField(help_text="NAV-001 §3'e göre kapsam")
    typical_entry = CharField(max_length=200)  # "Production/batch event" vb.
    is_active = BooleanField(default=True)

    # Bağımsız güvence hatları (CDD-002 §4.1)
    qc_independence = TextField(blank=True)
    release_authority = TextField(blank=True)
```

### 4.2 FK migration'ları

Aşağıdaki modellere **nullable** `business_line = FK(BusinessLine, null=True, on_delete=PROTECT)` eklenir; sonra veri backfill edilir; sonra `null=False` yapılır:

- `masterdata.Product` (KRMIX-SP → MCS)
- `masterdata.RawMaterial` (W/G/SP/HD → MCS)
- `masterdata.Container` (reactor → MCS)
- `formulation.Recipe`
- `inventory.RawMaterialLot`
- `production.ProductionOrder`
- `production.ProductionBatch`
- `purchasing.PurchaseOrder`
- `sales.SalesOrder`
- `quality.CertificateOfAnalysis`
- `chemicals.SafetyDataSheet`
- `cmms.Equipment`
- `qms.Nonconformance`
- `docs.ControlledDocument`

### 4.3 Portal etkisi

- **Rol × BusinessLine matrisi** — kullanıcının hangi BL'lerde ne yetkisi var
- Sidebar'da BL selector dropdown (MCS / MPT / MFT / MLTS / Tümü)
- Session'da aktif BL saklanır
- Tüm liste view'ları BL'ye göre otomatik filtrelenir

### 4.4 Seed komutu

`seed_business_lines` — 4 BL + KRMIX-SP ürünü MCS'e taşır + ADX-100 mevcut ürünü MCS ile eşleştirir.

### 4.5 Test

- BusinessLine oluştur, kod unique
- Ürün BL'ye taşınır, backward_trace BL koruyor
- Kullanıcı BL yetkisi olmadığı ürünü göremez
- Cross-BL şirket bakış (GM rolü)

**Tahmini:** 2 model, 15 migration, 15 test.

---

## 5. Faz C — Kontrollü Kod Register

### 5.1 Model tasarımı

**Yeni app:** `registry`

```python
class ControlledCode(TimeStamped):
    """247 kontrollü kod kimliği — 00_MCO_1 sheet 6 envanteri."""

    class Type(models.TextChoices):
        FORM = "FRM", "Form (L4)"
        REGISTER = "REG", "Register (L4)"
        MASTER = "MST", "Master data (L5)"
        SOP = "SOP", "SOP / WI (L3)"
        CHECKLIST = "CHK", "Checklist (L4)"
        PROCEDURE = "PRO", "Procedure (L2)"
        POLICY = "POL", "Policy (L1)"
        MANUAL = "MAN", "Manual (L1)"
        SPECIFICATION = "SPC", "Specification (L5)"
        PLAN = "PLN", "Plan (L2)"
        NAV = "NAV", "Navigation map (L1)"

    class Level(models.TextChoices):
        L1 = "L1", "L1 Corporate"
        L2 = "L2", "L2 Common Control"
        L3 = "L3", "L3 Execution"
        L4 = "L4", "L4 Evidence"
        L5 = "L5", "L5 Master Data"

    class Function(models.TextChoices):
        COR = "COR", "Corporate Governance"
        OPS = "OPS", "Factory Operations"
        QMS = "QMS", "QA / IMS"
        QCL = "QCL", "QC & Laboratory"
        RDT = "RDT", "R&D / Product / Formwork Technology"
        PRD = "PRD", "Production"
        SCM = "SCM", "Supply Chain & Purchasing"
        WHL = "WHL", "Warehouse & Logistics"
        MNT = "MNT", "Maintenance & Utilities"
        HSE = "HSE", "Health, Safety & Environment"
        COM = "COM", "Commercial & Technical Service"
        ADM = "ADM", "Finance / HR / Admin / IT Shared"

    class Status(models.TextChoices):
        ARCHITECTURE_REVIEW = "AR", "Architecture Review"
        DRAFT = "DR", "Draft"
        ISSUED = "IS", "Controlled Issue"
        ACTIVATED = "AC", "Activated (live)"
        RETIRED = "RT", "Retired"

    # Kimlik
    full_code = CharField(max_length=60, unique=True,
        validators=[RegexValidator(r"^MAPA-[A-Z]{3}-[A-Z]{3}(-[A-Z]{3,4})?-\d{3}$",
                                    "Format: MAPA-<Function>-<Type>-<Subject>-<Seq>")])
    short_alias = CharField(max_length=40, blank=True, unique=True, null=True)
    title = CharField(max_length=200)

    # Sınıflandırma
    type = CharField(max_length=3, choices=Type.choices)
    level = CharField(max_length=2, choices=Level.choices)
    function = CharField(max_length=3, choices=Function.choices)
    business_lines = M2MField(BusinessLine, blank=True)  # applicability

    # Sahiplik + prosedür
    source_procedure = CharField(max_length=100, blank=True)  # MAPA-IMS-PRO-DOC
    owner_role = CharField(max_length=40)  # rol adı
    package_wave = CharField(max_length=60, blank=True)  # "Operational Packages 004-009"
    status = CharField(max_length=2, choices=Status.choices)
    revision = CharField(max_length=8, default="R0")

    # Aktivasyon
    activation_gate = TextField(help_text="Aktivasyon için gereken kabul kriterleri")
    objective_evidence_rule = TextField(help_text="Kanıt olarak kabul kuralı")

    # Kullanım
    trigger_type = CharField(max_length=40)  # "Olay/değişiklik", "Rutin/işlem", "Register/master"
    primary_preparer_role = CharField(max_length=100)
    review_approval_model = TextField()
    example_record_id_pattern = CharField(max_length=100)  # "QA-FRM012-2026-0001"
    archive_path_pattern = CharField(max_length=200)  # "/MCOS/IMS/RECORDS/QA/<YYYY>/..."
    retention_authority = CharField(max_length=200)  # "MAPA-IMS-MST-REC-001"

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Kontrollü Kod"
        ordering = ["function", "type", "full_code"]


class ControlledCodeRevision(TimeStamped):
    """Kod revizyon geçmişi (R0, R0.1, R0.9, R1.0, ...)."""

    code = ForeignKey(ControlledCode, related_name="revisions")
    revision = CharField(max_length=8)
    revision_date = DateField()
    change_summary = TextField()
    reviewed_by = ForeignKey(User, related_name="reviewed_revisions",
                              null=True, on_delete=SET_NULL)
    approved_by = ForeignKey(User, related_name="approved_revisions",
                              null=True, on_delete=SET_NULL)
    issue_state = CharField(max_length=40)  # "Controlled Issue"

    class Meta:
        unique_together = (("code", "revision"),)
```

### 5.2 Import komutu

`import_controlled_codes` — 00_MCO_1 sheet 6'yı okuyup ControlledCode kayıtları oluşturur:

```bash
python manage.py import_controlled_codes --file 00_MCO_1.xls
# → 247 kod yüklenir, checksum + validation
```

### 5.3 Bağlantılar

Mevcut modeller `controlled_code` FK ile bir template'e bağlanır:

- `docs.ControlledDocument.controlled_code = FK(ControlledCode)` (SOP, WI)
- `quality.CertificateOfAnalysis.controlled_code = FK(ControlledCode)` (`MAPA-QA-FRM-COA-001` gibi)
- `qms.Nonconformance.controlled_code = FK(ControlledCode)` (`MAPA-IMS-FRM-NCR-001`)
- `qms.CAPA.controlled_code = FK(ControlledCode)` (`MAPA-IMS-FRM-CAPA-001`)
- `production.ProductionBatch.controlled_code = FK(ControlledCode)` (`MAPA-PRD-FRM-BMR-001`)

### 5.4 Portal görünümü

`/portal/registry/` — 247 kod tablosu, filtre (Function/Level/Status/BL), detay sayfası.

### 5.5 Test

- Format validator geçer/kalır (MAPA-XXX-XXX-XXX-000)
- Import 00_MCO_1 → 247 kod
- Kod revizyon zinciri (R0 → R0.9 → R1.0)
- Bağlı ControlledDocument kayıtları

**Tahmini:** 2 model, import komutu, 12 test.

---

## 6. Faz D — 5-Katman ID Modeli (paketin özü)

### 6.1 Model tasarımı

**Yeni app:** `records`

```python
class Case(TimeStamped):
    """Ana olay / vaka kaydı — bir kez üretilir, yeniden kullanılmaz.

    Örnek: INCIDENT-001, CHANGE-2026-0001, AUDIT-2026-Q1, COMPLAINT-2026-014
    """

    class Family(models.TextChoices):
        INCIDENT = "INCIDENT", "Incident / Olay"
        NCR = "NCR", "Nonconformance"
        CHANGE = "CHANGE", "Change Notice (MOC)"
        AUDIT = "AUDIT", "Audit finding"
        COMPLAINT = "COMPLAINT", "Customer complaint"
        DEVIATION = "DEVIATION", "Deviation"
        RISK = "RISK", "Risk event"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        INVESTIGATING = "INVESTIGATING", "Investigating"
        CLOSED = "CLOSED", "Closed"
        REOPENED = "REOPENED", "Reopened"

    case_id = CharField(max_length=60, unique=True,
                         help_text="INCIDENT-001, yeniden kullanılmaz")
    family = CharField(max_length=12, choices=Family.choices)
    business_line = FK(BusinessLine, null=True, on_delete=PROTECT)
    gate = CharField(max_length=20, blank=True)  # "GATE-001"

    title = CharField(max_length=200)
    description = TextField()
    detected_at = DateTimeField()
    detected_by = FK(User, related_name="detected_cases", on_delete=PROTECT)

    severity = CharField(max_length=8, choices=[
        ("SEV1", "Critical"), ("SEV2", "Major"),
        ("SEV3", "Significant"), ("SEV4", "Minor")])
    status = CharField(max_length=14, choices=Status.choices, default=Status.OPEN)

    # T-faz zaman damgaları
    contained_at = DateTimeField(null=True, blank=True)   # T1
    scope_frozen_at = DateTimeField(null=True, blank=True)  # T2
    classified_at = DateTimeField(null=True, blank=True)    # T3
    recovery_at = DateTimeField(null=True, blank=True)      # T4
    reconciled_at = DateTimeField(null=True, blank=True)    # T5
    capa_opened_at = DateTimeField(null=True, blank=True)   # T6
    closed_at = DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Case / Vaka"

    def clean(self):
        # Case ID bir kez üretildikten sonra yeniden kullanılamaz
        if Case.objects.filter(case_id=self.case_id).exclude(pk=self.pk).exists():
            raise ValidationError("Case ID yeniden kullanılamaz")


class RecordInstance(TimeStamped):
    """Bir Case × ControlledCode kesişimindeki gerçek doldurulmuş kayıt.

    Örnek: RTS-G001-001, CAPA-G001-001, REC-G001-001
    """

    class Status(models.TextChoices):
        WORKING = "WORKING", "Working copy"
        REVIEW = "REVIEW", "Supervisor review"
        APPROVED = "APPROVED", "Approved"
        RECORD_COPY = "RECORD_COPY", "Record copy (read-only)"
        SUPERSEDED = "SUPERSEDED", "Superseded"
        REOPENED = "REOPENED", "Reopened"

    record_id = CharField(max_length=60, unique=True,
                           help_text="RTS-G001-001, yeniden kullanılmaz")
    controlled_code = FK(ControlledCode, on_delete=PROTECT,
                          related_name="record_instances")
    case = FK(Case, on_delete=PROTECT, related_name="records")
    business_line = FK(BusinessLine, on_delete=PROTECT, null=True)

    # Lifecycle (00_MCO_1 sheet 8)
    status = CharField(max_length=12, choices=Status.choices, default=Status.WORKING)

    # Roller
    preparer = FK(User, related_name="prepared_records", on_delete=PROTECT)
    reviewer = FK(User, related_name="reviewed_records", null=True,
                    on_delete=SET_NULL)
    approver = FK(User, related_name="approved_records", null=True,
                    on_delete=SET_NULL)

    # Zaman damgaları
    working_started_at = DateTimeField(auto_now_add=True)
    review_started_at = DateTimeField(null=True, blank=True)
    approved_at = DateTimeField(null=True, blank=True)
    record_copy_at = DateTimeField(null=True, blank=True)

    # Payload — form alanları (JSON)
    payload = JSONField(default=dict)

    # Arşiv
    working_path = CharField(max_length=300, blank=True)  # /MCOS/GATE-001/WORKING/...
    record_copy_path = CharField(max_length=300, blank=True)  # .../RECORDS/...
    file = FileField(upload_to="records/%Y/%m/", null=True, blank=True)
    signed_pdf = FileField(upload_to="records/signed/%Y/%m/", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Record Instance"

    def clean(self):
        # SoD: preparer, reviewer, approver farklı kişiler olmalı
        if self.reviewer_id and self.reviewer_id == self.preparer_id:
            raise ValidationError("Hazırlayan aynı zamanda inceleyen olamaz (SoD)")
        if self.approver_id and self.approver_id in (self.preparer_id, self.reviewer_id):
            raise ValidationError("Hazırlayan/inceleyen aynı zamanda onaylayan olamaz")


class Evidence(TimeStamped):
    """Bir Case veya RecordInstance'a bağlı kanıt paketi.

    Örnek: EVD-G001-001, EVD-G001-004
    """

    class Kind(models.TextChoices):
        RAW_DATA = "RAW_DATA", "Ham veri"
        ATTACHMENT = "ATTACHMENT", "Ek dosya"
        PHOTO = "PHOTO", "Fotoğraf"
        LOG = "LOG", "Log / audit trail"
        CERTIFICATE = "CERTIFICATE", "Sertifika"
        COA = "COA", "Certificate of Analysis"
        SIGNED_REPORT = "SIGNED_REPORT", "İmzalı rapor"
        SIMULATION = "SIMULATION", "Simülasyon (canlı değil)"

    evidence_id = CharField(max_length=60, unique=True)
    case = FK(Case, on_delete=PROTECT, related_name="evidence_set")
    record_instance = FK(RecordInstance, null=True, blank=True,
                          related_name="evidence_set", on_delete=CASCADE)
    kind = CharField(max_length=14, choices=Kind.choices)
    title = CharField(max_length=200)
    description = TextField(blank=True)

    file = FileField(upload_to="evidence/%Y/%m/", null=True, blank=True)
    external_url = URLField(blank=True)
    sha256 = CharField(max_length=64, blank=True)
    collected_at = DateTimeField(auto_now_add=True)
    collected_by = FK(User, on_delete=PROTECT, related_name="collected_evidence")

    # ALCOA+ meta
    is_contemporaneous = BooleanField(default=True,
        help_text="Olayla eşzamanlı mı? (ALCOA+ C kriteri)")
    is_original = BooleanField(default=True, help_text="Orijinal mi?")
    derivative_note = CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Evidence"


class Decision(TimeStamped):
    """Yetkili karar kaydı — NAV-002 §4 mandatory decision record.

    Örnek: DEC-001..DEC-006
    """

    class Level(models.TextChoices):
        D1 = "D1", "D1 Routine execution"
        D2 = "D2", "D2 Functional decision"
        D3 = "D3", "D3 Major decision"
        D4 = "D4", "D4 Strategic / crisis"

    class Status(models.TextChoices):
        PASS = "PASS", "PASS"
        CONDITIONAL = "CONDITIONAL", "CONDITIONAL PASS"
        HOLD = "HOLD", "HOLD"
        REJECT = "REJECT", "REJECT"
        RELEASE = "RELEASE", "RELEASE"
        ROLLBACK = "ROLLBACK", "ROLLBACK"
        CLOSE = "CLOSE", "CLOSE"
        REOPENED = "REOPENED", "Reopened"

    decision_id = CharField(max_length=60, unique=True)
    case = FK(Case, on_delete=PROTECT, related_name="decisions")
    record_instance = FK(RecordInstance, null=True, blank=True,
                          related_name="decisions", on_delete=SET_NULL)

    level = CharField(max_length=2, choices=Level.choices)
    status = CharField(max_length=12, choices=Status.choices)

    # Zorunlu alanlar (NAV-002 §4)
    decision_date = DateTimeField()
    decision_maker = FK(User, on_delete=PROTECT, related_name="my_decisions")
    delegated_authority = CharField(max_length=200, blank=True)
    independent_reviewers = M2M(User, blank=True, related_name="reviewed_decisions")

    options_considered = TextField()
    evidence_reviewed = M2M(Evidence, blank=True, related_name="reviewed_in_decisions")
    assumptions = TextField(blank=True)
    dissent_or_veto = TextField(blank=True)
    rationale = TextField()

    conditions = TextField(blank=True)
    action_owner = FK(User, null=True, related_name="my_action_decisions",
                        on_delete=SET_NULL)
    due_date = DateField(null=True, blank=True)
    acceptance_evidence = TextField(blank=True)
    escalation_trigger = TextField(blank=True)
    reopen_trigger = TextField(blank=True)

    # Veto sahibi (NAV-002 §3)
    veto_holder_role = CharField(max_length=60, blank=True)  # "QA/QC", "HSE" vb.

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Decision"
        ordering = ["case", "decision_date"]

    def clean(self):
        # Self-approval yasak: decision_maker independent_reviewers'ta olamaz
        # (kayıt sonrası validate)
        pass  # M2M kaydedildikten sonra signal ile kontrol


class DecisionSignature(TimeStamped):
    """Kararın parola-doğrulamalı e-imzası (21 CFR Part 11)."""

    decision = FK(Decision, related_name="signatures", on_delete=CASCADE)
    signer = FK(User, on_delete=PROTECT)
    meaning = CharField(max_length=20)  # APPROVED, REVIEWED, VETOED, WITNESSED
    reason = CharField(max_length=255)
    ip_address = GenericIPAddressField(null=True)
    signed_at = DateTimeField(auto_now_add=True)
```

### 6.2 Servisler

`records/services.py`:

- `open_case(family, business_line, ..., detected_by)` → Case
- `create_record(controlled_code, case, preparer)` → RecordInstance (WORKING)
- `submit_review(record, reviewer)` → REVIEW
- `approve_record(record, approver)` → APPROVED (SoD check)
- `finalize_record_copy(record)` → RECORD_COPY (immutable, path taşır)
- `add_evidence(case/record, file, kind, ...)` → Evidence + SHA-256 hash
- `record_decision(case, level, status, decision_maker, evidence, rationale, ...)` → Decision
- `sign_decision(decision, user, password, meaning, reason)` → DecisionSignature

### 6.3 Portal

- `/portal/cases/` — açık case'ler
- `/portal/cases/<case_id>/` — case detay: T-faz timeline + record instances + evidence + decisions
- `/portal/records/<record_id>/` — form doldurma (JSON schema controlled_code'dan)
- `/portal/decisions/<decision_id>/` — karar detay + imza

### 6.4 Migration (mevcut modelleri bağla)

- `qms.Nonconformance` → `case` FK (aynı zamanda geçmiş NCR'lar bir Case oluşturur)
- `qms.CAPA` → hem `case` hem `record_instance` FK
- `ehs.Incident` → `case` FK
- `docs.DocumentRevision` → `record_instance` FK (revizyon = kayıt örneği)

### 6.5 Test

- Case unique ID, yeniden kullanılamaz
- RecordInstance SoD (preparer≠reviewer≠approver)
- Evidence SHA-256 hash + ALCOA+ flag
- Decision NAV-002 §4 zorunlu alanlar
- E-imza parola doğrulama
- Full workflow: Case → Record → Evidence → Decision → Sign

**Tahmini:** 5 model + 5 servis + 20 test.

---

## 7. Faz B — MCOS Rol Refactor

### 7.1 Mevcut 10 rol → 12 MCOS fonksiyonu

Mevcut roller korunacak (backward compat) ama MCOS fonksiyon kodu ile eşleştirilecek:

| Mevcut | MCOS Fonksiyon | Yeni label |
|---|---|---|
| `GENERAL_MANAGER` | COR | General Manager (yönetim seviyesi M0) |
| `TECHNICAL_MANAGER` | RDT + OPS koordinasyonu | Technical Director |
| `OPERATIONS_MANAGER` | OPS | Factory Director |
| `IMS_QA_MANAGER` | QMS | QA/IMS Manager |
| `ACCOUNTING_MANAGER` | ADM (Finans) | Finance Manager |
| `LAB_QC` | QCL | QC & Laboratory (kısıtlı yetki) |
| `OPERATIONS_SUPERVISOR` | PRD (üretim süpervizörü) | Production Supervisor |
| `WAREHOUSE` | WHL | Warehouse & Logistics |
| `PURCHASING` | SCM | Supply Chain & Purchasing |
| `IT_ADMIN` | ADM (IT) | IT Admin |

**Yeni roller (eklenecek):**

- `RDT_ENGINEER` — R&D / Product / Formwork Engineer (rol RDT)
- `MLTS_ANALYST` — Commercial Laboratory analyst (QCL ama MLTS BL için)
- `HSE_OFFICER` — HSE stop-work yetkisi
- `INTERNAL_AUDITOR` — bağımsız iç tetkik (kendi işini tetkik etmez)
- `MAINTENANCE_TECH` — MNT
- `COMMERCIAL_ENG` — COM (sözleşme + saha + şikayet)

### 7.2 D1-D4 karar seviyesi + Veto

`portal.ApprovalRequest`'e ekle:

```python
class ApprovalRequest(...):
    ...
    decision_level = CharField(max_length=2, choices=Decision.Level.choices)
    veto_holder_role = CharField(max_length=60, blank=True,
        help_text="Bu talebe veto edebilecek rol (örn. QA_MANAGER)")
```

### 7.3 seed_roles yenile

`ROLE_MATRIX`'ı MCOS fonksiyon kodlarına göre yeniden yaz. `MAPA_ROLE_MAP` sabiti ile eski rol → yeni rol geçişini destekle (migration için).

### 7.4 Test

- Yeni roller + izinler
- D1-D4 karar seviyesi validate
- Veto yetkisi enforce (QA rolü olmayan HOLD karar veremez)
- SoD (self-approval blokla)

**Tahmini:** Rol matrix güncelleme + 5 yeni rol + 8 test.

---

## 8. Faz E — 8-Part Gate Modeli

### 8.1 Model tasarımı

**Yeni app:** `gates`

```python
class Gate(TimeStamped):
    """8-part gate — NAV-001 §4.

    Bir Case veya major geçiş (batch release, doküman activation,
    yeni ürün launch, PO high-amount) bir gate mekaniğine oturur.
    """

    class Section(models.TextChoices):
        OPERATION = "OPERATION", "1. Operation"
        IMS_ENGINE = "IMS_ENGINE", "2. IMS Engine"
        DECISION_ARCH = "DECISION_ARCH", "3. Decision Architecture"
        OBJECTIVE_EVIDENCE = "OBJECTIVE_EVIDENCE", "4. Objective Evidence"
        MANAGEMENT_REVIEW = "MANAGEMENT_REVIEW", "5. Management Review"
        LESSONS_LEARNED = "LESSONS_LEARNED", "6. Lessons Learned"
        IMS_IMPROVEMENT = "IMS_IMPROVEMENT", "7. IMS Improvement"
        GATE_STATUS = "GATE_STATUS", "8. Gate Status"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        HOLD = "HOLD", "HOLD"
        CONDITIONAL = "CONDITIONAL", "Conditional PASS"
        PASS = "PASS", "PASS"
        FAIL = "FAIL", "FAIL"
        REOPENED = "REOPENED", "Reopened"

    gate_id = CharField(max_length=40, unique=True)  # "GATE-001"
    case = FK(Case, on_delete=PROTECT, related_name="gates")
    business_line = FK(BusinessLine, on_delete=PROTECT, null=True)
    scope = TextField()
    owner = FK(User, on_delete=PROTECT, related_name="owned_gates")

    status = CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    opened_at = DateTimeField(auto_now_add=True)
    closed_at = DateTimeField(null=True, blank=True)
    closed_by = FK(User, null=True, on_delete=SET_NULL, related_name="closed_gates")

    reopen_history = JSONField(default=list)


class GateSection(TimeStamped):
    """8 bölümün her biri için bağımsız durum + kanıt."""

    gate = FK(Gate, related_name="sections", on_delete=CASCADE)
    section = CharField(max_length=20, choices=Gate.Section.choices)
    completion_status = CharField(max_length=14, choices=Gate.Status.choices)
    evidence = M2M(Evidence, blank=True)
    reviewer = FK(User, null=True, on_delete=SET_NULL)
    reviewed_at = DateTimeField(null=True, blank=True)
    notes = TextField(blank=True)

    class Meta:
        unique_together = (("gate", "section"),)
        ordering = ["gate", "section"]
```

### 8.2 Servis

`close_gate(gate, closed_by)`:
- Tüm 8 section PASS olmalı
- Her section'da en az 1 evidence bağlı
- Case'in tüm zorunlu Decision'ları mevcut
- İzin verilen: PASS / CONDITIONAL_PASS
- Reddedilen: bir section HOLD veya FAIL ise gate FAIL

### 8.3 Reopen kuralı

Gate PASS'ten sonra bir Decision reddedilir veya yeni contradictory evidence gelirse:
`reopen_gate(gate, trigger)` → status=REOPENED, reopen_history'e log.

### 8.4 Portal

`/portal/gates/<gate_id>/` — 8 bölüm renkli kart görünümü + close butonu.

### 8.5 Test

- 8 section auto-create
- Tüm section PASS olmadan gate PASS olmaz
- Reopen mekanizması
- Reopen'dan sonra tekrar close edilebilir

**Tahmini:** 2 model + servis + 15 test.

---

## 9. Faz F — Retrieval Endpoint

### 9.1 Endpoint tasarımı

```
GET /api/v1/retrieve/?ref=<any-id>
```

`ref` şunlardan biri olabilir:
- Case ID (`INCIDENT-001`)
- Record ID (`RTS-G001-001`)
- Evidence ID (`EVD-G001-004`)
- Decision ID (`DEC-004`)
- Batch number (`BATCH-2026-0001`)
- Lot number (`LOT-SP-2026-0012`)

Response JSON:

```json
{
  "resolved_type": "Case",
  "case": {
    "case_id": "INCIDENT-001",
    "family": "INCIDENT",
    "severity": "SEV2",
    "business_line": "MCS",
    "timeline": {
      "detected_at": "...", "contained_at": "...", "closed_at": "..."
    }
  },
  "records": [ /* RecordInstance[] */ ],
  "evidence": [ /* Evidence[] */ ],
  "decisions": [ /* Decision[] */ ],
  "gate": { "gate_id": "GATE-001", "status": "PASS" },
  "capa": [ /* CAPA[] */ ],
  "generated_at": "...",
  "generation_time_ms": 340
}
```

### 9.2 Performans SLA

- **Hedef: < 2 dakika** (00_MCO_1 sınav kriteri)
- **Gerçek hedef: < 500ms** (P95)
- Prefetch + select_related, indeksler (case_id, record_id, evidence_id)
- Redis cache (5 dk TTL) opsiyonel

### 9.3 Yıllık örneklem cron

`retrieval_sample.py`:
- Aylık rastgele 20 record seç
- Her biri için retrieval çağır, response time ölç
- FAIL veya > 2min → EHS alerti
- Sonuç: `RetrievalSampleReport` modeli

### 9.4 Test

- Farklı ID türleri ile retrieve
- Case → tam dossier
- Response time SLA
- 404 unknown ID

**Tahmini:** 1 model + endpoint + cron + 10 test.

---

## 10. Faz G — Master Register (integrated)

### 10.1 Model tasarımı

**Yeni app:** `master_register` (veya `registers`)

```python
class IntegratedEventRegister(TimeStamped):
    """08_CLO sheet 6 → tek satırda NCR + incident + CAPA + effectiveness."""

    event_id = CharField(max_length=60, unique=True)  # INCIDENT-001
    family = CharField(max_length=20)  # NCR / IT-OT / HSE / Product
    ev_class = CharField(max_length=20)  # EV1-EV4
    d_level = CharField(max_length=2)  # D1-D4

    site_process = CharField(max_length=200)
    scope_summary = TextField()
    detection_date = DateField()
    containment_date = DateField(null=True)

    current_gate = CharField(max_length=20)  # NC9 = closed
    owner = FK(User, on_delete=PROTECT)
    status = CharField(max_length=20)
    disposition_status = CharField(max_length=40)
    hold_flag = BooleanField(default=False)

    # Bağlantılar
    case = FK(Case, on_delete=PROTECT)
    capa_id = CharField(max_length=60, blank=True)
    capa_status = CharField(max_length=20, blank=True)
    moc_id = CharField(max_length=60, blank=True)

    effectiveness_due = DateField(null=True)
    effectiveness_result = CharField(max_length=40, blank=True)
    recurrence_code = CharField(max_length=40, blank=True)
    related_records = TextField(blank=True)

    target_close = DateField(null=True)
    close_date = DateField(null=True)
    evidence_link = TextField(blank=True)  # EVD-G001-001..005

    # Immutable append-only
    is_snapshot = BooleanField(default=False)
    snapshot_of = FK("self", null=True, on_delete=SET_NULL)


class SecurityEventRegister(TimeStamped):
    """07_CLO sheet 6 → security event / incident / data breach register."""

    incident_id = CharField(max_length=60)
    detection_datetime = DateTimeField()
    severity = CharField(max_length=8)  # SEV1-3
    affected_asset = CharField(max_length=300)
    data_class = CharField(max_length=60)
    is_personal_data = BooleanField(default=False)
    detection_reporter = CharField(max_length=200)
    containment_status = CharField(max_length=40)
    evidence_timeline_ref = TextField()
    scope_impact_summary = TextField()
    dpo_legal_external_action = TextField(blank=True)
    recovery_rts_ids = CharField(max_length=200, blank=True)
    ncr_capa_moc_ids = CharField(max_length=200, blank=True)
    owner = FK(User, on_delete=PROTECT)
    target_date = DateField(null=True)
    close_date = DateField(null=True)
    current_status = CharField(max_length=20)
    repeat_effectiveness = CharField(max_length=200, blank=True)
    evidence_link = TextField()
    days_open = IntegerField(default=0)
    escalation_status = CharField(max_length=40, default="Routine")
```

### 10.2 Snapshot mekanizması

Register satırı **silinmez**. Onaylı her değişiklikte:
- Eski satır `is_snapshot=True` işaretlenir
- Yeni satır oluşur, `snapshot_of=eski_satir`
- Register history = time-ordered chain

### 10.3 Test

- Immutable satır (delete blocked)
- Snapshot chain
- Retrieval ile bağlantı

**Tahmini:** 2 model + 8 test.

---

## 11. Faz H — Non-Negotiable Rules Enforcer

### 11.1 12 kural (CDD-001 §16)

`common/rules.py` — her kural Django signal olarak:

| # | Kural | Enforcement |
|---|---|---|
| 01 | Onaysız reçete/HM/tedarikçi ile üretim yok | `production.ProductionBatch` save → recipe.is_active + tedarikçi ASL kontrolü |
| 02 | HOLD/REJECT malzeme kullanılamaz/sevk edilemez | `production.MaterialConsumption` + `sales.ShipmentLine` save → lot.qc_status |
| 03 | Geçerli numune + review olmadan release yok | `production.ProductionBatch` release → QC results kontrol |
| 04 | Kritik ölçüm geçerli kalibrasyon olmadan kabul edilmez | `quality.QCTestResult` save → equipment.calibration_valid |
| 05 | Kayıt geriye dönük oluşturulmaz | `RecordInstance.working_started_at > event.occurred_at + tolerance` |
| 06 | MOC olmadan reçete/proses değişmez | `formulation.Recipe` save → active Change Notice kontrolü |
| 07 | QA hold/red/release baskıyla geçersiz kılınmaz | Signal: high-priority commercial approval QA veto olmadan bypass edemez |
| 08 | Emniyetsiz iş bypass edilemez | `ehs.WorkPermit` state machine |
| 09 | Kritik görev yetkisiz kişi tarafından yürütülemez | User permission check + Competency valid_until |
| 10 | NCR/CAPA aksiyon yapıldı diye kapanmaz | `qms.CAPA` close → effectiveness_verified_at kontrolü |
| 11 | Master data sahibi/yürürlük olmadan yayımlanmaz | ControlledCode signal |
| 12 | Ciddi risk escalation edilir | severity SEV1/SEV2 → auto-notify GM |

### 11.2 Model

```python
class RuleViolation(TimeStamped):
    """Kural ihlali denemesi (log + notify)."""

    rule_no = IntegerField()  # 1-12
    rule_title = CharField(max_length=200)
    user = FK(User, on_delete=PROTECT)
    target_model = CharField(max_length=100)
    target_pk = PositiveBigIntegerField()
    attempted_action = CharField(max_length=100)  # "save", "delete", "release"
    context = JSONField(default=dict)  # önceki değer, denenen değer
    blocked = BooleanField(default=True)
    resolved = BooleanField(default=False)
    resolution_note = TextField(blank=True)
```

### 11.3 Test

- Her kural için pozitif ve negatif test
- Blocked action + notify GM
- Log kaydı

**Tahmini:** 1 model + 12 signal + 24 test.

---

## 12. Migration stratejisi

### 12.1 Prensipler

1. **Mevcut kod hiçbir yerden silinmez** — mevcut 144 test her fazdan sonra geçmeli
2. **Nullable FK, sonra backfill, sonra required** — her BL/Case bağlantısı önce nullable
3. **Feature flag** — her yeni faz `settings.MCOS_ENABLE_<X>` altında toggle edilebilir
4. **Rollback plan** — her migration reverse çalışabilir olmalı

### 12.2 Faz sırası ve bağımlılıklar

```
Sprint 1  Faz A  Business Line     (2 hafta)   ← independent
Sprint 2  Faz C  ControlledCode    (2 hafta)   ← independent
Sprint 3  Faz D  5-Katman ID       (3 hafta)   ← A + C bağımlı
Sprint 4  Faz B  MCOS Roles        (1 hafta)   ← D bağımlı
Sprint 5  Faz E  8-Part Gate       (2 hafta)   ← D bağımlı
Sprint 6  Faz F  Retrieval         (1 hafta)   ← D + E bağımlı
Sprint 7  Faz G  Master Register   (1 hafta)   ← D bağımlı
Sprint 8  Faz H  Rules Enforcer    (2 hafta)   ← A/B/C/D/E/G bağımlı

Toplam ~14 hafta
```

### 12.3 Kabul kriterleri (her sprint sonunda)

- ✅ 144 mevcut test geçmeye devam ediyor
- ✅ Yeni fazın testleri geçiyor (~10-25 test her sprint)
- ✅ `manage.py check` 0 warning
- ✅ Portal karşılık gelen sayfalar açılıyor + 4 farklı rol için 200 döndürüyor
- ✅ Migration reverse edilebilir (`migrate <app> <prev>`)
- ✅ Her yeni model django-simple-history ile audit trail'i var
- ✅ Kod review + IMS terminolojisiyle uyumlu

### 12.4 Genel Müdür onay boundary

**NAV-001'in aktivasyon kuralı**: her belge "Approved: General Manager · Required before live operational activation" diyor.

ERP'ye uygulama:
- Yeni faz merge edildiğinde `MCOS_FEATURE_<X>_ENABLED=False` (feature flag)
- GM tarafından `python manage.py mcos_activate --phase A --user gm` çalıştırılınca True olur
- Audit log tutulur (kim, ne zaman, hangi faz)

---

## 13. Kaynak dosyalarla eşleşme matrisi

| Kaynak dosya | Faz | Ne çıkarıldı |
|---|---|---|
| MAPA-CDD-001 | A, B, H | Business line kimliği, non-negotiable rules, ALCOA+, D1-D4 |
| MAPA-CDD-002 | B | 12 fonksiyon kodu, RACI+V, DoA, 8 kurumsal kayıt |
| NAV-001 | A, E | Business line, 8-part gate, 5 doküman katmanı |
| NAV-002 | D | Decision model (§4 mandatory fields), D1-D4, veto |
| NAV-003 | D, E | Investigation route → Case + Records + Decisions |
| NAV-SET-001 | E | 8-part gate handover, code preservation matrix |
| Training Deck | B, D, E | O-G01..O-G10 → gate transitions, R/V/A rolleri |
| **00_MCO_1** | **C, D, F** | **247 kontrollü kod, 5-katmanlı ID, retrieval sınavı** |
| 05_T5 | D, E | RTS record instance yapısı |
| 06_T6 | D, H | CAPA effectiveness (kural 10) |
| 07_CLO | G | Security event register |
| 08_CLO | G | Integrated master register |

---

## 14. Risk yönetimi

### 14.1 Refactor riskleri

| Risk | Etki | Olasılık | Azaltma |
|---|---|---|---|
| Mevcut 144 test kırılır | Yüksek | Orta | Her sprint sonunda tam suite; feature flag |
| Portal kullanıcıları için UX bozulması | Yüksek | Düşük | Aşamalı UI değişikliği; screenshot testleri |
| Data migration (backfill) hataları | Orta | Orta | Sample dataset ile test; rollback plan |
| ControlledCode import hatası (247 satır) | Düşük | Orta | Import validation + dry-run mode |
| Yeni model dependency conflict | Orta | Düşük | Her faz için ayrı migration file; net imza |
| Retrieval endpoint > 2min | Yüksek | Düşük | Index tasarımı + yük testi + Redis cache |
| GM onayı olmadan aktivasyon | Yüksek | Düşük | Feature flag + mcos_activate audit log |

### 14.2 IMS/ISO uyum riskleri

| Risk | Azaltma |
|---|---|
| MCOS terminolojisinden sapma | Her belgede bu plan referans olarak alınır; kod yorumlarında referans |
| Recovery ≠ CAPA effectiveness karışıklığı | Faz D + H'de ayrı state; test ile enforce |
| Self-approval bypass | SoD signal (Faz H kural #7) |
| Retrieval FAIL denetim sırasında | Yıllık örneklem cron (Faz F) + fail → GM alerti |

---

## 15. Onay ve etkinleştirme

**Bu plan taslak — GM onayı bekliyor.**

| Aşama | Rol | Karar koşulu | Durum |
|---|---|---|---|
| Hazırlayan | ERP mimari sorumlusu | Plan tamamlandı | 11.08.2026 |
| İncelenen | Technical Director + QA/IMS Manager | Teknik + IMS uygunluk | Beklemede |
| Onaylayan | Genel Müdür | Kaynak (bütçe/zaman), risk, öncelik | Beklemede |

**Aktivasyon sınırı**: Bu plan onay aldıktan sonra Faz A'dan başlanır. **Faz aktivasyonu**: her faz sonunda GM tarafından ayrı ayrı onay + `mcos_activate --phase X` komutu.

---

## 16. Ekler

### Ek A — MCOS fonksiyon kodları (CDD-002 Ek A)

| Kod | Fonksiyon |
|---|---|
| COR | Corporate Governance |
| OPS | Factory Operations |
| QMS | QA / IMS |
| QCL | QC & Laboratory |
| RDT | R&D / Product / Formwork Technology |
| PRD | Production |
| SCM | Supply Chain & Purchasing |
| WHL | Warehouse & Logistics |
| MNT | Maintenance & Utilities |
| HSE | Health, Safety & Environment |
| COM | Commercial & Technical Service |
| ADM | Finance / HR / Admin / IT Shared |

### Ek B — 5 katmanlı ID formatı

```
Doküman kodu    MAPA-<Function>-<Type>-<Subject>-<Seq>
                  örn. MAPA-IMS-FRM-NCR-001

Case ID         <Family>-<Seq>
                  örn. INCIDENT-001

Record ID       <Type>-<Gate>-<Seq>
                  örn. RTS-G001-001

Evidence ID     EVD-<Gate>-<Seq>
                  örn. EVD-G001-004

Decision ID     DEC-<Seq>
                  örn. DEC-004
```

### Ek C — 8-Part Gate bölümleri

1. **Operation** — What happened, what output required
2. **IMS Engine** — Which controls & records govern
3. **Decision Architecture** — Who decides, at what level, with which vetoes
4. **Objective Evidence** — What proves execution, review, status
5. **Management Review** — What management must review/resource
6. **Lessons Learned** — What was learned from performance/deviation
7. **IMS Improvement** — What controlled change/CAPA follows
8. **Gate Status** — PASS / CONDITIONAL / HOLD / FAIL

### Ek D — D-Level yetki modeli

| Level | Karar sınıfı | Yetki | No-go |
|---|---|---|---|
| D1 | Rutin | Supervisor / authorized operator | Sapma yok, kritik risk yok |
| D2 | Fonksiyonel | Function manager / process owner | QA/HSE/technical review |
| D3 | Majör | Technical Director / GM delegate | Independent review; kritik FAIL yok |
| D4 | Stratejik/kriz | GM / Board | Formal decision record + implementation gate |

### Ek E — Non-negotiable rules (12)

CDD-001 §16 — bkz. bu planın §11.

---

**Bu doküman ADMIX-ERP-PLAN-MCOS-001 V0.1'dir. GM onayı öncesi sadece taslak referans; live aktivasyon yasaktır.**
