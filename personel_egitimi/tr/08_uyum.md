# 08 — Yasal Uyum Modülü

**Kime yönelik:** Yasal uyum sorumlusu, QA müdürü, ihracat sorumlusu
**Süre:** 90 dakika
**Ön koşul:** `01_giris.md` ve `04_kalite.md` okundu

Bu belge Yasal Uyum modülünün tüm kısımlarını içerir:
1. SDS (Safety Data Sheet — Güvenlik Bilgi Formu)
2. DoP (Declaration of Performance) + CE Marking
3. Notified Body ve FPC Audit
4. CoC (Certificate of Conformity)
5. REACH SVHC İzleme
6. EN 480 Test Metotları
7. Retention Numunesi
8. Storage/Depolama Uyumluluğu
9. Cezayir Özel Uyum (SCF, TVA G50, DGI)

---

## 1. SDS (Safety Data Sheet — Güvenlik Bilgi Formu)

### 1.1 SDS Nedir?

SDS, kimyasal ürünün güvenli kullanımı için 16 bölümlük yasal belge:
- **EU Reg 2020/878** (yeni SDS formatı)
- **REACH Reg 1907/2006**
- **GHS/CLP** etiketleme sistemi

Cezayir'de: Fransız CLP standartlarına uyumlu SDS gereklidir.

### 1.2 SDS Listesi

**Yol:** Sol menü → **Yasal Uyum** → **SDS (16 Bölüm)**

Doğrudan URL: `/portal/uyum/sds/`

**KPI Kartları:**
- Toplam SDS
- Taslak
- Onaylı

**Tablo:**
- SDS No
- Profile (kimyasal profil)
- v (versiyon)
- Dil (`tr`, `fr`, `en`, `ar`)
- Revizyon tarihi
- **Durum badge:**
  - 🟢 Onaylı
  - 🟠 Taslak
  - ⚫ Superseded / Withdrawn
- **📄 PDF butonu**

### 1.3 Yeni SDS Oluşturma

**Yol:** Admin → `/admin/chemicals/safetydatasheet/add/`

1. **SDS No:** Ör. `SDS-ADX-100-v3-fr`
2. **Chemical Profile:** Dropdown'dan ürünün profilini seç
3. **Versiyon:** `1.0`, `2.0`, ...
4. **Dil:** `fr` (Fransızca — Cezayir varsayılan)
5. **Tarihler:** Issue date, Revision date, Next review date
6. **16 Bölüm** (her biri TextField):
   - 1. Identification (Kimlik)
   - 2. Hazards identification (Tehlike tanımlaması)
   - 3. Composition / ingredients (Bileşim)
   - 4. First-aid measures (İlk yardım)
   - 5. Fire-fighting (Yangınla mücadele)
   - 6. Accidental release (Kaza sonucu yayılma)
   - 7. Handling and storage (Elleçleme)
   - 8. Exposure controls / PPE (Maruziyet kontrolü)
   - 9. Physical/chemical properties (Fiziksel özellikler)
   - 10. Stability and reactivity (Kararlılık)
   - 11. Toxicological (Toksikolojik)
   - 12. Ecological (Ekolojik)
   - 13. Disposal (Bertaraf)
   - 14. Transport (Taşıma — ADR/RID/IMDG)
   - 15. Regulatory (Mevzuat — REACH, CLP)
   - 16. Other information (Diğer)
7. **Hazırlayan** ve **Onaylayan (QA)**
8. **Ek dosya (PDF)** — üretilmiş PDF eklenebilir
9. **Durum:** DRAFT → APPROVED → SUPERSEDED → WITHDRAWN

### 1.4 SDS PDF Otomatik Üretme

Her SDS için sistem otomatik 16 bölüm PDF üretir.

**Yol:** SDS listesi → satırdaki **📄 PDF** butonuna tıkla

- PDF yeni sekmede açılır
- Format: A4, siyah-beyaz, ISO standardında
- İçerik: Tüm 16 bölüm + hazırlayan + onaylayan + Regulation EC 2020/878 referansı
- İndirilebilir veya yazdırılabilir

