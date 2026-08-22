# 04 — Kalite / QA Modülü

**Kime yönelik:** Kalite sorumluları (QA), lab teknisyenleri, kalite müdürü
**Süre:** 90 dakika
**Ön koşul:** `01_giris.md` okundu

Bu belge Kalite modülünün tüm kısımlarını içerir:
1. Kalite Kataloğu (QC Parametreleri + EN 480 metotları)
2. Kalite Şartnameleri (Spécifications Qualité)
3. QA Onay Akışı ve Versiyonlama
4. Per-Gate Kontrolü (Gate A/B/C)
5. Örnekleme Planları (Plans d'échantillonnage · BR-QA-12)
6. Numune Alma ve Sonuç Girişi (BR-QA-04)
7. Uygunsuzluk Yönetimi (NCR + BR-QA-11)
8. COA (Certificate of Analysis)
9. CAPA (Düzeltici Faaliyet)
10. Portal İzleme ve Raporlar

---

## 1. Kalite Kataloğu (QC Parametreleri)

### 1.1 QC Parametresi Nedir?

Bir QC parametresi, kalite şartnamelerinde kullanılan ölçülebilir bir özelliktir. Örnekler:
- **pH** (birim: yok, precision: 1)
- **DENSITY** (birim: g/cm³, precision: 3)
- **SOLIDS** (Katı %) (birim: %, precision: 2)
- **CHLORIDE** (birim: %, precision: 3)
- **VISCOSITY** (birim: mPa·s, precision: 2)

### 1.2 Katalog Görüntüleme

**Yol:** Sol menü → **Kalite** → **Özellik / Test Kataloğu**

Doğrudan URL: `/portal/kalite/katalog/`

Tabloda görürsünüz:
- **Kod** (ör. `PH`)
- **Özellik adı** (Türkçe/İngilizce)
- **Birim** (ör. `g/cm³`)
- **Yöntem** (ör. `EN 480-8 (Katı madde %)`, `EN ISO 758 (Yoğunluk)`)
- **Ondalık hane** (precision — sonuç girişinde kullanılır)

### 1.3 Yeni Parametre Ekleme

**Yol:** Admin → `/admin/quality/qcparameter/add/`

1. **Kod:** Benzersiz — ör. `TEMP`
2. **Ad:** Ör. `Sıcaklık`
3. **Birim:** `°C`
4. **Metot:** Dropdown'dan seçin (EN 934-2, EN 480-1, EN 480-8, EN 480-10, ISO 758, İç metot)
5. **EN 480 metot referansı** (opsiyonel serbest metin): ör. `EN 480-8 § 5.2`
6. **Decimal precision:** 2 (varsayılan)
7. **Aktif:** True
8. **Kaydet**

Bu parametreyi artık şartnamelerde ve numune sonuçlarında kullanabilirsiniz.

---

## 2. Kalite Şartnameleri (Spécifications Qualité)

### 2.1 Şartname Nedir?

Bir kalite şartnamesi, bir **ürün (Product)** veya **hammadde (RawMaterial)** için bir parametrenin uygun sınırlarını tanımlar.

Örn: `ADX-100 · pH · min: 4.5, max: 7.0, target: 6.0 · Gate C'de kontrol edilir · BR-QA-05 KRİTİK`

### 2.2 Şartname Listesi

**Yol:** Sol menü → **Kalite** → **Şartnameler (Spécifications)**

Doğrudan URL: `/portal/kalite/sartname/`

Tabloda görürsünüz:
- **Hedef** (Ürün veya Hammadde)
- **Özellik** (ör. `PH (birim)`)
- **v** (versiyon)
- **Min / Max**
- **Gates** (A/B/C rozetleri — hangi Gate'te kontrol edilir)
- **Kritik** (BR-QA-05 rozet — kritik parametreler için)
- **Durum** (Aktif / Pasif)
- **QA Onay** (imzalayan kişi)

**Filtre:** "Sadece aktif" veya "Tümü"

### 2.3 Yeni Şartname Oluşturma

**Yol:** Admin → `/admin/quality/qcspec/add/`

1. **Parametre:** Katalogdan seçin (ör. PH)
2. **Ürün** veya **Hammadde** — sadece birini seçin (XOR)
3. **Değerler:**
   - Min: `4.5`
   - Max: `7.0`
   - Target: `6.0` (nominal)
   - Tolerance (%): `5.0`
4. **is_mandatory:** True (bu parametreyi ölçmek zorunlu mu)
5. **is_critical (BR-QA-05):** True → bu parametrenin ihlali kritik NCR açar
6. **Per-Gate kontrolü:**
   - `check_at_gate_a`: Gate A'da (mal kabul) kontrol
   - `check_at_gate_b`: Gate B'de (üretim ara) kontrol
   - `check_at_gate_c`: Gate C'de (bitmiş ürün) kontrol
7. **Versiyonlama:**
   - **Versiyon:** 1, 2, 3, ... (aynı ürün+parametre için birden fazla versiyon olabilir)
   - **Yürürlük tarihi**
   - **is_active:** True (aynı hedef için sadece bir aktif olabilir)
8. **QA onayı:**
   - **Oluşturan** (auto: sizin kullanıcınız)
   - **Onaylayan (QA):** QA yetkilisi
   - **Onay zamanı**

**Önemli:** `is_active=True` yapmak için `approved_by` alanı DOLU olmalıdır. Aksi halde sistem hata verir (BR-QA-05 gereği — kalite bakış açısıyla).

---

## 3. QA Onay Akışı ve Versiyonlama

### 3.1 Neden Versiyonlama?

Şartnameler zamanla değişir:
- Müşteri geribildirimi ile tolerans daralır
- Yeni yasal gereklilik → sıkı limit
- Ürün formülü güncellenir → parametre değişir

Her değişiklik yeni bir **versiyon**dur. Eskiler saklanır (audit trail).

### 3.2 Versiyon Değiştirme

Örneğin `ADX-100 pH v1` (min 4.5, max 7.0) yerine yeni **v2** (min 4.8, max 6.8) kullanmak isterseniz:

1. **Yeni QCSpec oluştur:** aynı ürün+parametre, `version=2`, yeni min/max
2. Eski v1'i düzenle: `is_active=False` yap
3. Yeni v2'yi kaydederken `is_active=True` yap (QA onaylı olmalı)

Sistem otomatik kontrol eder — aynı ürün+parametre için sadece **bir** aktif versiyon olabilir.

### 3.3 Şartname Detay Sayfası

Bir şartnameye tıkladığınızda:
- **Limit değerleri kartı** (Min / Hedef / Max / Tolerans)
- Kritik bayrağı varsa BR-QA-05 uyarısı
- **Gate kontrolleri** (üç kart — A/B/C renkli)
- **Versiyon + QA onayı** paneli
- **Diğer versiyonlar** listesi

Bu sayfa, denetleyicilere sunulacak şartname belgesi olarak PDF'e çıkarılabilir *(bu özellik yakında)*.

---

## 4. Per-Gate Kontrolü (Gate A / B / C)

MCOS metodolojisinde üretim üç ana Gate'ten geçer:

- **Gate A** — Mal Kabul (RM giriş kalitesi)
- **Gate B** — Üretim Ara (IPC — in-process control)
- **Gate C** — Bitmiş Ürün (PF final QC)

### 4.1 Gate'ler Nasıl Belirlenir?

Şartname oluştururken her parametrenin hangi Gate'te kontrol edileceğini işaretlersiniz. Örnekler:

| Parametre | Gate A | Gate B | Gate C |
|-----------|--------|--------|--------|
| pH | ⬜ | ✅ | ✅ |
| Density | ⬜ | ⬜ | ✅ |
| Solids | ⬜ | ⬜ | ✅ |
| Chloride | ⬜ | ⬜ | ✅ (Kritik BR-QA-05) |
| Viscosity | ⬜ | ✅ | ✅ |

**Tipik pattern:**
- Fizik-kimyasal özellikler (Density, Solids) → sadece Gate C
- Kritik parametreler (Chloride) → Gate C + kritik bayrağı
- Reaksiyon kontrolleri (pH, sıcaklık) → Gate B + Gate C

---

## 5. Örnekleme Planları (Plans d'échantillonnage · BR-QA-12)

### 5.1 Örnekleme Planı Nedir?

Bir örnekleme planı, **hangi Gate'te**, **hangi tetikleyicide**, **hangi sıklıkta** numune alınacağını tanımlar.

### 5.2 Örnekleme Planı Listesi

**Yol:** Sol menü → **Kalite** → **Örnekleme Planları**

Doğrudan URL: `/portal/kalite/orneklem-plani/`

Tabloda görürsünüz:
- Plan Kodu (ör. `SP-PF-001`)
- Hedef (Ürün veya Hammadde)
- Gate (A/B/C renkli badge)
- Tetikleyici (À la réception, Par batch, vs.)
- Sıklık (1/N — her N'de bir)
- Numune Boyutu Kuralı
- Durum (Aktif / Pasif)

### 5.3 Yeni Plan Oluşturma

**Yol:** Admin → `/admin/quality/samplingplan/add/`

1. **Kod:** Ör. `SP-PF-001`
2. **Ad:** Ör. `Bitmiş ürün · her batch pH + yoğunluk`
3. **Uygulama alanı:** Ürün VEYA Hammadde
4. **Gate:** A / B / C
5. **Tetikleyici:**
   - `À la réception` (mal kabulde)
   - `Par ligne de BL` (BL satırı başına)
   - `Après mélange` (mikslemeden sonra)
   - `Par batch de production` (üretim batch'i başına)
   - `À l'expédition` (sevkiyatta)
   - `Programmé (calendrier)` (planlı)
6. **Sıklık (Frequency N):** 1 = her batch, 5 = 5 batch'te bir
7. **Numune boyutu kuralı:** Serbest metin (ör. `sqrt(N)+1`, `3 numune sabit`, `MIL-STD-105E S-2`)
8. **is_active:** True

### 5.4 BR-QA-12 — Deaktivasyon Sebebi

Bir örnekleme planını pasifleştirmek istiyorsanız:
- `is_active` = False
- `deactivation_reason` **zorunlu** — neden pasif yapıldı yazılmalı

Sistem bunu enforce eder (`clean()` validation). Boşsa hata verir.

**Örnek gerekçe:** *"Metot değiştiği için yeni plan SP-PF-002 devreye alındı, eski plan geçersiz kılındı."*

---

## 6. Numune Alma ve Sonuç Girişi (BR-QA-04)

### 6.1 Numune Nedir?

Bir batch veya lot için alınan fiziksel örneğe **numune (Sample)** denir. Numune üzerinde parametrik testler yapılır → sonuçlar `QCTestResult` olarak kaydedilir.

### 6.2 BR-QA-04 — Spec Kilidi

Numune alındığı anda, o üründe/lotta aktif olan **QCSpec versiyonu numune ile kilitlenir** (`spec_locked` alanı).

Sonradan spec değişse bile, bu numune eski spec ile değerlendirilir. Bu **çok kritik** — audit sırasında "hangi spec ile geçti/kaldı" sorusunun net cevabıdır.

### 6.3 Yeni Test Sonucu Girme

**Yol:** Admin → `/admin/quality/qctestresult/add/`

Alternatif: Portal → **Kalite** → **Test Sonuçları**

1. **Parametre:** Katalogdan seçin (ör. PH)
2. **Lot VEYA Batch:** Sadece birini seçin
   - Lot = hammadde partisi (Gate A testi)
   - Batch = mamul üretim partisi (Gate B/C testi)
3. **spec_locked:** O anda aktif QCSpec otomatik seçilir (BR-QA-04)
4. **Gate:** A / B / C (hangi Gate'te alındı)
5. **Değer:** Ölçüm sonucu (parametrenin precision'una göre yuvarlar)
6. **Verdict:** Otomatik hesaplanır spec'e göre (`evaluate()` methodu):
   - PASS (min-max arası)
   - FAIL (dışarıda)
   - NA (uygulanamaz)
7. **Testi yapan:** Lab teknisyeni adı
8. **Notlar:** Serbest metin

### 6.4 Numune Sonuç Ekranı (UsineERP tarzı)

Portal'da numune için özet ekran:
- Numune numarası (ör. `ECH-2026-0002`)
- **Spécification verrouillée: PF-002 - superplastifiant karamix 3020 — v1 (BR-QA-04)**
- Parametre listesi ve nominal/limit değerleri
- **CRITIQUE** bayrağı olanlar sarı/kırmızı vurgu
- Boş **VALEUR RELEVÉE** kutuları
- **Enregistrer les résultats** butonu

---

## 7. Uygunsuzluk Yönetimi (NCR — Non-Conformance Report)

### 7.1 NCR Nedir?

Bir NCR (Non-Conformance Report), bir ürün/proses/sistem uygunsuzluğunu belgeler. Kaynaklar:
- Kalite testi (FAIL sonuç)
- Üretim (tolerans aşımı)
- İç denetim
- Tedarikçi (hammadde uygunsuzluğu)
- Müşteri şikayeti
- Bakım
- İSG/Çevre

### 7.2 NCR Açma

**Yol:** Sol menü → **QMS** → **Uygunsuzluk (NCR)** → **+ Yeni NCR**

Alternatif admin: `/admin/qms/nonconformance/add/`

1. **NCR No:** Ör. `NCR-2026-0042`
2. **Kaynak:** Dropdown (QC_TEST, PRODUCTION, INTERNAL_AUDIT, SUPPLIER, CUSTOMER_COMPLAINT, MAINTENANCE, EHS, OTHER)
3. **Şiddet (Severity):** LOW / MEDIUM / HIGH / CRITICAL
4. **Tespit zamanı**
5. **Tespit eden:** Sizin kullanıcınız (otomatik)
6. **Başlık:** Kısa özet
7. **Açıklama:** Detay
8. **Hedef (Generic FK):** Hangi kaydı etkiliyor (batch, lot, order vs.)
9. **Etkilenen miktar:** Ör. `500 kg`
10. **Gate:** A / B / C (hangi Gate'te tespit)
11. **Root cause category (7 seçenek + Autre):**
    - Qualité fournisseur
    - Équipement
    - Process / Opérateur
    - Conception formule
    - Erreur de mesure / échantillonnage
    - Environnemental
    - Autre
12. **Disposition:** PENDING → USE_AS_IS / REWORK / **REJECT** / **RETURN_TO_SUPPLIER** / DOWNGRADE / **WAIVER**
13. **Justificatif belge (BR-QA-11):** PDF/JPG yükle

### 7.3 BR-QA-11 — Justificatif Zorunluluğu

**Disposition = REJECT, RETURN_TO_SUPPLIER veya WAIVER (Dérogation)** ise `proof_document` **ZORUNLU**dur.

- Sistem `clean()` validation ile kontrol eder
- Boşsa: `"BR-QA-11 : un document justificatif est requis pour Retour fournisseur / Rebut / Dérogation."` hatası

Bu belge tipik olarak:
- REJECT için: İmha tutanağı
- RETURN_TO_SUPPLIER için: İade tebliğ mektubu + tedarikçi cevabı
- WAIVER için: Kalite müdürü onay yazısı

### 7.4 NCR Yaşam Döngüsü

```
OPEN → INVESTIGATING → DISPOSITIONED → CLOSED
                                     ↘ CANCELLED
```

- **OPEN:** Yeni açıldı
- **INVESTIGATING:** İnceleme sürüyor
- **DISPOSITIONED:** Karar verildi (disposition seçildi)
- **CLOSED:** Kapatıldı (tüm aksiyonlar tamamlandı)
- **CANCELLED:** İptal

---

## 8. COA (Certificate of Analysis)

### 8.1 COA Nedir?

Bir COA, bir üretim partisinin kalite özet belgesidir. Müşteriye sevk edilen her ürünle birlikte gider.

### 8.2 COA Otomatik Üretme

**Yol:** Admin → ProductionBatch listesi → Batch seç → **Action** → **COA üret + yayımla**

Alternatif: `/admin/quality/certificateofanalysis/`

1. Batch seçilir
2. Sistem otomatik olarak `QCTestResult`'lara bakar
3. Tüm ölçümler PASS ise COA `ISSUED` durumuna geçer
4. Bir FAIL varsa COA üretilmez (batch RELEASED değil demektir)

COA içeriği:
- COA No
- Batch No + ürün + reçete versiyonu
- Üretim tarihi
- Parametre listesi + ölçülen değer + verdict + metot
- İmza + tarih

### 8.3 COA PDF İndirme

*(Bu özellik yakında — şu an admin action ile üretilir)*

---

## 9. CAPA (Corrective and Preventive Action)

### 9.1 CAPA Nedir?

Bir CAPA, bir uygunsuzluğun kök nedenini ortadan kaldıracak (Corrective) veya oluşmasını önleyecek (Preventive) aksiyondur.

### 9.2 Yeni CAPA

**Yol:** Sol menü → **QMS** → **CAPA**

1. **CAPA No**
2. **Bağlı NCR** (varsa)
3. **Tip:** CORRECTIVE / PREVENTIVE
4. **Açıklama**
5. **Kök neden analizi** (5 Why, Fishbone vs.)
6. **Aksiyon planı**
7. **Sorumlu**
8. **Son tarih**
9. **Etkinlik kontrolü (effectiveness check):** Aksiyon işe yaradı mı?

---

## 10. Portal İzleme ve Raporlar

### 10.1 Kalite Panosu

**Yol:** Sol menü → **Kalite Panosu**

- Bekleyen lot testleri
- Bekleyen parti testleri (QC_HOLD)
- Son 30 gün toplam test / PASS / FAIL
- FAIL oranı (kırmızı → %5+ tehlikeli)

### 10.2 Şartname Uyum İzleme

**Yol:** Sol menü → **Kalite** → **Şartnameler** → sadece **aktif** filtresi

Bir bakışta:
- Kaç aktif şartname var
- Kaç tanesi QA onaylı (yeşil ✓)
- Kaç tanesi onay bekliyor (kırmızı ⚠)

---

## 11. Sık Sorulan Sorular

**S: Şartnameyi aktif yapmaya çalıştım ama hata veriyor?**
C: `approved_by` alanı boş. QA yetkilisini seçin, `approved_at` otomatik dolar, sonra kaydedin.

**S: Aynı ürün+parametre için iki aktif şartname olabilir mi?**
C: Hayır. Sistem `UniqueConstraint` ile engelliyor. Eskiyi pasif yapmadan yeniyi aktif edemezsiniz.

**S: Numune aldım ama spec_locked otomatik dolmadı?**
C: O ürün için aktif QCSpec yok. Önce şartnameyi oluşturup aktifleştirin, sonra numuneyi girin.

**S: NCR açtım ama proof_document istiyor?**
C: Disposition'ınız REJECT / RETURN_TO_SUPPLIER / WAIVER. Belge yükleyin veya disposition'ı REWORK gibi değiştirin.

**S: Örnekleme planını pasif yapmaya çalıştım ama sebep istiyor?**
C: BR-QA-12 gereği zorunlu. `deactivation_reason` alanına net gerekçe yazın.

**S: Gate A'da test yapmam gerekiyor ama şartnamem sadece Gate C işaretli?**
C: Şartnameyi düzenleyin, `check_at_gate_a=True` yapın. Alternatif: yeni versiyon oluşturun.

**S: FAIL çıkan bir test batch'i nasıl etkiler?**
C: Batch otomatik `QC_HOLD` durumuna düşer. QA kararı ile RELEASED (waiver) veya REJECTED yapılır. NCR açılabilir.

---

## 12. Uygulama Egzersizi

1. **Yeni QC parametre:** `VISCOSITY`, birim `mPa·s`, EN 480-4 metodu, precision 2
2. **Şartname:** `ADX-100 · pH v2` (min 5.0, max 6.5, kritik, Gate C, QA onaylı)
3. **Örnekleme planı:** `SP-PF-002` — her PF batch'inde 1 numune, Gate C
4. **Test sonucu:** Bir batch için pH=5.8 sonucu gir → PASS otomatik hesaplanmalı
5. **NCR:** Bir tedarikçiden gelen lot için CHLORIDE FAIL, Return to supplier disposition + justificatif belge

Her egzersizi bitirdiğinizde kalite müdürüne gösterin.
