# 05 — Stok / Depo Modülü

**Kime yönelik:** Depo sorumluları, mal kabul memurları, depo müdürü
**Süre:** 75 dakika
**Ön koşul:** `01_giris.md` okundu

Bu belge Stok/Depo modülünün tüm kısımlarını içerir:
1. Hammadde ve Lot Yönetimi
2. Mal Kabul (Goods Receipt)
3. Stok Detay Sayfası (Alerte + Rupture)
4. Ajustement de Stock (Stok Düzeltmesi)
5. Multi-Line Ajustement (Toplu Düzeltme)
6. Stok Hareket Geçmişi
7. Raflar ve Depo Bölgeleri
8. Retention Numunesi
9. Raporlar

---

## 1. Hammadde ve Lot Yönetimi

### 1.1 Hammadde Kavramı

Bir **hammadde (RawMaterial)** üretim reçetelerinde kullanılan bir bileşendir. Örnekler:
- `W` — Su
- `M1` — Monomer A (PEG)
- `M2` — Monomer B (Akrilik asit)
- `IN` — İnisiyatör (Persülfat)
- `NaOH` — Baz

Her hammaddenin:
- **Kod** ve **Ad**
- **Tip** (Su, Priz geciktirici, Superplastikleştirici, Katkı bileşeni, Diğer)
- **Birim** (kg, L, ton)
- **Yoğunluk** (kg/L — sıvılar için)
- **Raf ömrü** (gün)
- **Seuil d'alerte** (uyarı eşiği)
- **Seuil de rupture** (kritik alt eşik)
- **REACH/SVHC bilgisi** (varsa)
- **CAS/EC numarası**

### 1.2 Lot Kavramı

Bir **lot (RawMaterialLot)** o hammaddeden gelen belirli bir partidir. Aynı hammaddenin farklı zamanlarda gelen farklı lotları olur.

Her lot için:
- **Lot No** (benzersiz — ör. `LOT-W-202606-014`)
- **Tedarikçi**
- **Kabul tarihi**
- **Son kullanma tarihi**
- **Kabul miktarı** ve **Kalan miktar**
- **QC Durumu:** PENDING / RELEASED / QUARANTINE / REJECTED
- **COA referansı** (tedarikçi COA numarası)
- **Birim maliyet** (DZD/kg)
- **Container/Konteynır** (hangi tank/depoda)

### 1.3 Lot Listesi Görüntüleme

**Yol:** Sol menü → **Stok / Depo** → **Hammadde Lotları**

Alternatif admin: `/admin/inventory/rawmateriallot/`

Filtreler:
- QC durumu (PENDING/RELEASED/QUARANTINE/REJECTED)
- Hammadde
- Tedarikçi
- Kabul tarihi (date_hierarchy)

Renkli QC durumu badge:
- 🟢 RELEASED — kullanılabilir
- ⚫ PENDING — test bekliyor
- 🟠 QUARANTINE — karantinada
- 🔴 REJECTED — reddedilmiş

---

## 2. Mal Kabul (Goods Receipt)

### 2.1 Yeni Mal Kabul

**Yol:** Sol menü → **Stok / Depo** → **Yeni Mal Kabul**

Doğrudan URL: `/portal/stok/mal-kabul/`

1. **Tedarikçi:** Dropdown'dan seç
2. **Satın Alma Siparişi (PO)** (opsiyonel — varsa)
3. **Hammadde:** Hangi RM geldi
4. **Miktar:** Ör. `1500` kg
5. **Lot No:** Tedarikçinin verdiği lot numarası
6. **Son kullanma tarihi**
7. **COA referansı:** Tedarikçi COA numarası
8. **Birim maliyet:** DZD/kg
9. **Container:** Hangi tank/depoya kondu (opsiyonel)
10. **Kaydet**

Sistem otomatik:
- Yeni `RawMaterialLot` kaydı oluşturur
- `qc_status = PENDING` yapar (test bekliyor)
- `remaining_qty = received_qty` (tam miktar kalan)
- `StockMovement(RECEIPT)` yazar