Bu PDF müşterilere gönderilir (her ürün sevkiyatında ekli olmalı).

### 1.5 SDS Versiyonlama

Formül değişince veya yasal gereklilik güncellenince:
- **Eski SDS:** durumu `SUPERSEDED` yapılır
- **Yeni SDS:** yeni versiyon numarasıyla oluşturulur (`v2`, `v3`)
- Aynı profil+versiyon+dil kombinasyonu tekli (unique_together)

**Öneri:** Her yıl gözden geçirin. `next_review_date` alanını doldurun.

---

## 2. DoP (Declaration of Performance)

### 2.1 DoP Nedir?

**Declaration of Performance** — Regulation EU 305/2011 Annex III uyumlu, CE marking için zorunlu belge.

**CoC (Certificate of Conformity) ile fark:**
- **CoC:** Notified Body tarafından verilir (denetimden sonra)
- **DoP:** Üretici tarafından **beyan edilir** (kendi imzasıyla)

Cezayir üretici EU'ya ihracat yapıyorsa DoP zorunludur.

### 2.2 DoP Listesi

**Yol:** Sol menü → **Yasal Uyum** → **DoP / CE Marking**

Doğrudan URL: `/portal/uyum/dop/`

**Tablo:**
- DoP No
- Ürün
- Kullanım amacı
- v (versiyon)
- Yayım tarihi
- NB (Notified Body numarası)
- Durum badge (Yayımlandı/Taslak)
- **📄 CE PDF butonu**

### 2.3 Yeni DoP Oluşturma

**Yol:** Admin → `/admin/chemicals/declarationofperformance/add/`

1. **DoP No:** Ör. `DOP-2026-001`
2. **Ürün:** Dropdown'dan seç
3. **CoC (Bağlı CoC):** Notified Body tarafından verilen sertifika
4. **Versiyon:** `1.0`
5. **Yayım tarihi**
6. **Kullanım amacı (Intended use):** Ör. `Superplasticizer / High Range Water Reducer`
7. **Performance data (JSON):** EN 934-2 tablo değerleri
   ```json
   {
     "chloride_ion_content": "<=0.1%",
     "alkali_content": "<=1.5%",
     "water_reduction": ">=12%",
     "compressive_strength_ratio_7d": ">=125%",
     "compressive_strength_ratio_28d": ">=115%"
   }
   ```
8. **İmza sahibi:** Ör. `A. Bouzidi, Directeur Général`
9. **Durum:** DRAFT → ISSUED → SUPERSEDED → WITHDRAWN

### 2.4 DoP PDF Üretme

**Yol:** DoP listesi → satırdaki **📄 CE PDF** butonuna tıkla

PDF içeriği (Annex III uyumlu):
- Başlık: **DECLARATION OF PERFORMANCE**
- DoP numarası
- 10 bölüm:
  1. Unique product-type ID
  2. Type/batch/serial
  3. Intended use
  4. Manufacturer (SARL MAPA Algérie + adres)
  5. Authorised representative
  6. AVCP System (System 2+)
  7. Harmonised standard (EN 934-2:2009+A1:2012)
  8. Notified body (NB number + name)
  9. **Declared performance table** (performance_data JSON)
  10. Signature bloğu

Bu PDF ürün ambalajında ve müşteri belgelerinde referans verilir.

---

## 3. Notified Body ve FPC Audit

### 3.1 Notified Body Nedir?

CE marking için ürünün fabrika kalite kontrolünü denetleyen bağımsız kuruluş. Cezayir tarafından tanınan Avrupa NB'leri:
- **NB 1234 — CTC Groupe** (Fransa)
- **NB 0987 — CSTB** (Fransa)
- **NB 0432 — CATAS** (İtalya)

Her NB kendi denetim programını uygular.

### 3.2 NB Listesi

**Yol:** Admin → `/admin/chemicals/notifiedbody/`

Her NB:
- Number (4 haneli — ör. `1234`)
- Ad (ör. `CTC Groupe`)
- Ülke

