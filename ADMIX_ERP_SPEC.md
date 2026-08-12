# ADMIX-ERP — Sıvı Beton Katkısı Fabrikası ERP
### Claude Code İnşa Şartnamesi (PROJECT_SPEC)

> Bu doküman Claude Code'un projeyi sıfırdan kurması için yazılmıştır. Kod tanımlayıcıları (model/alan adları) İngilizce, açıklamalar Türkçedir. Bu standarttan sapma.

---

## 1. Bağlam ve Amaç

Bir **sıvı beton katkısı** (concrete admixture) üretim tesisi için ERP. Tesis **gravimetrik (ağırlık esaslı) reçeteli dozajlama** ile çalışır: her hammadde bir yük hücreli teraziden (Balance) geçerek, selenoid vana (electrovanne) hedef ağırlıkta kapanacak şekilde merkezî bir karıştırmalı reaktöre dozlanır, ürün IBC totlarına basılır.

**Proses akışı (referans hat):**
```
W  (su)           ─┐
G  (glukonat)     ─┴─► G+W ön-karışım ─┐
SP (süperplastik.)  3×IBC ─► Balance ──┼─► REAKTÖR (karıştırıcı) ─► Balance ─► IBC (mamul)
HD (katkı bileşeni) 3×IBC ─► Balance ──┘         ▲
W  (su, ikinci)   ────────► Balance ─────────────┘
                                          Kontrol: PLC + HMI (SCADA)
```

Bu **discrete değil, proses/formülasyon üretimidir.** Model bu temele göre kurulur.

### Mimari konumlanma (ISA-95)
- **L2 (PLC + SCADA)** — entegratörün alanı; gerçek batching sekansı, güvenlik, vana/terazi kontrolü. **Bu ERP'nin kapsamı DEĞİL.**
- **L4 (ERP — bu proje)** — master data, reçete, stok, üretim emri, parti, izlenebilirlik, kalite, maliyet.
- **L3 (MES-lite köprüsü)** — Faz 6'da eklenir: PLC'den gerçek tartım verisini çekme, üretim emrini reçete olarak indirme.

ERP **standalone canlıya alınır** (parti verileri manuel girilir), SCADA entegrasyonu sonradan bağlanır. Tüm projeyi risksizleştirir.

### Faz-1 önceliği
**Üretim + Parti + İzlenebilirlik.** Ancak izlenebilirlik bir veri-modeli problemidir; lot şeceresini destekleyen tüm çekirdek varlıklar (master data, reçete, lot) ilk sürümde kurulur ki sonradan yeniden yapılandırma gerekmesin.

---

## 2. Teknoloji Yığını

| Katman | Seçim |
|---|---|
| Dil / Framework | Python 3.12, **Django 5.x** (LTS) |
| Veritabanı | **PostgreSQL 16** (üretim, DMZ sunucusu) / SQLite (yerel dev) |
| Admin/İç arayüz | Django Admin (Faz 1–5) → sonra DRF + ince frontend |
| Ortam | Docker + docker-compose |
| Yapı | Modüler Django app'leri (aşağıdaki `masterdata / formulation / inventory / production`) |

- DB seçimi `DB_ENGINE` env değişkeniyle: `postgres` → PostgreSQL, aksi halde SQLite.
- Tüm gizli değerler `.env` üzerinden; repoya `.env.example` konur.
- Para/ağırlık alanları **`DecimalField`** (asla float). Ağırlık: `max_digits=12, decimal_places=4`.
- Tüm modeller `TimeStamped` soyut modelinden türer (`created_at`, `updated_at`).

---

## 3. Dizin Yapısı

```
admix_erp/
├── manage.py
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── config/
│   ├── settings.py        # env-tabanlı DB, TR locale, Europe/Istanbul
│   ├── urls.py
│   └── wsgi.py
├── common/
│   └── models.py          # TimeStamped soyut model
├── masterdata/            # RawMaterial, Product, Supplier, Customer, Container, UnitOfMeasure
├── formulation/           # Recipe, RecipeLine  (+ scaling servisi)
├── inventory/             # RawMaterialLot, StockMovement  (+ FEFO tahsis)
└── production/            # ProductionOrder, ProductionBatch, MaterialConsumption, OutputContainer
    ├── models.py
    ├── services.py        # batch oluşturma, izlenebilirlik (forward/backward trace)
    └── admin.py
```