### 2.2 Lot Serbest Bırakma (QC Onayı)

Mal kabulden sonra QA lotu test eder. Sonuca göre:

**Yol:** Admin → RawMaterialLot detay → **Actions:**

- **Lot serbest bırak (RELEASED)** — Kullanıma açar
- **Lot karantinaya al** — Şüpheli, ek test bekliyor
- **Lot reddet** — Kullanılamaz, iade veya imha

Aksiyon seçildikten sonra otomatik `qc_status` güncellenir.

### 2.3 FEFO (First Expiry First Out)

Üretimde reçete dozajı yapılırken sistem **FEFO** algoritmasıyla lot seçer:
- Son kullanma tarihi en yakın olan lot ÖNCE tüketilir
- Böylece stok ıskartası minimize edilir
- **BR-QA-06:** Consumption anında lot düşülür

---

## 3. Stok Detay Sayfası (Alerte + Rupture)

### 3.1 Hammadde Detay Görüntüleme

**Yol:** Sol menü → **Stok / Depo** → hammaddeye tıkla

Doğrudan URL: `/portal/stok/hammadde/<pk>/`

Sayfa içeriği:

**Üst şerit:**
- Hammadde kodu + ad
- Tip, birim, yoğunluk
- **Sağ üstte:** Seviye badge'i
  - 🟢 **✓ Stok yeterli**
  - 🟠 **⚠ ALERTE — Uyarı**
  - 🔴 **🚨 RUPTURE — Kritik**

**Niveau de Stock kartı:**
- **Anlık stok** (büyük rakam)
- **Seuil d'alerte** (sarı)
- **Seuil de rupture** (kırmızı)
- **Valeur du stock** (DZD — ort. birim × kalan)
- **Progress bar** — anlık / alert eşik oranı

**Aktif Lotlar tablosu:**
- Her RELEASED lot: no, tedarikçi, kabul tarihi, kalan, birim maliyet

**Historique des Mouvements (son 50):**
- Date, Type (Consommation/Réception/Ajustement badge)
- Document Source (Ordre de Production, Ajustement no)
- Quantité (+/− renkli)
- Prix Unitaire (DZD)
- Observations
- Opérateur

### 3.2 Accès Rapides (Sol Sidebar'da)

Hammadde detay sayfasında sol sidebar'da hızlı erişim linkleri:
- ➕ **Créer un ajustement**
- 📋 **Voir tous les mouvements** (admin)
- 📜 **Historique ajustements** (admin)

### 3.3 Eşik (Threshold) Ayarlama

**Yol:** Admin → RawMaterial detayı → Alert threshold + Rupture threshold alanları

Örnek:
- Alert threshold: `5000` kg
- Rupture threshold: `1000` kg

**Ne olur:**
- Stok > 5000 kg → yeşil (OK)
- 1000 < Stok ≤ 5000 kg → sarı (ALERTE)
- Stok ≤ 1000 kg → kırmızı (RUPTURE — üretimi durdurabilir)

---

## 4. Ajustement de Stock (Tek Satır)

### 4.1 Ajustement Nedir?

Bir stok düzeltmesi, envanter farkı, kayıp, hasar gibi durumları belgeler.

### 4.2 Yeni Ajustement

**Yol:** Sol menü → **Stok / Depo** → **Yeni Ajustement**

Doğrudan URL: `/portal/stok/ajustement/yeni/`

1. **Lot (RELEASED):** Dropdown'dan seç (mevcut miktar gösterilir)
2. **Type d'ajustement:**
   - `INVENTORY` — Envanter sayımı (Inventaire)
   - `LOSS` — Kayıp / Fire (Perte)
   - `DAMAGE` — Hasar (Dégât)
   - `RETURN` — Tedarikçiye iade
   - `CORRECTION` — Düzeltme
   - `OTHER` — Diğer
