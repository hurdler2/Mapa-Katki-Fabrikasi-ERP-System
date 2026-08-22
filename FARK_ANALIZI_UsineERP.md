# UsineERP vs ADMIX-ERP — Fark Analizi ve Yol Haritası

**Analiz tarihi:** 20 Ağustos 2026
**Referans sistem:** UsineERP (aynı sektör — süperplastifiyan / kimyasal katkı üreticisi, Cezayir)
**Karşılaştırılan sistem:** ADMIX-ERP (SARL MAPA Algérie)
**İncelenen ekran görüntüsü:** 182 foto (30+ ekran detaylı analiz edildi)

---

## 1. Yönetici Özeti

UsineERP, bizim sistemimizle **aynı mimari felsefeyi** paylaşıyor:
- MCOS benzeri iş kuralı (BR) referansları — **BR-PROD-01, BR-QA-03/04/05/06/11/12, §22, §23**
- Gate A / Gate B / Gate C mekanizması (bizim 8-part gate'in daha basit versiyonu)
- 5-katmanlı belge zinciri (Case → RecordInstance → Evidence → Decision → Signature)

Ancak **operasyonel derinlik** açısından bizden ileride. En kritik farklar:

| # | Alan | UsineERP | Bizde | Fark |
|---|------|----------|-------|------|
| 1 | Formülasyon — Bilan massique / COMPLÉMENT | ✅ Otomatik su tamamlama | ❌ | KRİTİK |
| 2 | Üretim emri — Facteur d'échelle | ✅ 1.0 → 2.0 çarpımı | ❌ | KRİTİK |
| 3 | Spec versiyonlama + QA onayı | ✅ Créée par + Approuvée par (QA) | ⚠ Kısmen | YÜKSEK |
| 4 | Örnekleme planları (Plans d'échantillonnage) | ✅ Gate bağlı, tetikleyicili | ❌ | YÜKSEK |
| 5 | Test kataloğu (Propriétés/Tests) | ✅ Unite/method/precision | ⚠ Model var kullanım yok | YÜKSEK |
| 6 | NCR root cause taksonomisi | ✅ 7+1 sabit kategori | ⚠ Serbest metin | ORTA |
| 7 | Stok detay — progress bar + eşikler | ✅ Alerte/rupture threshold | ⚠ Kısmen | ORTA |
| 8 | BL Client (İrsaliye) faturadan ayrı | ✅ Ayrı belge | ❌ | YÜKSEK |
| 9 | Avance Client (§23) | ✅ Ayrı model | ❌ | ORTA |
| 10 | Reporting hub + accès rapide | ✅ 6 rapor kartı | ⚠ Sadece dashboard | ORTA |

**Sonuç:** Muhasebe/Cezayir uyumu (SCF, TVA, DGI) ve sidebar/PDF/iskonto bizim tarafta iyi. Ama **kalite yönetimi (QA/Lab)** ve **üretim şablonlama** taraflarında UsineERP çok daha detaylı. Aynı zamanda **BL (irsaliye)/faturalama ayrımı** eksik.

---

## 2. Modül-Modül Detaylı Karşılaştırma

### 2.1 Formülasyon (Formulations)

**UsineERP'de olan (IMG_8305–8320):**
- `qty_per_batch` (batch başına miktar)
- `tolerance_pct` (tolerans %)
- **COMPLÉMENT** checkbox — bir hammadde "tamamlayıcı" olarak işaretlenir (genelde su)
- **Bilan massique §22 PLANIFIÉ** — otomatik su tamamlama:
  - Toplam batch hedefi: 1000 kg
  - Diğer hammaddeler: 850 kg
  - Complément (su) = 150 kg (otomatik)
- Batch bazlı miktar tanımı, tolerans, iş kuralı §22 referansı UI'da görünüyor

**Bizde durum:**
- `Formulation` modeli var, `qty_per_batch` var
- COMPLÉMENT / auto-calculated water yok
- `tolerance_pct` yok
- §22 bilan massique hesaplama yok

**Yapılması gereken:**
```python
# masterdata/models.py — FormulationLine
is_complement = models.BooleanField(default=False)
tolerance_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

# services.py
def compute_bilan_massique(formulation):
    """§22 PLANIFIÉ: complément satırı toplam batch'e tamamlar."""
    target = formulation.qty_per_batch
    fixed = sum(l.quantity for l in formulation.lines.exclude(is_complement=True))
    complement = target - fixed
    ...
```

**Öncelik:** 🔴 KRİTİK (üretim sürecinin temeli)

---

### 2.2 Üretim Emirleri (Ordres de Production)

**UsineERP'de olan (IMG_8325–8340):**
- **Facteur d'échelle** (ölçek faktörü) — formülasyondaki 1000 kg'lık reçete → 2000 kg üretilecekse faktör 2.0
- **Besoins théoriques MP** tablosu:
  - Malzeme adı | Qté nécessaire | Stock dispo | ✓/✗
  - Yeşil check: stok yeterli
  - Kırmızı X: "Stock insuffisant"
- Faktör değişince tablo anında güncelleniyor
- Batch bazlı üretim (2 batch × 1000 = 2000 kg gibi)

**Bizde durum:**
- `ProductionOrder` var, `type`, `scheduled_date` var
- Scale factor / theoretical needs otomatik hesabı yok
- Stok yeterlilik UI'da anlık gösterilmiyor

**Yapılması gereken:**
- `ProductionOrder.scale_factor` (default 1.0)
- Detay sayfasında AJAX ile "besoins théoriques" tablosu (formulation × scale × qty vs current stock)
- Stok yetersizse üretim emri onaylanamasın (BR-PROD-01 zaten var)

**Öncelik:** 🔴 KRİTİK

---

### 2.3 Kalite Şartnameleri (Spécifications qualité)

**UsineERP'de olan (IMG_8455–8470, 8485):**
- **Version** numarası (1, 2, 3...) — spec versiyonlama
- **Date d'effet** (yürürlük tarihi)
- **Active** checkbox
- **Créée par** (kim oluşturdu)
- **Approuvée par (QA)** — QA onayı zorunlu, ayrı alan
- **LIGNES DE SPÉCIFICATION** tablosu:
  - PROPRIÉTÉ (dropdown, katalogtan)
  - CONTRÔLÉ À GATE A / GATE B / GATE C — 3 ayrı checkbox
  - VALEUR NOMINALE (hedef değer)
  - TOLÉRANCE (%)
  - MIN ABSOLU / MAX ABSOLU
  - **CRITIQUE (BR-QA-05)** — bir spec ihlali kritik mi?
  - RÉSULTAT ATTENDU (CONFORME = COCHÉ)
  - CATÉGORIES/GRADES ACCEPTÉS

**Bizde durum:**
- `QualitySpec` modeli var, aktif/pasif var
- Versiyonlama var ama UI'da net değil
- QA approval workflow yok (Créée par ≠ Approuvée par ayrımı yok)
- Per-Gate checkbox yok (spec her Gate'te çalışıyor varsayımıyla)
- Kritik/non-critique ayrımı yok

**Yapılması gereken:**
```python
# quality/models.py
class QualitySpec:
    version = models.PositiveIntegerField(default=1)
    effective_date = models.DateField()
    created_by = models.ForeignKey(User, related_name="+")
    approved_by = models.ForeignKey(User, related_name="+", null=True)
    approved_at = models.DateTimeField(null=True)
    # approved_by null → aktif olamaz

class SpecLine:
    property = models.ForeignKey(TestProperty)
    check_at_gate_a = models.BooleanField(default=False)
    check_at_gate_b = models.BooleanField(default=False)
    check_at_gate_c = models.BooleanField(default=False)
    nominal_value = models.DecimalField(...)
    tolerance_pct = models.DecimalField(...)
    min_absolute = models.DecimalField(null=True)
    max_absolute = models.DecimalField(null=True)
    is_critical = models.BooleanField(default=False)  # BR-QA-05
```

**Öncelik:** 🟠 YÜKSEK

---

### 2.4 Test Kataloğu (Catalogue Propriétés / Tests)

**UsineERP'de olan (IMG_8445, 8460):**
- **Propriété** (özellik adı)
- **S'applique à** (uygulanır: MP / PF / her ikisi)
- **Unité** (birim: %, pH, cP, g/cm³, μm, ΔE, °Brix, MPa, CFU/g)
- **Méthode / référence d'essai** (test yöntemi referansı)
- **Type de résultat** (Numérique valeur unique / Texte / Katégorique)
- **Précision décimales**

**Bizde durum:**
- `TestProperty` modeli var (birim, method alanları mevcut)
- Ancak portal UI'da yönetim yok, sadece admin'de
- Precision (ondalık hane sayısı) alanı yok

**Yapılması gereken:**
- `TestProperty.decimal_precision = models.PositiveSmallIntegerField(default=2)`
- Portal QA sidebar'a "Katalog: Özellikler/Testler" ekle
- Numune sonuç girişinde decimal precision'a göre input mask/rounding

**Öncelik:** 🟠 YÜKSEK

---

### 2.5 Örnekleme Planları (Plans d'échantillonnage)

**UsineERP'de olan (IMG_8385, 8410):**
- Matière première VEYA Produit fini'ye bağlı
- **Point de contrôle** (Gate A / B / C)
- **Déclencheur** (tetikleyici):
  - "par ligne de BL" (BL satırı başına)
  - "après mélange" (mikslemeden sonra)
  - "à réception" (mal kabulde)
- **Fréquence** (her N'de bir)
- **Règle de taille d'échantillon** (numune sayısı formülü)
- **Motif de désactivation (BR-QA-12)** — deaktifse sebep zorunlu

**Bizde durum:**
- Böyle bir model **yok**
- Numune manuel olarak oluşturuluyor

**Yapılması gereken:**
```python
class SamplingPlan(models.Model):
    material = models.ForeignKey(RawMaterial, null=True)
    product = models.ForeignKey(FinishedProduct, null=True)
    gate = models.CharField(choices=[("A","Gate A"),("B","Gate B"),("C","Gate C")])
    trigger = models.CharField(choices=[
        ("per_bl_line","Par ligne de BL"),
        ("after_mix","Après mélange"),
        ("on_receipt","À réception"),
    ])
    frequency_n = models.PositiveIntegerField(default=1)
    sample_size_rule = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    deactivation_reason = models.TextField(blank=True)  # BR-QA-12
```

**Öncelik:** 🟠 YÜKSEK (kalite süreç otomasyonu)

---

### 2.6 Numune Sonuç Girişi (Saisie des résultats)

**UsineERP'de olan (IMG_8490):**
- **Spec kilitleme (BR-QA-04):** "Spécification verrouillée : PF-002 v1 (BR-QA-04)"
  - Numune oluşturulduğu anda spec versiyonu kilitleniyor, sonra spec değişse bile bu numune eski spec ile değerlendiriliyor
- Sonuç girişi tablosu:
  - PROPRIÉTÉ | NOMINAL / LIMITES [10.0000 - 15.0000] | CRITIQUE | VALEUR RELEVÉE
- Kritik özellikler sarı/kırmızı vurgu
- Değer girildikçe pass/fail anlık gösterim

**Bizde durum:**
- Numune modelinde `spec_version_locked` alanı yok
- Sonuç girişi var ama limit gösterimi zayıf

**Yapılması gereken:**
- `Sample.spec_version` FK kilidi (BR-QA-04)
- Sonuç girişi UI'da min-max ve conforme/non-conforme anlık badge

**Öncelik:** 🟠 YÜKSEK

---

### 2.7 Uygunsuzluk (Non-Conformités / NCR)

**UsineERP'de olan (IMG_8395):**
- NCR-YYYY-NNNN numarası
- Gate belirteci (Gate C — Post-production PF/rendement)
- Sabit taksonomi:
  - Description (otomatik: "OP-XXX rendement=Y, statut=critical. Écarts: HD400: -3.1%, SR100: -3.1%")
  - **Analyser et dispositionner (Responsable QA)** paneli
  - **Root cause category** dropdown (7 seçenek + Autre):
    1. Qualité fournisseur
    2. Équipement
    3. Process / Opérateur
    4. Conception formule
    5. Erreur de mesure / échantillonnage
    6. Environnemental
    7. Autre
  - **Disposition** dropdown (aksiyon türü)
  - **Proof document** — dosya yükleme
  - **BR-QA-11:** "un document justificatif est requis pour Retour fournisseur / Rebut / Dérogation"

**Bizde durum:**
- NCR modeli var, description var
- Root cause **serbest metin** — sabit taksonomi yok
- BR-QA-11 (justificatif zorunluluğu) yazılı ama enforcement zayıf

**Yapılması gereken:**
- `NCR.root_cause_category` — 8-choice enum
- `NCR.disposition` — enum (Retour fournisseur / Rebut / Dérogation / Rework / Accept)
- Validator: disposition ∈ {"return","scrap","waiver"} ise `proof_document` NOT NULL (BR-QA-11)

**Öncelik:** 🟡 ORTA

---

### 2.8 Stok Yönetimi

**UsineERP'de olan (IMG_8355–8365):**
- **Stok detay sayfası:**
  - Niveau de stock — yeşil progress bar
  - Seuil d'alerte (5000)
  - Seuil de rupture (1000)
  - Valeur du stock (DA cinsinden, canlı)
  - Accès rapides sidebar
- **Historique des mouvements** — birleşik hareket geçmişi
  - Consommation / Réception badge'leri
  - Prix Unitaire kolonu
- **Ajustement de stock** formu:
  - Type d'ajustement
  - Motif (sebep, serbest metin)
  - Auto-Générer récap
  - Qté avant → Qté après → Delta
  - Document justificatif (opsiyonel dosya)

**Bizde durum:**
- Stok modeli var, hareketler tabloda görünüyor
- Progress bar / eşik göstergesi yok
- Ajustement formu zayıf, motif zorunlu değil
- Consommation/Réception unified history yok

**Öncelik:** 🟡 ORTA

---

### 2.9 Ticari / Sales

**UsineERP'de olan (IMG_8480, 8485):**
Sidebar yapısı:
- **Allocations d'avance (§23 planifié)** — avans tahsisi
- **Avances Client (§23 planifié)** — müşteri avansı
- **BL Clients** — irsaliye (delivery note)
- **Client invoice dn links** — irsaliye-fatura eşleştirme
- **Encaissements Client** — tahsilat
- **Factures Client** — fatura
- **Lignes BL Client** — irsaliye satırları
- **Règlements compte client** — cari hesap kapatma

**Bizde durum:**
- Fatura ✅
- Payment (check/transfer/cash) ✅ — bu bizde tamam
- **BL (irsaliye) belgesi ayrı YOK** — fatura direkt kesiyoruz
- Avance/Encaissement §23 planlanmış ama implement değil
- Cari hesap kapama (règlement) yok

**Yapılması gereken:**
```python
class DeliveryNote(models.Model):  # BL Client
    bl_number = models.CharField(unique=True)
    customer = models.ForeignKey(Customer)
    delivery_date = models.DateField()
    truck_plate = models.CharField()
    driver_name = models.CharField()
    invoice = models.ForeignKey(Invoice, null=True)  # sonradan fatura

class CustomerAdvance(models.Model):  # §23
    customer = models.ForeignKey(Customer)
    amount = models.DecimalField(...)
    ...

class AdvanceAllocation(models.Model):  # §23
    advance = models.ForeignKey(CustomerAdvance)
    invoice = models.ForeignKey(Invoice)
    amount = models.DecimalField(...)
```

**Öncelik:** 🟠 YÜKSEK (BL Client), 🟡 ORTA (avans)

---

### 2.10 Reporting / Analytics

**UsineERP'de olan (IMG_8500):**
- **Tableau de bord reporting** — ayrı reporting dashboard
- Date filtreleri: Mois / Trimestre / Année + custom range
- 4 KPI kart: REVENUS FACTURÉS / CHARGES TOTALES / RÉSULTAT NET (Bénéfice/Perte badge) / DÉPENSES OPÉRAT.
- Charts: **Revenus vs Charges** (bar), **Répartition des charges** (doughnut)
- **Accès rapide aux rapports** — 6 rapor kartı:
  1. Résultat financier (P&L)
  2. Échéancier clients (aging alacaklar)
  3. Échéancier fournisseurs (aging borçlar)
  4. Rendements production
  5. Répartition dépenses
  6. Valorisation stocks
- **Dernières exécutions** paneli — geçmiş rapor çalışmaları

**Bizde durum:**
- Bizim `/portal/muhasebe/dashboard` çok iyi — 8 KPI + 6 chart var, hatta UsineERP'den fazla ✅
- Ama **Rapports hub** yok — kullanıcı rapor kartlarından seçim yapamıyor
- **Report execution log** yok (kim ne zaman hangi raporu çalıştırdı)

**Yapılması gereken:**
- `/portal/rapports/` hub sayfası (6 tile)
- `ReportExecution` modeli (audit trail)

**Öncelik:** 🟡 ORTA

---

## 3. Öncelik Sıralı Uygulama Yol Haritası

### Sprint 1 (1 hafta) — 🔴 KRİTİK üretim
- [ ] `FormulationLine.is_complement` + tolerance_pct
- [ ] Bilan massique §22 hesabı (services)
- [ ] `ProductionOrder.scale_factor`
- [ ] Besoins théoriques MP UI (AJAX stok kontrolü)

### Sprint 2 (1 hafta) — 🟠 KALİTE ekosistemi
- [ ] `QualitySpec.approved_by` + versiyon UI
- [ ] `SpecLine` per-Gate checkbox + is_critical
- [ ] `TestProperty.decimal_precision`
- [ ] Portal QA sidebar'a "Katalog: Özellikler/Testler"
- [ ] `SamplingPlan` modeli + CRUD
- [ ] `Sample.spec_version` kilit (BR-QA-04)
- [ ] Sonuç girişi UI'da anlık pass/fail badge

### Sprint 3 (1 hafta) — 🟠 TİCARİ
- [ ] `DeliveryNote` (BL Client) modeli + CRUD
- [ ] BL → Fatura dönüşümü akışı
- [ ] BL satırları modeli

### Sprint 4 (1 hafta) — 🟡 ORTA öncelik
- [ ] NCR root cause + disposition enum'ları
- [ ] BR-QA-11 enforcement (justificatif zorunlu)
- [ ] Stok detay: progress bar + eşikler
- [ ] Ajustement formu detaylandırma
- [ ] Reporting hub (`/portal/rapports/`)
- [ ] `ReportExecution` audit trail

### Sprint 5 (opsiyonel) — İleri özellikler
- [ ] Avance Client / Allocation (§23)
- [ ] Cari hesap kapama (règlement)
- [ ] BL-Fatura eşleştirme raporu

---

## 4. Bizim Avantajlarımız (UsineERP'de olmayan)

Adalet açısından, bazı alanlarda **biz öndeyiz**:

- ✅ **12 non-negotiable rules** (Django signals) — UsineERP'de sadece BR referansları var, enforcement yumuşak
- ✅ **8-part gate** — UsineERP'de sadece 3 gate (A/B/C)
- ✅ **Cezayir SCF (PCN 2010) muhasebe planı** — tam entegre
- ✅ **TVA G50 / DGI e-fatura** hazırlığı — UsineERP'de görülmedi
- ✅ **Şirket profili + logo + PDF/print** — bizde profesyonel, UsineERP'de basit
- ✅ **Müşteri bazlı iskonto** — otomatik autofill, UsineERP'de manuel
- ✅ **Ödeme yöntemleri** — CHECK/BANK/CASH ayrı paneller, 13 banka enum, çek durumu takibi
- ✅ **Portal turu + validation kontrolü** hazırlığı
- ✅ **Fatura eki (attachment)** — DGI orijinali için
- ✅ **Beyaz sidebar teması** — Notion/Linear tarzı modern

---

## 5. Sonuç

**Öz:** UsineERP bizim referansımız olabilir — özellikle **kalite (QA/Lab), formülasyon ve üretim** taraflarında. Ama biz de **muhasebe uyumu, ödeme çeşitliliği, ve MCOS-uyum** taraflarında ondan iyiyiz.

**Tahmini toplam iş yükü:** 4 sprint × 1 hafta = ~4 hafta
**Beklenen sonuç:** İşleyen bir çimento katkı üreticisi ERP'sinin **%100 fonksiyon paritesi** + Cezayir yerelleştirmesi.

---

*Bu rapor 20 Ağustos 2026 tarihli 30+ ekran görüntüsü analizinden üretildi. UsineERP muhtemelen benzer bir MCOS metodolojisi ile geliştirilmiş; bu benzerlik iki sistem arasında migrasyon köprüsü kurulabileceğini gösteriyor.*
