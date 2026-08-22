# 06 — Satış Modülü

**Kime yönelik:** Satış temsilcileri, satış müdürü, teknik danışman
**Süre:** 90 dakika
**Ön koşul:** `01_giris.md` okundu

Bu belge Satış modülünün tüm kısımlarını içerir:
1. Müşteri Yönetimi
2. Satış Siparişi (Sales Order)
3. BL Client — Bordereau de Livraison (İrsaliye)
4. BL → Fatura Dönüşüm Akışı
5. Trial Batch (Deneme Partisi)
6. Mix Design Consultation (Reçete Danışmanlığı)
7. Applicator Training (Uygulayıcı Eğitimi)
8. Performance Warranty (Garanti Belgesi)
9. Customer Site Test (Saha Kabul Testi)
10. BL-Fatura Eşleştirme Raporu

---

## 1. Müşteri Yönetimi

### 1.1 Yeni Müşteri Ekleme

**Yol:** Admin → `/admin/masterdata/customer/add/`

1. **Kod:** Ör. `C-2026-045` (otomatik sıralı önerilir)
2. **Ad:** Ör. `SARL Cimenterie Blida`
3. **İletişim (contact):** Telefon, e-posta karışık
4. **Adres:** Sokak, şehir, ülke
5. **E-posta**
6. **Default İskonto (%):** Ör. `10.00` — bu müşteriye kesilen faturalarda otomatik uygulanır
7. **Aktif:** True

### 1.2 Müşteri Listesi

**Yol:** Admin → `/admin/masterdata/customer/`

- **list_editable:** İskonto oranı listeden düzenlenebilir (tıklayıp değiştir + Kaydet)
- **Search:** kod veya isim

### 1.3 Müşteri İskonto Otomatik Uygulaması

Yeni fatura kesiminde:
1. Müşteri dropdown'undan seçin
2. Eğer o müşteride `default_discount_pct > 0` ise:
   - **"İskonto Oranı" alanı otomatik dolar** (ör. `%15`)
   - Yeşil onay mesajı: `✓ Bu müşteri için tanımlı iskonto: %15`
3. Farklı iskonto uygulanacaksa manuel değiştirilebilir

---

## 2. Satış Siparişi (Sales Order)

### 2.1 Yeni Sipariş

**Yol:** Admin → `/admin/sales/salesorder/add/`

1. **Sipariş No:** Ör. `SO-2026-0042`
2. **Müşteri**
3. **Sipariş tarihi**
4. **Sevk tarihi** (planlanan)
5. **Durum:** DRAFT (varsayılan)
6. **Notlar**

**Satırlar (inline):**
- Ürün
- Miktar
- Birim
- Birim fiyat (DZD/kg)

### 2.2 Sipariş Durum Akışı

```
DRAFT → CONFIRMED → PARTIAL → SHIPPED
                            ↘ CANCELLED
```

- **DRAFT:** Taslak (henüz onaylanmadı)
- **CONFIRMED:** Onaylandı, sevkiyata hazır
- **PARTIAL:** Kısmi sevk (bazı satırlar sevk edildi)
- **SHIPPED:** Tam sevk edildi
- **CANCELLED:** İptal

### 2.3 Sipariş Statüsü Otomatik Güncellenir

Her sevkiyat kaydı sonrası sistem `refresh_status()` çağırır:
- Toplam sevk edilen = 0 → CONFIRMED
- 0 < sevk < toplam → PARTIAL
- sevk ≥ toplam → SHIPPED

---

## 3. BL Client — Bordereau de Livraison (İrsaliye)

### 3.1 BL Client Nedir?

Bordereau de Livraison (BL, kısaca "İrsaliye"), sevk edilen ürünün fiziksel çıkış belgesidir. Cezayir'de fatura kesilmeden **önce** BL çıkar; fatura sonradan bir veya birden fazla BL'yi kapsar.

### 3.2 BL Client Listesi

**Yol:** Sol menü → **Satış** → **BL Client (İrsaliye)**

Doğrudan URL: `/portal/satis/bl/`

**KPI Kartları (üstte):**
- Taslak sayısı
- Teslim edildi (faturaya hazır)
- Faturalandı
- İptal

**Tablo:**
- Checkbox (fatura kesmek için seç)
- BL No, Müşteri, Sipariş, Sevk Tarihi
- Şoför / Plaka
- **Durum badge (renkli):**
  - ⚫ Taslak
  - 🟠 Teslim
  - 🟢 Faturalandı
  - 🔴 İptal
- Fatura (varsa link)

**Filtre butonları:** Tümü / Taslak / Teslim edildi / Faturalandı / İptal

### 3.3 Yeni BL Client Oluşturma

**Yol:** Admin → `/admin/sales/shipment/add/`

Doğrudan portal formu yok — admin arayüzü kullanılır (varsayılan).