3. **Yeni Miktar (Qté après):** Ölçülen yeni değer
   - Sistem otomatik: Delta = Qté après − Qté avant
4. **Motif:** Sebep (serbest metin — zorunlu)
5. **Document Justificatif (BR):**
   - `LOSS`, `DAMAGE`, `RETURN` için **ZORUNLU**
   - Diğerlerinde opsiyonel
   - Document type: Örn. "Vardiya raporu"
   - Document référence: Ör. "RAP-2026-071"
   - Dosya: PDF/JPG (< 10 MB)

Sistem otomatik yapılan:
- `StockAdjustment` kaydı üretilir
- `StockMovement (ADJUSTMENT)` yaratılır (delta ile)
- `RawMaterialLot.remaining_qty` güncellenir
- Hareket geçmişi zenginleştirilmiş: performed_by + observations + unit_price

### 4.3 BR — Justificatif Zorunluluğu

**LOSS / DAMAGE / RETURN** türü için belge YÜKLEMEZSENİZ:

```
BR : Perte / Dégât / Retour için justificatif belge zorunlu.
```

hatası alırsınız. Bu Cezayir üretim standardı gereği zorunlu.

---

## 5. Multi-Line Ajustement (Toplu Düzeltme)

### 5.1 Ne Zaman Kullanılır?

Aylık envanter sayımı gibi durumlar — birden çok lotu **aynı belgede** düzeltmek.

### 5.2 Yeni Multi-Line Ajustement

**Yol:** Sol menü → **Stok / Depo** → **Multi-Ligne**

Doğrudan URL: `/portal/stok/ajustement/multi/`

1. **Type d'ajustement:** Envanter, kayıp, vs.
2. **Motif genel (belge motifi):** Ör. "Aylık envanter sayımı Ağustos 2026"
3. **Lignes tablosu (8 satır):**

| # | Lot | Yeni Miktar | Satır motifi |
|---|-----|-------------|--------------|
| 1 | W · LOT-W-202606-014 · 3450 kg | 3400 | Sayım eksik |
| 2 | G · LOT-G-202607-023 · 5279 kg | 5300 | Sayım fazla |
| 3 | ... | ... | ... |

4. **Document Justificatif:** Genel belge (perte/dégât/return için zorunlu)
5. **Kaydet** — sistem tüm satırları atomik uygular

Sistem otomatik:
- 1 ana `StockAdjustment` (özet delta)
- N adet `StockAdjustmentLine` (her satır)
- N adet `StockMovement` (her lot için)
- N adet `remaining_qty` güncelleme

Toplam delta = tüm satır delta'larının toplamı.

---

## 6. Stok Hareket Geçmişi

### 6.1 Tüm Hareketleri Görüntüleme

**Yol:** Admin → `/admin/inventory/stockmovement/`

Filtreler:
- Movement type (RECEIPT / CONSUMPTION / ADJUSTMENT)
- Timestamp (date_hierarchy)
- Lot

### 6.2 Hammadde Bazlı Filtreleme

Bir hammaddenin tüm hareketlerini görmek için:
- Hammadde detay sayfasında **Historique des Mouvements** tablosu (son 50)
- Alternatif: Admin → Stock Movement → filtre `lot__raw_material__id__exact=<pk>`

### 6.3 Hareket Kayıtları Değişmez

**Önemli:** `StockMovement` kayıtları **SİLİNMEZ**. Yanlış hareket → ters kayıt (negatif) girmek gerekir. Audit trail bütünlüğü için.

---

## 7. Depo Bölgeleri (Storage Zones)

### 7.1 Depo Bölgesi Nedir?

Tehlike sınıfına göre ayrılmış lokasyondur. Örn:
- Zon-01: Yanıcı sıvılar (Klas 3)
- Zon-02: Korozif (Klas 8)
- Zon-03: Oksidan (Klas 5.1)

### 7.2 Depo Uyumluluğu

**Yol:** Admin → `/admin/chemicals/storageincompatibility/`