---

## 4. Veri Modeli

Aşağıda her app için modeller, alanlar ve ilişkiler tanımlıdır. **İzlenebilirlik omurgası:**
`Supplier → RawMaterialLot → MaterialConsumption → ProductionBatch → OutputContainer → (Customer)`

### 4.1 `common`
**TimeStamped** *(abstract)* — `created_at` (auto_now_add), `updated_at` (auto_now).

### 4.2 `masterdata`

**UnitOfMeasure** — `code` (unique, örn. kg/L), `name`.

**RawMaterial** — hammadde ana kaydı (W, G, SP, HD…)
| alan | tip | not |
|---|---|---|
| `code` | Char(30) unique | Örn. `W`, `G`, `SP`, `HD` |
| `name` | Char(120) | |
| `material_type` | Char choices | `WATER / RETARDER / SUPERPLASTICIZER / ADDITIVE / OTHER` |
| `unit` | FK→UnitOfMeasure PROTECT | |
| `density` | Decimal(8,4) null | kg/L (hacim↔ağırlık dönüşümü) |
| `shelf_life_days` | PositiveInt null | raf ömrü |
| `is_active` | Bool default True | |

**Product** — mamul katkı. `code` unique, `name`, `unit` FK, `description`, `is_active`.

**Supplier** — `code` unique, `name`, `contact`, `tax_no`, `is_active`.

**Customer** — `code` unique, `name`, `contact`, `tax_no`, `is_active`.

**Container** — fiziksel kap/tank
| alan | tip | not |
|---|---|---|
| `code` | Char unique | `TANK-W1`, `IBC-SP-01`, `REACTOR-1` |
| `name` | Char | |
| `container_type` | choices | `TANK / IBC / REACTOR` |
| `capacity` | Decimal(12,4) | |
| `unit` | FK | |
| `is_active` | Bool | |

### 4.3 `formulation`

**Recipe** — versiyonlu reçete
| alan | tip | not |
|---|---|---|
| `product` | FK→Product | |
| `version` | PositiveInt | |
| `base_batch_size` | Decimal(12,4) | referans parti (örn. 1000) |
| `unit` | FK | |
| `is_active` | Bool | **ürün başına yalnızca 1 aktif** |
| `effective_date` | Date | |
| `notes` | Text | |

`Meta.unique_together = (product, version)`. Metod: `scaled_lines(target_qty)` → `factor = target_qty / base_batch_size`, her satırın miktarını ölçekler.

**RecipeLine**
| alan | tip | not |
|---|---|---|
| `recipe` | FK→Recipe related_name="lines" | |
| `raw_material` | FK→RawMaterial | |
| `quantity` | Decimal(12,4) | `base_batch_size` başına |
| `sequence` | PositiveInt | dozaj sırası |
| `tolerance_pct` | Decimal(5,2) | tartım toleransı (%) |

`Meta.unique_together = (recipe, raw_material)`, `ordering = ["sequence"]`.

### 4.4 `inventory`

**RawMaterialLot** — hammadde lotu (giriş izlenebilirlik düğümü)
| alan | tip | not |
|---|---|---|
| `lot_number` | Char unique | |
| `raw_material` | FK→RawMaterial | |
| `supplier` | FK→Supplier null | |
| `received_date` | Date | |
| `expiry_date` | Date null | FEFO için |
| `received_qty` | Decimal(12,4) | |
| `remaining_qty` | Decimal(12,4) | tüketimle azalır |
| `qc_status` | choices | `PENDING / RELEASED / QUARANTINE / REJECTED` |
| `coa_reference` | Char | Analiz sertifikası ref. |
| `container` | FK→Container null | hangi tank/IBC'de |

**StockMovement** — stok hareketi (audit trail)
`lot` FK, `movement_type` (`RECEIPT / CONSUMPTION / ADJUSTMENT`), `quantity` (+/−), `reference` (batch no vb.), `timestamp`, `note`.

### 4.5 `production` — çekirdek