1. **Shipment Number (BL No):** Ör. `BL-202608-042`
2. **Müşteri**
3. **Sales Order** (opsiyonel — hangi sipariş için)
4. **Sevk tarihi**
5. **Sevkiyat detayı:**
   - Taşıyıcı (ör. `Trans Cezayir SARL`)
   - Araç plakası (ör. `01234-11-16`)
   - Şoför adı (ör. `Mohamed Belaidi`)
   - Teslim adresi
6. **Status:** DRAFT (varsayılan)
7. **Notlar**

**Satırlar (Shipment Lines inline):**
- SO Line
- Output Container (IBC) — RELEASED bir batch'ten
- Miktar

**Doğrulama (BR):**
- IBC (Output Container) yalnız **QC-RELEASED** partilerden sevk edilebilir
- Bir IBC iki kez sevk edilemez (OneToOne + shipment_reference kontrolü)
- SO satırı verilmişse ürünler eşleşmelidir

### 3.4 BL Detay Sayfası

BL detayına tıklayınca (portal'da):
- BL numarası + status badge
- Müşteri + sipariş
- **Sevkiyat detayı** kartı (tarih, taşıyıcı, plaka, şoför, teslim adresi)
- **Satırlar tablosu (IBC bazlı):**
  - Ürün
  - IBC kod
  - Miktar
  - Birim fiyat
  - Tutar (HT)
- **Toplam (HT)** en altta
- **Faturalandırma** paneli:
  - Eğer BL faturalanmış: fatura link
  - Değilse: **"🧾 Bu BL'den Fatura Oluştur"** butonu

### 3.5 BL Durum Akışı

```
DRAFT → DELIVERED → INVOICED
              ↘ CANCELLED
```

- **DRAFT:** Taslak (yeni oluşturulmuş)
- **DELIVERED:** Ürün teslim edildi (fatura kesilmeye hazır)
- **INVOICED:** Faturalandı (fatura link'i var)
- **CANCELLED:** İptal edilmiş

---

## 4. BL → Fatura Dönüşüm Akışı

### 4.1 Tek BL'den Fatura Oluşturma

**Yol:** BL detay sayfasında → **"🧾 Bu BL'den Fatura Oluştur"** butonu

Sistem otomatik:
1. Yeni `Invoice` (SALES tipi) oluşturur
2. Müşterinin `default_discount_pct` fatura başlığına taşınır (otomatik iskonto)
3. Her BL satırı için bir InvoiceLine (IBC bilgisiyle)
4. Fatura numarası: `INV-BL-<timestamp>`
5. Vade tarihi: fatura tarihi + 30 gün
6. BL durumu `INVOICED`, `invoice` alanı bağlanır
7. Fatura durumu `DRAFT` — muhasebe süreçleri devam eder

### 4.2 Çoklu BL'den Tek Fatura

**Yol:** BL listesinde birden fazla BL'nin checkbox'ını işaretle → **"🧾 Seçili BL'lerden Fatura Oluştur"**

**Kısıtlar:**
- Tüm seçili BL'ler **aynı müşteriye ait** olmalı (aksi halde hata)
- Hiçbiri INVOICED olmamalı (aksi halde hata)
- Hiçbiri CANCELLED olmamalı
- Her BL'de en az bir satır olmalı

Sistem tüm satırları tek faturaya birleştirir.

### 4.3 İskonto Otomatik Uygulama

Müşteri `default_discount_pct = 10.00` ise:
- Fatura başlığında `discount_pct = 10.00`
- `recompute_invoice()` iskonto tutarını hesaplar:
  - `multiplier = (100 - 10) / 100 = 0.9`
  - `discount_amount = total_line_ht × 10/100`
  - `invoice.total_ht = total_line_ht - discount_amount`
  - `invoice.total_tva = total_line_tva × 0.9`

BL detay sayfasında bilgi görünür: `Müşteri iskonto (%10,00) otomatik uygulanır.`

---

## 5. Trial Batch (Deneme Partisi)

### 5.1 Trial Batch Nedir?

Müşteri sipariş vermeden önce, küçük bir numune ile saha testi yapmak için gönderilir. Sika/BASF modeli: müşterinin kendi çimentosuyla, kendi sahasında test.

### 5.2 Yeni Trial Batch

**Yol:** Admin → `/admin/sales/trialbatch/add/`

1. **Trial No:** Ör. `TRL-2026-001`
2. **Müşteri**
3. **Ürün adayı**
4. **Deneme tarihi**
5. **Numune miktarı:** Ör. `25 kg` (küçük deneme paketi)
6. **Birim:** kg
7. **Saha adresi:** Deneme yapılacak inşaat/santral
8. **Müşteri çimento markası:** Ör. `Ciments d'Algérie CEM I`
9. **Çimento sınıfı:** Ör. `CEM I 42.5 R`
10. **Agrega max boyutu:** Ör. `20 mm`
11. **Hedef slump:** Ör. `S4 (160-210 mm)`
12. **Hedef w/c oranı:** Ör. `0.450`
13. **Doz (%):** Çimento ağırlığına göre önerilen doz
14. **Sorumlu:** Sizin kullanıcınız

### 5.3 Trial Sonuçları

Deneme yapıldıktan sonra saha ekibi sonuçları girer:
- **İlk slump (mm)**
- **30 dk slump**
- **60 dk slump**
- **90 dk slump**
- **Saha sıcaklığı (°C)**
- **Saha ekibi notları**

### 5.4 Trial Durum Akışı

```
PLANNED → SHIPPED → IN_TRIAL → SUCCESS
                           ↘ FAILED
                           ↘ CANCELLED
```

- **PLANNED:** Deneme planlandı
- **SHIPPED:** Numune sevk edildi
- **IN_TRIAL:** Saha testinde
- **SUCCESS:** Başarılı — müşteri sipariş vermeye uygun
- **FAILED:** Başarısız — reçete revizyonu gerekir
- **CANCELLED:** İptal

---

## 6. Mix Design Consultation (Reçete Danışmanlığı)

### 6.1 Mix Design Consultation Nedir?

Müşteri özel projesi için katkı dozaj optimizasyonu — sıcak/soğuk iklim formülü, ekstra dayanım için karışım.

### 6.2 Yeni Consultation

**Yol:** Admin → `/admin/sales/mixdesignconsultation/add/`

1. **Consultation No:** Ör. `MDC-2026-001`
2. **Müşteri**
3. **Talep tarihi**
4. **Proje adı:** Ör. `Baraj enjeksiyon karışımı - Béjaïa`
5. **Beton sınıfı hedefi:** Ör. `C40/50`
6. **Özel gereksinimler:** Sıcak iklim, deniz suyu maruziyeti, erken dayanım
7. **Önerilen ürün(ler):** Ör. `ADX-A + ADX-B`
8. **Önerilen doz:** Ör. `ADX-A: 1.2% · ADX-B: 0.3%`
9. **Teknik danışman:** Sizin kullanıcınız
10. **Öneri raporu:** PDF yükle
11. **Durum:** REQUESTED → IN_STUDY → DELIVERED → IMPLEMENTED

---

## 7. Applicator Training (Uygulayıcı Eğitimi)

### 7.1 Eğitim Kaydı

Sika/Chryso modeli — müşterinin saha ekibine ürün kullanımı eğitimi.

**Yol:** Admin → `/admin/sales/applicatortraining/add/`

1. **Training No:** Ör. `ATR-2026-001`
2. **Müşteri**
3. **Eğitim tarihi**
4. **Yer:** Ör. `Chantier Cimenterie Blida`
5. **Konu başlıkları:** Örn. "Dozaj kalibrasyonu, slump yönetimi, güvenlik prosedürleri"
6. **İşlenen ürünler**
7. **Katılımcı sayısı**
8. **Katılımcı listesi:** Her satır bir kişi (`Ad Soyad · Görev`)
9. **Eğitmen**
10. **Süre (saat):** Ör. `6.5`
11. **Katılım belgesi verildi:** True/False
12. **Toplu katılım belgesi PDF**
13. **Geri bildirim puanı (1-5)**

---

## 8. Performance Warranty (Garanti Belgesi)

### 8.1 Garanti Belgesi Nedir?

Ürün+müşteri+proje bazlı yazılı garanti. Sika: 60+ ülkede sistem garantisi (10-25 yıl).

### 8.2 Yeni Garanti

**Yol:** Admin → `/admin/sales/performancewarranty/add/`

1. **Warranty No:** Ör. `WAR-2026-001`
2. **Müşteri**
3. **Ürün**
4. **Proje adı:** Ör. `Otoyol köprüsü Sétif`
5. **Proje konumu**
6. **Teslim edilen miktar:** Ör. `15000 kg`
7. **Garanti başlangıcı** ve **Garanti sonu** (ör. 25 yıl sonra)
8. **Kapsam özeti:** 25 yıl dayanıklılık, dozaj koşulları
9. **Hariç durumlar:** Yanlış uygulama, uygun olmayan koşullar
10. **İmza sahibi**
11. **İmza zamanı**
12. **Garanti belgesi PDF**
13. **Durum:** ACTIVE / EXPIRED / CLAIMED / VOIDED

---

## 9. Customer Site Test (Saha Kabul Testi)

### 9.1 Saha Kabul Testi

Müşteri sahasında yapılan 7/14/28 gün küp mukavemet, slump, sıcaklık ölçümleri. Şikayet analizi + kalite trendleri için kritik veri.

### 9.2 Yeni Site Test

**Yol:** Admin → `/admin/quality/customersitetest/add/`

1. **Test No:** Ör. `CST-2026-001`
2. **Bağlı Fatura Satırı** (opsiyonel — satın alınan ürünle bağla)
3. **Batch** (mamul partisi)
4. **Proje adı**
5. **Saha konumu**
6. **Test tarihi**
7. **Test tipi:**
   - SLUMP (Slump testi)
   - CUBE_7 (Küp mukavemet 7 gün)
   - CUBE_14 (14 gün)
   - CUBE_28 (28 gün)
   - TEMPERATURE
   - AIR_CONTENT (Hava içeriği)
   - DURABILITY (Dayanıklılık)
   - OTHER
8. **Ölçülen değer**
9. **Birim** (MPa, mm, °C)
10. **Hedef değer**
11. **Verdict:** PASS / FAIL / MARGINAL / NA
12. **Testi yapan** (müşteri/lab)
13. **Lab raporu PDF**

---

## 10. BL-Fatura Eşleştirme Raporu

### 10.1 Rapor Görüntüleme

**Yol:** Sol menü → **Raporlar** → **BL-Fatura Eşleştirme**

Doğrudan URL: `/portal/rapor/bl-fatura/`

**4 KPI Kartı:**
- Eşleşen BL (fatura kesildi)
- Bekleyen BL (fatura kesilmemiş)
- Bekleyen tutar (fatura edilecek)
- İptal edilen BL

**Faturalandırılmamış BL'ler tablosu (sarı uyarı):**
- BL no, müşteri, sevk tarihi, tutar (HT), statü
- **Kritik:** Bu BL'ler hızlı fatura kesilmeli (nakit akışı için)

**Eşleşen BL'ler tablosu (son 50):**
- BL no, müşteri, sevk tarihi, fatura link, fatura tarihi

### 10.2 Nakit Akışı Optimizasyonu

Bu rapor haftalık takip edilir:
- Bekleyen tutar > belli eşik → fatura kesimi hızlandırılır
- Uzun süre bekleyen BL'ler → müşteri ile iletişime geçilir
- CANCELLED yükleyen BL'ler için sebep sorgulanır

---

## 11. Sık Sorulan Sorular

**S: Yeni müşteri kaydettim ama fatura kesince iskonto gelmiyor?**
C: Müşteri kaydında `default_discount_pct` alanı boş. Admin → Customer → alanı doldurup kaydedin (list_editable ile toplu düzenleyebilirsiniz).

**S: BL Client kesildi ama admin arayüzü kullanmam gerekiyor, portal formu yok mu?**
C: Şu an portal'dan BL oluşturma formu yok — admin arayüzü kullanılır. Portal'da sadece listeleme + detay + fatura oluşturma var.

**S: Aynı IBC'yi iki farklı BL'ye ekleyebilir miyim?**
C: Hayır. `OutputContainer` OneToOne — bir kez sevk edildikten sonra `shipment_reference` dolar, tekrar kullanılamaz.

**S: Farklı müşterilerin BL'lerini tek faturada birleştirebilir miyim?**
C: Hayır. Sistem `Aynı müşteri` kısıtını `create_invoice_from_bl()` içinde uygular.

**S: Trial batch başarısız oldu, ne yapmalıyım?**
C: Status'ü FAILED yapın + notlarda sebebi yazın. Sonra Mix Design Consultation açıp reçete revizyonu talep edebilirsiniz.

**S: Applicator training katılımcı listesini nasıl gireceğim?**
C: `participant_list` alanı serbest metin — her satır bir kişi. Ör:
```
A. Belaidi · Foreman
M. Boudjelal · Operator
K. Djellal · QC
```

**S: Performance warranty PDF şablonu var mı?**
C: PDF üretimi henüz yok — mevcut şablonu Word/PDF olarak elle hazırlayıp sisteme yüklersiniz. Yakında otomatik PDF gelecek.

**S: Customer Site Test 28 gün küp mukavemetini nasıl kaydederim?**
C: Test tipi `CUBE_28`, ölçülen değer MPa cinsinden, birim `MPa`, hedef değer (ör. 40 MPa), verdict otomatik (measured ≥ target → PASS).

---

## 12. Uygulama Egzersizi

1. **Yeni müşteri:** İskonto oranı %12, aktif
2. **Trial batch:** 25 kg numune, CEM I 42.5 R çimento, slump S4 hedef
3. **BL Client:** Yukarıdaki müşteriye yeni BL (2 IBC), teslim et durumu
4. **Fatura kes:** BL'den fatura oluştur, iskonto otomatik gelmeli
5. **Site test:** 28 gün küp mukavemet 42.5 MPa, PASS

Her egzersizi bitirdiğinizde satış müdürüne gösterin.