Örn: Klas 3 (yanıcı) + Klas 5.1 (oksidan) birlikte depolanamaz — patlama riski.

Sistem tanımlı incompatibility kurallarını izler; ihlal durumunda uyarı üretir.

---

## 8. Retention Numunesi (Referans Numune)

### 8.1 Retention Numunesi Nedir?

Her üretim partisinden alınan referans numunedir. Raf ömrü + 6 ay saklanır. Şikayet/uyuşmazlık durumunda yeniden analiz kaynağıdır.

### 8.2 Retention Numunesi Kaydı

**Yol:** Admin → `/admin/chemicals/retentionsample/add/`

1. Numune No
2. Bağlı ProductionBatch
3. Saklama yeri (dolap, oda)
4. Alınma tarihi
5. Son kullanma tarihi (raf ömrü + 6 ay)
6. Durum: STORED / RETESTED / DISPOSED / LOST

---

## 9. Raporlar

### 9.1 Depo Panosu

**Yol:** Sol menü → **Depo Panosu**

Gösterir:
- Lot statü dağılımı (PENDING/RELEASED/QUARANTINE/REJECTED sayıları)
- Test bekleyen lotlar (son 15)
- Serbest lotlar (son 15, son kullanma tarihine göre)
- Raf ömrü alarmları (yakın SKT)

### 9.2 Valorisation Stocks (Stok Değerleme)

**Yol:** Sol menü → **Raporlar** → **Stok Değerleme**

Gösterir:
- Her hammadde için:
  - Miktar
  - Ort. maliyet (weighted average)
  - Değer (DZD)
  - Seviye badge (OK/Alerte/Rupture)
- Toplam MP değeri (özet)

### 9.3 Historique des Mouvements Raporu

**Yol:** Admin → StockMovement → export CSV (tarih aralığı ile)

Muhasebede stok değeri kontrolü için kullanılır.

---

## 10. Sık Sorulan Sorular

**S: Mal kabul yaptım ama lot RELEASED olmuyor?**
C: Kabul sonrası QC testi gerekiyor. QA lot'u kontrol edip `Actions → Lot serbest bırak` yapmalı.

**S: FEFO nasıl çalışır?**
C: Reçete tüketiminde sistem RELEASED lotlar arasından **expiry_date** en yakın olanı seçer. Manuel lot seçimi de yapabilirsiniz (üretim tarafında).

**S: Ajustement yaptım ama LOSS belgesi istemedi?**
C: `INVENTORY`, `CORRECTION`, `OTHER` gibi tiplerde belge zorunlu değil. `LOSS`, `DAMAGE`, `RETURN` için zorunlu.

**S: Multi-line ajustement'te bir satırı boş bırakabilir miyim?**
C: Evet. Lot seçilmemiş veya miktar girilmemiş satırlar atlanır.

**S: Stok eşiklerini kim belirler?**
C: Depo müdürü + satın alma müdürü ortak karar verir. Ölçü: Ortalama günlük tüketim × tedarik süresi × güvenlik marjı.

**S: Progress bar %100'ün üstünde çıkabilir mi?**
C: Evet — stok alert threshold'un iki katından fazlaysa bar kapanır ama seviye "OK" olur.

**S: Retention numunesi imha etmek istiyorum?**
C: Admin → RetentionSample → durum DISPOSED yapılır. Fiziksel imha ile birlikte yazılı tutanak eklenmesi önerilir.

---

## 11. Uygulama Egzersizi

1. **Yeni mal kabul:** 2000 kg RM1, tedarikçi BASF, COA numarası, birim maliyet
2. **Lot serbest bırak:** Yukarıdaki lotu QA testi sonrası RELEASED yap
3. **Ajustement:** Envanter sayımı sonrası W lot'unda -50 kg düzeltme
4. **Multi-line:** Aylık envanter — 3 farklı lot düzeltmesi tek belgede
5. **Stok raporu:** Valorisation Stocks raporundan MP toplam değerini not al

Her egzersizi bitirdiğinizde depo müdürüne gösterin.