**ProductionOrder** — üretim emri
`order_number` unique, `product` FK, `recipe` FK (versiyon sabitlenir), `target_qty` Decimal, `unit` FK, `scheduled_date`, `reactor` FK→Container, `status` (`PLANNED / RELEASED / IN_PROGRESS / COMPLETED / CANCELLED`), `notes`.

**ProductionBatch** — üretim partisi *(batch_number = mamul lot numarası)*
| alan | tip | not |
|---|---|---|
| `batch_number` | Char unique | mamul lot |
| `production_order` | FK→ProductionOrder null | |
| `recipe` | FK→Recipe | sabitlenmiş versiyon |
| `reactor` | FK→Container | |
| `target_qty` | Decimal(12,4) | |
| `actual_qty` | Decimal(12,4) null | ölçülen çıktı |
| `status` | choices | aşağıdaki durum makinesi |
| `operator` | Char (veya FK→User) | |
| `started_at` / `completed_at` | DateTime null | |
| `qc_status` | choices | `PENDING / RELEASED / REJECTED` |
| `qc_notes` | Text | |

**MaterialConsumption** — ⭐ **izlenebilirlik omurgası** (parti ↔ tüketilen lot)
| alan | tip | not |
|---|---|---|
| `batch` | FK→ProductionBatch related_name="consumptions" | |
| `raw_material` | FK→RawMaterial | |
| `lot` | FK→RawMaterialLot | **hangi lot tüketildi** |
| `target_weight` | Decimal(12,4) | reçeteden ölçeklenmiş hedef |
| `actual_weight` | Decimal(12,4) null | teraziden (Faz1 manuel, Faz6 SCADA) |
| `sequence` | PositiveInt | |
| `dosed_at` | DateTime null | |
| `source` | choices | `MANUAL / SCADA` |

Property: `deviation_pct` = `(actual_weight − target_weight) / target_weight * 100`.

**OutputContainer** — mamul çıkışı (ileri izlenebilirlik → sevkiyat)
`batch` FK related_name="outputs", `container` FK→Container (doldurulan IBC), `quantity` Decimal, `filled_at`, `shipment_reference` Char null *(Faz 4'te Customer/Shipment'e bağlanır)*.

---

## 5. İş Kuralları

1. **Aktif reçete tekliği:** Bir ürün için aynı anda yalnızca bir `Recipe.is_active=True`. `save()` / clean ile zorla.
2. **Reçete sabitleme:** Parti oluşturulunca kullanılan reçete versiyonu partiye bağlanır; reçete sonradan değişse bile parti kaydı etkilenmez (immutable snapshot mantığı).
3. **Lot tüketimi:** Bir `MaterialConsumption` kesinleşince ilgili `RawMaterialLot.remaining_qty` düşülür ve bir `StockMovement(CONSUMPTION)` yazılır. Tek transaction içinde (`@transaction.atomic`).
4. **FEFO tahsis:** Dozaj için lot seçilirken önce en yakın `expiry_date`, sadece `qc_status=RELEASED` lotlar. Yetersizse birden çok lottan tüketim (split) desteklenir.
5. **Kalite kapısı:** Yalnız `RELEASED` lot tüketilebilir; yalnız `qc_status=RELEASED` parti sevk edilebilir.
6. **Tolerans kontrolü:** `|deviation_pct| > RecipeLine.tolerance_pct` ise parti `QC_HOLD`'a düşer / uyarı üretilir.
7. **Kütle dengesi:** `actual_qty` ≈ Σ(actual_weight); sapma raporlanır (fire/kayıp).

### Parti durum makinesi
```
PLANNED ─► IN_PROGRESS ─► COMPLETED ─► QC_HOLD ─┬─► RELEASED
                                                └─► REJECTED
```
Geçersiz geçişler engellenir (örn. RELEASED'dan geri dönülmez).

---

## 6. İzlenebilirlik Servisleri (`production/services.py`)

**`backward_trace(batch)`** — bir mamul partiden geriye: tüketilen tüm hammadde lotları + tedarikçileri + COA referansları. *(Kalite denetimi / şikayet kökü.)*

**`forward_trace(raw_lot)`** — bir hammadde lotundan ileriye: bu lotun girdiği tüm partiler ve onların doldurulduğu IBC'ler (+ Faz4'te müşteriler). *(Geri çağırma / recall kapsamı.)*

