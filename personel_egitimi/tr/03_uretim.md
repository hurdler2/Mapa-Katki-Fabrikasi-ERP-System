# 03 — Üretim Modülü

**Kime yönelik:** Üretim sorumluları, vardiya süpervizörleri, üretim müdürü
**Süre:** 90 dakika
**Ön koşul:** `01_giris.md` okundu

Bu belge Üretim modülünün tüm kısımlarını içerir:
1. Reçete Yönetimi
2. Üretim Emri Açma
3. Batch Başlatma ve Takibi
4. Malzeme Tüketimi (Dozajlama)
5. Bitmiş Ürün Kaydı (IBC/Konteynır)
6. §22 Bilan Massique ve COMPLÉMENT
7. Facteur d'Échelle (Ölçek Faktörü)
8. Üretim Kampanyası (Campaign)
9. İzlenebilirlik (Forward/Backward Trace)

---

## 1. Reçete Yönetimi

### 1.1 Reçete Nedir?

Bir reçete, bir mamul (ör. `ADX-100` Superplasticizer) için hammaddelerin miktarını ve karışım kurallarını tanımlar. Her reçete **versiyonlanır** — aynı ürün için birden fazla versiyon olabilir, ama **sadece bir tanesi aktif** olabilir.

### 1.2 Yeni Reçete Oluşturma (Nouvelle Formulation)

**Yol:** Sol menü → **Üretim** → **Reçeteler** → **Yeni Formulation**

Doğrudan URL: `/portal/recete/yeni/`

1. **Ürün (Produit fini):** Hangi mamul için (dropdown)
2. **Référence parti (base):** Ör. `1000` kg — bir batch için baz miktar
3. **Unité:** `kg` (varsayılan)
4. **Bu reçeteyi aktif yap:** İşaretli bırakırsanız, aynı ürün için varsa mevcut aktif reçete otomatik pasifleşir
5. **Composition — Matières Premières** tablosu:

| # | Matière Première | Qté / Lot | Tolérance % | Complément §22 |
|---|-----------------|-----------|-------------|----------------|
| 1 | W (Su) | 600.0000 | 0.50 | ✅ |
| 2 | M1 (Monomer A) | 250.0000 | 0.50 | ⬜ |
| 3 | M2 (Monomer B) | 80.0000 | 0.50 | ⬜ |
| 4 | IN (İnisiyatör) | 15.0000 | 1.00 | ⬜ |
| 5 | NaOH | 47.0000 | 1.00 | ⬜ |

**Önemli notlar:**
- **Complément §22** işaretli satır otomatik su tamamlama (bilan massique) yapar
- Genelde su (W) complément olarak işaretlenir
- Aynı reçetede sadece **bir** complément satırı olabilir
- Toleranslar Cezayir üretimi için genellikle %0.5 (kritik) veya %1.0 (esnek)

6. **Notlar:** Reçete geliştirme geçmişi, referans
7. **Reçeteyi Kaydet** butonuna basın

### 1.3 Aktif Reçeteyi Değiştirme

Bir ürün için birden fazla reçete versiyonu varsa:
- **Reçeteler listesi** sayfasına git
- Kullanılmak istediğiniz reçetenin detayına gir
- **Bu reçeteyi aktif yap** checkbox'ını işaretle + kaydet
- Sistem otomatik olarak diğer reçetenin `is_active` alanını `False` yapar

### 1.4 Reçete Görüntüleme ve Düzenleme

- Reçeteler listesine git
- İstediğiniz reçetenin satırına tıkla
- Detay sayfasında:
  - Ürün + versiyon
  - Base batch size + unit
  - Aktif mi
  - Satırlar tablosu
  - Notlar

**Uyarı:** Aktif olan bir reçeteyi değiştirmek RISKLI — üretimde kullanılıyor olabilir. Değişiklik gerekirse yeni bir versiyon oluşturmak daha güvenli.

---

## 2. Üretim Emri Açma (Ordre de Production)

Reçete tanımlandıktan sonra, gerçek üretim başlatmak için bir **üretim emri** oluşturulur.