### 3.3 FPC Audit (Factory Production Control) Kayıtları

FPC audit, Notified Body'nin fabrikada yaptığı fabrika üretim kontrolü denetimi. EN 934-2 System 2+ kapsamında yıllık/periyodik.

### 3.4 FPC Audit Listesi

**Yol:** Sol menü → **Yasal Uyum** → **FPC Audit (NB)**

Doğrudan URL: `/portal/uyum/fpc-audit/`

**Tablo:**
- Audit No
- NB
- Tip (INITIAL/SURVEILLANCE/SPECIAL/RENEWAL)
- Tarih
- Major NC (kırmızı — kritik uygunsuzluk)
- Minor NC (sarı — küçük uygunsuzluk)
- Observations (bilgi amaçlı)
- **Sonuç badge:**
  - 🟢 ✓ Uygun (PASSED)
  - 🔵 ✓ Bulgu (PASSED_FINDINGS)
  - 🟠 Şartlı (CONDITIONAL)
  - 🔴 ✗ Uygun değil (FAILED)
- Cert (sertifika düzenlendi mi ✓/—)

### 3.5 Yeni FPC Audit Kaydı

**Yol:** Admin → `/admin/chemicals/fpcaudit/add/`

1. **Audit No:** Ör. `FPC-2026-001`
2. **Notified Body**
3. **Audit type:** INITIAL / SURVEILLANCE / SPECIAL / RENEWAL
4. **Audit tarihi**
5. **Denetçi adı:** Ör. `Jean Dupont`
6. **Kapsam:** Denetlenen ürünler, hatlar, prosesler
7. **Bulgular:** Major/minor NC + observation'lar
8. **NC sayıları:** Major, Minor, Observations
9. **Sonuç (outcome):** PENDING/PASSED/PASSED_FINDINGS/CONDITIONAL/FAILED
10. **Corrective action deadline** (Major NC varsa zorunlu)
11. **Corrective actions:** Aksiyon planı
12. **Denetim raporu PDF**
13. **Sertifika düzenlendi (True/False)**
14. **Sonraki denetim tarihi**

### 3.6 Denetime Hazırlık