**`create_batch_from_order(order, batch_number, reactor=None)`** — üretim emrinden parti üretir; reçeteyi `target_qty`'ye ölçekleyip her satır için hedef ağırlıklı `MaterialConsumption` (henüz `actual_weight=null`) oluşturur.

**`record_dosing(consumption, actual_weight, lot=None, source="MANUAL")`** — gerçek tartımı işler; FEFO lot seçer (verilmediyse), `remaining_qty` düşer, `StockMovement` yazar, tolerans kontrolü yapar. Atomik.

Her servis için pytest testi: özellikle backward/forward trace'in doğru lot→parti→IBC zincirini döndürmesi.

---

## 7. Admin Gereksinimleri

- `ProductionBatch` admin: inline `MaterialConsumption` (hedef vs. gerçek, `deviation_pct` renkli), inline `OutputContainer`.
- `Recipe` admin: inline `RecipeLine` (sequence sıralı).
- `RawMaterialLot` list: `qc_status`, `remaining_qty`, `expiry_date` filtre/renk.
- Batch detayında **"İzlenebilirlik"** admin action → backward trace çıktısı.
- List filtreleri: parti durumu, tarih aralığı, ürün, operatör.

---

## 8. Faz Planı (Claude Code için sıralı görevler)

**Faz 0 — İskele:** proje + 4 app + `common.TimeStamped` + env-tabanlı settings + Docker + `.env.example`. `migrate` çalışır.

**Faz 1 — Master data + Reçete:** `masterdata` ve `formulation` modelleri, admin, `Recipe.scaled_lines`. Seed komutu: W/G/SP/HD hammaddeleri + örnek 1 ürün + 1 reçete.

**Faz 2 — Üretim + Parti + İzlenebilirlik (ÖNCELİK):** `inventory` + `production` modelleri, `services.py` (create_batch, record_dosing, forward/backward trace), admin inline'ları, testler. **Bu fazın sonunda: emir→parti→manuel tartım→IBC→tam trace uçtan uca çalışır.**

**Faz 3 — Kalite:** QC test kayıtları (yoğunluk, pH, katı madde %, klorür, viskozite → EN 934), COA üretimi, karantina/serbest bırakma iş akışı.

**Faz 4 — Satın Alma + Satış:** PO→mal kabul→lot girişi; müşteri siparişi→irsaliye→sevk edilen IBC eşleştirme (forward trace müşteriye uzar).

**Faz 5 — Maliyet + Raporlama:** parti maliyeti, kg başına maliyet, fire, dashboard.

**Faz 6 — SCADA Köprüsü:** OPC UA / Modbus TCP / MQTT ile PLC'den gerçek tartım verisi (`source=SCADA`), üretim emrini reçete olarak indirme. DMZ'den izole OT ağına kontrollü tek geçiş.

---

## 9. Fonksiyonel Olmayan Gereksinimler

- **OT güvenliği:** ERP DMZ/iş ağında; OT ağı izole. Faz 6 köprüsü tek yönlü/kontrollü geçiş, ayrı servis hesabı.
- **Denetlenebilirlik:** tüm stok ve parti hareketleri `StockMovement` + timestamp ile iz bırakır; kayıtlar silinmez, iptal/ters kayıtla yürütülür.
- **Yedekleme:** PostgreSQL günlük dump; `.env` sırları repoda değil.
- **Test:** izlenebilirlik ve kütle dengesi servisleri için pytest zorunlu.
- **Locale:** `tr`, `Europe/Istanbul`, Decimal para/ağırlık.

---

## 10. Claude Code'a Başlangıç Talimatı

> "Bu şartnameyi uygula. **Faz 0**'dan başla, sonra öncelik olarak **Faz 2**'ye kadar (Faz 1 dahil) kur. Her fazın sonunda migration'ları çalıştır, seed'i uygula ve backward/forward trace için bir pytest testi ekle. PostgreSQL için docker-compose ver ama yerelde SQLite ile de çalışsın. Kod adları İngilizce, docstring/yorumlar Türkçe."