### 2.1 Yeni Üretim Emri

**Yol:** Admin arayüzü → `/admin/production/productionorder/add/`

1. **Emir No:** Ör. `PORD-202608-005`
2. **Ürün:** Aynı ürünün aktif reçetesi otomatik seçilir
3. **Reçete:** Aktif reçete (değiştirilebilir)
4. **Hedef miktar:** Ör. `2000` kg (2 batch × 1000 kg baz)
5. **Birim:** `kg`
6. **Planlanan tarih:** Üretim ne zaman yapılacak
7. **Reaktör:** Hangi reaktörde üretilecek (R-01, R-02, ...)
8. **Durum:** `PLANNED` (varsayılan)
9. **Notlar:** Serbest metin

### 2.2 Üretim Emri Detay Sayfası

**Yol:** Sol menü → **Üretim Panosu** → emir listesinden bir emre tıkla

Bu sayfa **çok önemli** — burada:

- **Facteur d'échelle** girip önizleme alırsınız
- **Besoins théoriques MP** tablosunu görürsünüz (her hammadde için ihtiyaç vs stok)
- **§22 Bilan massique** özetini görürsünüz
- Stok yeterliyse **Parti Başlat** butonu aktif olur

---

## 3. Facteur d'Échelle (Ölçek Faktörü)

Reçete `1000 kg` batch için tanımlıdır; ancak `2000 kg` üretmek istiyorsanız faktör `2.0` olur.

### 3.1 Ölçek Değiştirme

Üretim emri detayında:
1. **Ölçek faktörü** kutusuna `2.0` yazın
2. **Yeniden hesapla** butonuna basın
3. Ekran otomatik güncellenir:
   - Hedef miktar: `2000 kg`
   - Su (complément): otomatik `1200 kg` hesaplanır
   - Diğer hammaddeler: `500 kg`, `160 kg` (2× reçete)

### 3.2 §22 Bilan Massique — Nasıl Çalışır?

Reçete: Su (complément) = 600, Diğer = 400 → Toplam 1000 kg
Ölçek 2.0 → Hedef 2000 kg
- Sabit satırlar × 2 = 800 kg
- **Su (complément) otomatik = 2000 − 800 = 1200 kg**

Bu Cezayir üretim standardı (§22 Bilan massique planifié) — sıcak iklim için çok kritik.

### 3.3 Besoins Théoriques MP Tablosu

Ölçek girildikten sonra tablo şöyle görünür:

| Hammadde | İhtiyaç | Stok (dispo) | Fark | Durum |
|----------|---------|--------------|------|-------|
| W · Su | 1.200,0000 | 7.919,3000 | +6.719 | ✓ |
| G · Sodyum glukonat | 30,0000 | 5.279,5000 | +5.249 | ✓ |
| SP · Superplastik. PCE | 700,0000 | 4.198,0000 | +3.498 | ✓ |
| HD · Katkı bileşeni | 70,0000 | 3.435,4000 | +3.365 | ✓ |

- **Tüm hammaddeler yeterli** yeşil badge → **Parti Başlat** butonu aktif
- Herhangi bir hammadde eksikse → kırmızı **Stok insuffisant** uyarısı
- Üretim başlatılamaz — hammadde takviye edin veya batch küçültün

---

## 4. Batch Başlatma

### 4.1 Yeni Batch Başlat

**Yol:** Sol menü → **Yeni Parti Başlat**

Alternatif: Üretim emri detayından **Parti Başlat** butonu

1. **Emir Seç:** Aktif üretim emirlerinden birini seçin
2. **Batch No:** Otomatik öneri: `BATCH-20260915-042`
3. **Kaydet**

Sistem arka planda:
- ProductionBatch kaydı oluşturur
- Reçetedeki her hammadde için `MaterialConsumption` kaydı hazırlar (henüz `actual_weight` boş)
- Batch durumu **PLANNED** olur

### 4.2 Batch Durumu Akışı

```
PLANNED → IN_PROGRESS → COMPLETED → QC_HOLD → RELEASED
                                              ↘ REJECTED
```