FPC audit öncesi kontrol listesi:
- ✅ Aktif QCSpec'ler QA onaylı mı
- ✅ Örnekleme planları güncel mi (BR-QA-12)
- ✅ NCR'ların hepsi kapatılmış mı
- ✅ CAPA'lar effectiveness check yapılmış mı
- ✅ Retention numuneleri saklıda mı
- ✅ SDS + DoP güncel mi
- ✅ Kalibrasyon kayıtları tamamlanmış mı (CMMS'ten)

---

## 4. CoC (Certificate of Conformity)

### 4.1 CoC ile DoP Farkı

- **CoC:** Notified Body'nin verdiği "üretim kalite güvencesi" belgesi
- **DoP:** Üreticinin kendi imzasıyla beyan ettiği "performans" belgesi

Bir ürünün CE marking'i için önce CoC alınır, sonra DoP hazırlanır (CoC referansıyla).

### 4.2 CoC Kaydı

**Yol:** Admin → `/admin/chemicals/certificateofconformity/`

1. **CoC No**
2. **Ürün**
3. **FPC Test Plan** bağlantısı
4. **Standart:** `EN 934-2:2009+A1:2012`
5. **Admixture type:** Superplasticizer / HRWR / vs.
6. **CE marking yılı**
7. **DoP No** (bağlantı)
8. **Yayım tarihi + Geçerlilik sonu**
9. **Düzenleyen kuruluş (NB)**
10. **Durum:** DRAFT/ISSUED/SUSPENDED/REVOKED
11. **PDF dosya**

---

## 5. REACH SVHC İzleme

### 5.1 SVHC Nedir?

**Substance of Very High Concern** — REACH kapsamında yüksek endişe verici madde. Örnekler:
- Kanserojen (Carcinogenic)
- Mutajen
- Toksik üreme (Reproductive toxic)
- Dayanıklı (Persistent)
- Biyoakümülatif

Bir hammaddede SVHC oranı **>%0.1** ise ürüne aktarılır → downstream user notification zorunlu.

### 5.2 SVHC İzleme Sayfası

**Yol:** Sol menü → **Yasal Uyum** → **REACH SVHC**

Doğrudan URL: `/portal/uyum/reach-svhc/`

**Tablo (sadece SVHC işaretli hammaddeler):**
- Kod, Ad
- **CAS numarası** (ör. `9003-01-4`)
- **EC numarası** (ör. `618-347-7`)
- **REACH Reg No** (ör. `01-2119471299-27-0001`)
- **SVHC %** (ölçüm oranı)
- **Eşik durumu:**
  - 🔴 **⚠ Bildirim gerekli** (SVHC > %0.1)
  - 🟢 ✓ (SVHC ≤ %0.1)

**Uyarı paneli:** Eğer bir hammadde %0.1 üzerindeyse üstte kırmızı bilgilendirme:
`⚠ N hammadde %0.1 SVHC eşiğinin üzerinde — downstream user notification hazırlanmalı.`

### 5.3 SVHC Bilgisi Girme

**Yol:** Admin → RawMaterial detayı

Alanlar:
- **SVHC işareti (svhc_flag):** True
- **SVHC oranı (svhc_pct):** Ör. `0.150` (%)
- **REACH Registration No:** ECHA formatı
- **CAS numarası**
- **EC numarası**

Bilgiler tedarikçinin SDS'inden alınır.

### 5.4 Downstream User Notification

**REACH Article 33** gereği, %0.1 üzeri SVHC içeren ürünün müşterisine bilgi verilir:
- Ürün kodu
- SVHC madde adı + CAS
- Konsantrasyon
- Güvenli kullanım bilgisi

Bu belge şu an manuel hazırlanır (yakında ADMIX-ERP'de otomatik üretim gelecek).

---

## 6. EN 480 Test Metotları

### 6.1 EN 480 Nedir?

**EN 480 serisi** — çimento katkı testlerinin standartları:
- EN 480-1: Numune hazırlama
- EN 480-8: Katı madde %
- EN 480-10: Klorür iyonu
- EN 480-11: Hava içeriği
- EN ISO 758: Yoğunluk

### 6.2 QC Parametreye EN 480 Metot Referansı

**Yol:** Admin → QCParameter → **en480_method_ref** alanı

Örnek:
- `CHLORIDE` parametresi → `EN 480-10 § 5.2`
- `SOLIDS` parametresi → `EN 480-8 § 4.3`
- `DENSITY` parametresi → `EN ISO 758`

Bu bilgi COA + FPC audit + müşteri şartname sorularında kullanılır.

---

## 7. Retention Numunesi

Detayı `05_stok.md` § 8'de anlatıldı.

**Yasal uyum tarafı:**
- Her batch için retention numunesi **saklamak zorunludur** (EN 934-2 gereği)
- Raf ömrü + 6 ay saklama süresi
- Şikayet/audit sırasında yeniden analiz kaynağı

---

## 8. Depolama Uyumluluğu (Storage Compatibility)

### 8.1 Depo Bölgeleri

`05_stok.md` § 7'de kısa değinildi. Yasal uyum tarafı:

- **StorageZone** modeli — her zone için:
  - İzin verilen tehlike sınıfları
  - Max kapasite (kg)
  - Sıcaklık min/max
  - Havalandırma tipi

- **StorageIncompatibility** — hangi iki sınıf birlikte depolanamaz:
  - Ör. Klas 3 (yanıcı) + Klas 5.1 (oksidan) → patlama riski
  - Sistem denetim/uyum kontrolünde uyarı üretir

### 8.2 Depolama Denetimi

FPC/ISO audit sırasında NB denetçileri depoyu inceler. Ön hazırlık:
- Tüm hammaddelerin doğru zone'a yerleştiğini kontrol et
- Sıcaklık logları hazır
- Ventilation testi güncel
- MSDS (SDS) her hammadde yakınında görünür

---

## 9. Cezayir Özel Uyum

### 9.1 SCF (Système Comptable Financier) — PCN 2010

Cezayir hesap planı. ADMIX-ERP tam entegre:
- 1-9 hesap sınıfları
- Journal codes (JV, JA, JB, JC, JVE, JAE)
- Muhasebe yazma kuralları

Detay: `02_muhasebe.md` § 6.

### 9.2 TVA G50 Deklarasyonu

Aylık TVA + IBS avans + diğer vergiler tek beyanname:
- Ayın 20'sine kadar DGI'ye teslim
- ADMIX-ERP'de `TVADeclaration` modeli hazır
- Portal'dan otomatik hesaplama gelecek sürümde

### 9.3 DGI E-Fatura

Cezayir e-fatura mandatı 2027'ye ertelendi. ADMIX-ERP hazır:
- Fatura eki (attachment) alanı
- E-fatura JSON hazırlığı (yasa çıkınca aktif olur)

### 9.4 Sonelgaz ve Diğer

- Elektrik faturaları: Sonelgaz belgesi
- Su: SEAAL
- Doğalgaz: Sonelgaz

Bu faturalar `08_uyum` bakımından **gider faturası** olarak muhasebeye kaydedilir (`02_muhasebe.md` § 4).

---

## 10. Sık Sorulan Sorular

**S: SDS yıllık gözden geçirme zorunlu mu?**
C: EU 2020/878 § 4.1 → hayır zorunlu değil, ancak öneri. Şirketiniz kalite prosedürünüzde 6 aylık veya yıllık gözden geçirme yapmalı.

**S: DoP olmadan CE marking yapabilir miyim?**
C: HAYIR. EU 305/2011 CPR gereği DoP zorunlu. NB sertifikası (CoC) alsanız bile üretici DoP imzalamak zorunda.

**S: FPC Audit'te Major NC alırsak sertifika iptal olur mu?**
C: Bağlıdır — NB politikasına göre. Genelde `CONDITIONAL` durumu verilir, corrective action deadline verilir (60-90 gün). Deadline'da düzeltilmezse sertifika askıya alınır.

**S: REACH SVHC oranını nasıl belirlerim?**
C: Tedarikçi SDS'inden bakın. Şüpheliyseniz akredite lab'a test ettirin.

**S: EN 480 metot referansı zorunlu mu?**
C: FPC/ISO audit sırasında sorulacak — spec'lerde metot referansı olması güçlü kanıt. Boş bırakmayın.

**S: Retention numunesini 5 yıl sakladım, imha edebilir miyim?**
C: Raf ömrü + 6 ay bir minimum. Şirket politikanız daha uzun süre saklamayı gerektirebilir (ör. müşteri sözleşmeleri için 10 yıl). Kalite müdürüne danışın.

**S: Bir SDS versiyonunu geri çekmek istiyorum?**
C: Durum `WITHDRAWN` yapılır. Ancak müşterilerin ellerinde eski kopyalar olabilir — resmi bildirim gerektirebilir (müşteri kayıtları üzerinden).

**S: SDS Türkçe olarak da hazırlamalı mıyım?**
C: Bağlıdır — Cezayir müşterileri Fransızca yeterli. Ancak Türkiye ihracatı yapıyorsanız Türkçe SDS zorunlu.

---

## 11. Uygulama Egzersizi

1. **Yeni SDS:** `ADX-100` için Fransızca SDS v1, tüm 16 bölüm dolu, PDF üret
2. **DoP:** Aynı ürün için DoP oluştur (performance_data JSON tam)
3. **FPC Audit:** Yeni denetim kaydı — SURVEILLANCE tipi, PASSED_FINDINGS sonuç
4. **REACH SVHC:** Bir hammadde için SVHC bilgisi gir (>0.1% örnek)
5. **SDS PDF karşılaştırma:** İki versiyonun PDF'lerini yan yana karşılaştır

Her egzersizi bitirdiğinizde yasal uyum sorumlusuna gösterin.