- **PLANNED:** Batch hazırlandı, üretim başlamadı
- **IN_PROGRESS:** Dozajlama başladı (SCADA'dan otomatik)
- **COMPLETED:** Tüm hammaddeler dozajlandı, karışım tamamlandı
- **QC_HOLD:** Kalite kontrol bekliyor
- **RELEASED:** QA onayladı, satılabilir
- **REJECTED:** QA reddetti, imha veya rework

---

## 5. Malzeme Tüketimi (Dozajlama)

### 5.1 Manuel Kayıt (SCADA yoksa)

**Yol:** Admin → `/admin/production/materialconsumption/`

1. İlgili batch'i seçin
2. Her hammadde satırı için:
   - **Actual weight** girin (gerçek tartılan miktar)
   - **Lot** seçin (hangi hammadde lotundan alındı — FEFO önerisi otomatik)
   - **Kaynak:** `MANUAL`

**Toleransı aşan sapma** varsa sistem otomatik olarak batch'i `QC_HOLD` durumuna çeker.

### 5.2 SCADA'dan Otomatik Kayıt

Eğer SCADA sistemi bağlıysa:
- Batch tamamlandığında Node-RED otomatik POST atar
- ADMIX-ERP'de `ProductionBatch` + `MaterialConsumption` + `QCTestResult` kayıtları otomatik oluşur
- Kaynak alanı `SCADA` olur

**Portal'dan izleme:** Sol menü → **SCADA** → SCADA batch akışını görürsünüz.

---

## 6. Bitmiş Ürün Kaydı (Output Container / IBC)

Batch tamamlandıktan sonra üretilen ürünün hangi IBC/tanka doldurulduğunu kaydedersiniz.

### 6.1 Yeni Çıkış Kabı

**Yol:** Admin → `/admin/production/outputcontainer/add/`

1. **Batch:** Tamamlanan batch'i seç
2. **Container (IBC):** Hangi kap doldurulduğu (kap kodu ör. `IBC-OUT-01`)
3. **Miktar:** Ör. `500` kg
4. **Dolum zamanı**
5. **Sevkiyat referansı** (opsiyonel — sevk edildiğinde eklenir)

Bir batch'ten birden fazla IBC doldurulabilir. Ör. 2000 kg batch → 4× 500 kg IBC.

---

## 7. Üretim Kampanyası (Production Campaign)

Aynı ürünü art arda çok kez üretmek için kampanya kullanılır (MES super batch).

### 7.1 Yeni Kampanya

**Yol:** Admin → `/admin/production/productioncampaign/add/`

1. **Campaign No:** Ör. `CMP-2026-Q4-001`
2. **Ürün + Reçete** + **Reaktör**
3. **Planlanan parti sayısı:** Ör. `10`
4. **Toplam hedef:** Ör. `10.000` kg
5. **Başlangıç + Bitiş** tarihleri

Kampanya süresince her batch tamamlandığında `completed_batch_count` otomatik artar. İlerleme yüzdesi hesaplanır (`progress_pct`).

---

## 8. İzlenebilirlik (Forward/Backward Trace)

**Backward trace:** Bir üretilmiş partinin hangi hammadde lotlarından yapıldığını görün.
**Forward trace:** Bir hammadde lotu hangi partileri etkiledi + hangi müşterilere gitti?

### 8.1 Backward Trace

**Yol:** Admin → ProductionBatch detayı → **Actions** → **Backward Trace**

Sonuç JSON:
```json
{
  "batch_number": "BATCH-20260915-042",
  "consumptions": [
    {"raw_material": "W", "lot_number": "LOT-W-202606-014", "supplier": "MC-Bauchemie"},
    {"raw_material": "M1", "lot_number": "LOT-M1-202607-023", "supplier": "BASF"}
  ]
}
```

### 8.2 Forward Trace

**Yol:** Admin → RawMaterialLot detayı → **Actions** → **Forward Trace**

Sonuç JSON:
```json
{
  "lot_number": "LOT-W-202606-014",
  "batches": ["BATCH-2026-041", "BATCH-2026-042", "BATCH-2026-043"],
  "shipments": ["BL-2026-100", "BL-2026-102"],
  "customers": ["C-2026-001 SARL Cimenterie Blida"]
}
```

**Kullanım:** Bir müşteri şikayet ettiğinde, sorunlu batch'i bulup — o batch'in hangi lotlardan yapıldığını — o lotların başka nerelere gittiğini görürsünüz.

---

## 9. Portal'da İzleme

### 9.1 Üretim Panosu

**Yol:** Sol menü → **Üretim Panosu**

Bu ekran gösterir:
- Aktif batch'ler (son 20)
- Planlanan üretim emirleri (yaklaşık 10)
- Reaktör kullanım durumu (hangi reaktör hangi batch'te çalışıyor)
- Son 30 gün üretim sayısı + released oranı
- Aktif reçete sayısı

### 9.2 Üretim Verimi Raporu (Rendements Production)

**Yol:** Sol menü → **Raporlar** → **Üretim Verimi**

- Son 90 gün + son 100 batch
- Ortalama verim yüzdesi
- Her batch için: hedef vs gerçek, delta, verim %
- Renk kodu: %98+ yeşil, %95-98 sarı, <%95 kırmızı

---

## 10. SCADA Entegrasyon Panosu

Eğer fabrikada SCADA kullanılıyorsa:

**Yol:** Sol menü → **SCADA**

- Köprü durumu (online/offline)
- Bugünkü + haftalık batch sayısı
- Son 24 saat aktivite grafiği
- Son 20 SCADA batch'i (batch no, reçete, verim %)
- Bridge kullanıcı + token durumu

Bu ekran, entegratör Node-RED'in düzgün çalışıp çalışmadığını gösterir.

---

## 11. Sık Sorulan Sorular

**S: Ölçek faktörünü değiştirdim ama besoins théoriques güncellenmiyor?**
C: **Yeniden hesapla** butonuna basın. Değişiklik ancak tıklama ile uygulanır.

**S: Complément satırı işaretlenmiş ama miktar 0 gösteriyor?**
C: Reçete satırında `quantity` alanı da doldurulmalı (küçük bir başlangıç değeri, ör. `600`). Complément bayrağı miktar hesabını override eder ama satır tanımlı olmalı.

**S: Batch başlatmaya çalıştım ama Parti Başlat butonu gri?**
C: Besoins théoriques tablosunda **kırmızı bir hammadde** vardır — stok yetersiz. Depoya bakın veya batch'i küçültün.

**S: Aynı ürün için iki aktif reçete oluşturdum, ne olur?**
C: Sistem bunu engelliyor — `Recipe.save()` transaction'ında eski aktif reçete otomatik `False` yapılır. Yalnızca son değiştirdiğiniz reçete aktif kalır.

**S: SCADA'dan batch geldi ama portalda görmüyorum?**
C: **SCADA panosuna** bakın. Eğer orada da yoksa Node-RED tarafında POST hatalı. Entegratöre başvurun.

**S: Tolerance aşıldı, batch QC_HOLD'a düştü. Ne yaparım?**
C: QA'ya bilgi verin. Onlar detaya bakıp `RELEASED` veya `REJECTED` yaparlar. Yeniden işleme (rework) alınabilir.

**S: Kampanyadaki bir batch iptal edilirse toplam sayı azalır mı?**
C: Hayır, `planned_batch_count` sabittir. `completed_batch_count` sadece tamamlanan sayısıyla artar. İptal edilen batch dahil edilmez.

---

## 12. Uygulama Egzersizi

1. **Yeni reçete:** 5 satır, biri complément (su), tolerans %0.5
2. **Üretim emri:** 3000 kg hedef, planlı tarih 3 gün sonra
3. **Ölçek testi:** Aynı emir için 1.5 ve 2.0 ölçek faktörü uygulayıp besoins théoriques karşılaştır
4. **Manuel batch:** Bir batch'e her hammaddeyi manuel dozajla + IBC'ye doldur
5. **Backward trace:** Bir tamamlanmış batch için hammadde lotlarını listele

Her egzersizi bitirdiğinizde üretim müdürüne gösterin.
