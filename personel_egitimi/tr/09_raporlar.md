# 09 — Yönetim Raporları

**Kime yönelik:** Genel müdür, direktör, finans müdürü, üretim müdürü, kalite müdürü
**Süre:** 60 dakika
**Ön koşul:** `01_giris.md` okundu, ilgili modül belgeleri okundu

Bu belge yönetim raporlarının tümünü içerir:
1. Rapor Merkezi (Hub)
2. Muhasebe Panosu
3. Alacak Yaşlandırma (Echéancier Clients)
4. Borç Yaşlandırma (Echéancier Fournisseurs)
5. Stok Değerleme (Valorisation Stocks)
6. Üretim Verimi (Rendements Production)
7. BL-Fatura Eşleştirme
8. Cari Hesap Özeti (Relevé de Compte Client)
9. SCADA Entegrasyon Panosu
10. Ne Zaman Hangi Raporu Okumalıyım?

---

## 1. Rapor Merkezi (Hub)

### 1.1 Merkezi Erişim

**Yol:** Sol menü → **Yönetim Raporları** → **Rapor Merkezi**

Doğrudan URL: `/portal/rapor/`

Bu ekran şirketin genel finansal durumunu tek bakışta gösterir.

### 1.2 KPI Kartları (Üstte 4 Kart)

| KPI | Açıklama |
|-----|----------|
| **Revenus facturés (mois)** | Bu ay kesilmiş fatura toplamı (TTC) |
| **Charges totales (mois)** | Bu ay giderler + purchase invoices |
| **Résultat net** | Revenus − Charges (Bénéfice/Perte badge) |
| **Bu ay revenus** | Faturalanan revenus özeti |

### 1.3 Rapor Kartları (6 Tıklanabilir Kart)

Her kart bir detay rapora yönlendirir:

1. **Résultat financier** — P&L théorique + trésorerie
2. **Échéancier clients** — Alacak yaşlandırma
3. **Échéancier fournisseurs** — Borç yaşlandırma
4. **Rendements production** — Üretim verimi analizi
5. **Répartition dépenses** — Gider kategori dağılımı
6. **Valorisation stocks** — Stok değerleme
7. **BL-Facture matching** — İrsaliye-fatura eşleştirme

### 1.4 Kullanım Sıklığı

- **Genel Müdür:** Haftalık — üst düzey KPI'lar
- **Finans Müdürü:** Günlük — Echéancier clients + BL-Fatura
- **Üretim Müdürü:** Haftalık — Rendements production
- **Depo Müdürü:** Aylık — Valorisation stocks

---

## 2. Muhasebe Panosu

### 2.1 Erişim

**Yol:** Sol menü → **Muhasebe Panosu**

Doğrudan URL: `/portal/muhasebe/`

### 2.2 İçerik

**8 KPI Kart:**
- Bugünkü tahsilat
- Bu ay tahsilat
- Açık alacak (toplam)
- Vadesi gelen bu hafta
- Kesilmemiş BL (fatura edilecek)
- Bekleyen çek (post-dated)
- Karşılıksız çek uyarısı
- Aktif avanslar

**6 Chart.js Grafik:**
- Aylık gelir/gider trendi
- Ödeme türü dağılımı (Havale/Çek/Nakit doughnut)
- Aging (0-30, 31-60, 61-90, 90+ bar)
- TVA aylık trend
- Top müşteriler (revenus bazında)
- Fatura durumu pie

**2 Tablo:**
- Yaklaşan çekler (post-dated)
- Gecikmiş faturalar

### 2.3 Nasıl Kullanılır?

Her sabah **5 dakikada** göz atın:
- Vadesi gelmiş çek var mı? → tahsilat için gönder
- Karşılıksız çek uyarısı → müşteriyle görüş
- Aging kırmızı bölgede müşteri → kolleksiyon başlat

---

## 3. Alacak Yaşlandırma (Echéancier Clients)

### 3.1 Erişim

**Yol:** Sol menü → **Yönetim Raporları** → **Alacak Yaşlandırma**

Doğrudan URL: `/portal/rapor/echeancier-clients/`

### 3.2 Bucket'lar (5 Yaş Grubu)

Her açık faturanın vade tarihinden itibaren kaç gün geçtiğine göre gruplar:

| Bucket | Anlamı | Renk |
|--------|--------|------|
| **Vadesi gelmemiş** | Vade tarihi gelecekte | Yeşil |
| **0-30 gün** | Yeni gecikmiş | Mavi (bilgi) |
| **31-60 gün** | Orta gecikme | Sarı (uyarı) |
| **61-90 gün** | Ciddi gecikme | Sarı-Kırmızı |
| **90+ gün** | Kritik risk | Kırmızı |

### 3.3 Müşteri Bazlı Kırılım

Tablo her müşteri için:
- Vadesi gelmemiş tutar
- 0-30, 31-60, 61-90, 90+ tutarları
- **TOPLAM** (en sağ, kalın)
- **Detay butonu** → müşteri cari hesabına git

### 3.4 Kullanım Senaryoları

**Senaryo 1 — Haftalık kolleksiyon toplantısı:**
- Rapor açılır, 90+ bucket'a bakılır
- Her müşteri için aksiyon belirlenir (ara, mektup, ziyaret, hukuk)

**Senaryo 2 — Aylık yönetim toplantısı:**
- Toplam açık alacak trendi
- Ortalama tahsilat süresi (DSO)
- Kritik müşteri listesi

**Senaryo 3 — Yıllık şüpheli alacak karşılığı:**
- 180+ gün gecikmiş faturalar için şüpheli alacak karşılığı ayrılabilir
- Muhasebeye bildir

---

## 4. Borç Yaşlandırma (Echéancier Fournisseurs)

### 4.1 Erişim

**Yol:** Sol menü → **Yönetim Raporları** → **Borç Yaşlandırma**

*(Şu an admin arayüzden — portal sayfası gelecek)*

### 4.2 Yapı

Alacak yaşlandırması ile aynı — sadece **borç tarafı** (tedarikçilere olan yükümlülük).

### 4.3 Kullanım

- Ödeme öncelik listesi
- Nakit akışı planlaması
- Erken ödeme indirimi fırsatları
- Vadesi gelen faturaların takibi

---

## 5. Stok Değerleme (Valorisation Stocks)

### 5.1 Erişim

**Yol:** Sol menü → **Yönetim Raporları** → **Stok Değerleme**

Doğrudan URL: `/portal/rapor/valorisation-stocks/`

### 5.2 İçerik

**KPI Kart (üstte):**
- Toplam MP değeri (DZD)
- Hammadde çeşidi sayısı

**Tablo:**
| Kod | Ad | Miktar | Ort. Maliyet | Değer (DZD) | Seviye |
|-----|-----|--------|--------------|-------------|--------|
| G | Sodyum glukonat | 5.279,50 kg | 265,80 | 1.403.299,00 | ✓ |
| HD | Katkı bileşeni | 3.435,40 kg | 332,48 | 1.142.203,70 | ⚠ Alerte |
| SP | Superplastik. PCE | 4.198,00 kg | 165,00 | 692.670,00 | ⚠ Alerte |
| W | Su | 7.919,30 L | 199,09 | 1.576.670,20 | ✓ |

**Alt satırda:** TOPLAM (kalın)

### 5.3 Kullanım Senaryoları

**Senaryo 1 — Ay sonu envanter değerleme:**
- Muhasebe için stok değeri (mizanda 31'lerin gerçek karşılığı)
- Vergi beyannamesinde stok değeri raporlama

**Senaryo 2 — Nakit optimizasyon:**
- Yüksek değerli düşük dönen stoklar identify et
- Fazla stok → sipariş miktarı azalt
- Düşük stok (rupture eşiğinde) → satın alma acil

**Senaryo 3 — Rupture uyarısı:**
- Rupture badge'li hammaddeler → üretim risk altında
- Acil satın alma emri gerekir

---

## 6. Üretim Verimi (Rendements Production)

### 6.1 Erişim

**Yol:** Sol menü → **Yönetim Raporları** → **Üretim Verimi**

Doğrudan URL: `/portal/rapor/rendements-production/`

### 6.2 İçerik

**3 KPI Kart:**
- Toplam Hedef (kg — son 90 gün)
- Toplam Gerçek (kg)
- **Ortalama Verim** (%)

**Renk kodlaması:**
- 🟢 %98+ — Mükemmel
- 🟠 %95-98 — Kabul edilebilir
- 🔴 <%95 — Sorunlu, incele

**Tablo (Son 100 batch):**
| Parti | Ürün | Hedef | Gerçek | Delta | Verim |
|-------|------|-------|--------|-------|-------|
| BATCH-202509-024 | ADX-100 | 1.404,00 | 1.432,08 | +28,08 | %102 |
| BATCH-202601-023 | ADX-100 | 507,00 | 507,00 | 0,00 | %100 |
| BATCH-202604-022 | ADX-100 | 604,00 | 591,92 | -12,08 | %98 |

### 6.3 Kullanım Senaryoları

**Senaryo 1 — Reçete revizyonu:**
- Bir üründe sürekli %95'in altında verim → reçete yeniden hesaplanmalı
- Ör. bilan massique complément fazla su tamamlıyor

**Senaryo 2 — Reaktör analizi:**
- Aynı reçete farklı reaktörlerde farklı verim
- Reaktör kalibrasyonu (CMMS) sorgulanır

**Senaryo 3 — Operatör performansı:**
- Aynı vardiyada verim düşük → eğitim ihtiyacı
- Delta'lar sistematik negatifse dozajlama sensörü kalibre edilir

---

## 7. BL-Fatura Eşleştirme

Detay `06_satis.md` § 10'da anlatıldı. Özet:

**Yol:** Sol menü → **Yönetim Raporları** → **BL-Fatura Eşleştirme**

Doğrudan URL: `/portal/rapor/bl-fatura/`

**KPI:**
- Eşleşen BL
- Bekleyen BL (fatura kesilmemiş)
- **Bekleyen tutar** (kritik — nakit akışı)
- İptal BL

**Kullanım:** Bekleyen BL listesi → hızlı fatura kesimi → nakit akışı iyileşir.

---

## 8. Cari Hesap Özeti (Relevé de Compte Client)

### 8.1 Erişim

Alacak yaşlandırmasından bir müşteriye tıkla → **Detay** butonu

Doğrudan URL: `/portal/muhasebe/cari/<customer_pk>/`

### 8.2 İçerik

**4 KPI Kart:**
- Toplam Fatura (TTC)
- Toplam Ödeme
- Açık Avans
- **Bakiye (Solde)** — alacaklıyız / denk

**Tablo 1 — Faturalar:**
- No, tarih, TTC, ödenen, kalan, durum

**Tablo 2 — Avanslar (§23):**
- No, tarih, tutar, tahsis, kalan, durum

### 8.3 Kullanım Senaryoları

**Senaryo 1 — Müşteri görüşmesi:**
- Müşteri "Ne kadar borcum var?" diyor → cari hesap gösterilir
- Ekran görüntüsü alıp müşteriye gönder

**Senaryo 2 — Yıl sonu mutabakat:**
- Muhasebede müşteri bakiyesi vs müşteri kayıtları karşılaştırılır
- Fark varsa detayına inilir (fatura mı ödeme mi eksik)

**Senaryo 3 — Şüpheli alacak analizi:**
- 90+ gün gecikmiş faturalar
- Aynı müşteride sürekli gecikme → risk skoru artırılır

---

## 9. SCADA Entegrasyon Panosu

### 9.1 Erişim

**Yol:** Sol menü → **SCADA**

Doğrudan URL: `/portal/scada/`

### 9.2 İçerik

**4 KPI Kart:**
- **Köprü Durumu** — ONLINE / Beklemede
- Bugün SCADA batch sayısı
- Bu hafta SCADA batch sayısı
- Toplam SCADA batch sayısı (tüm zamanlar)

**Bridge Kimlik & API paneli:**
- Bridge Kullanıcı (`scada_bridge`) durumu (✓ aktif / ⚠ kurulmadı)
- Token oluşturulma tarihi
- Son 8 karakter (güvenlik için tam gösterilmez)
- API endpoint listesi (kopyala-yapıştır için)

**Son 24 Saat Aktivite Grafiği:**
- Saatlik bar chart — kaç batch geldi

**Son 20 SCADA Batch tablosu:**
- Batch no, reçete, hedef, gerçek, verim, operatör, tamamlandı

### 9.3 Sorun Giderme

- **Köprü OFFLINE** → SCADA sistem sunucusu ile iletişim yok. IT/entegratöre haber ver.
- **Verim %95 altı** → SCADA'da dozajlama sorunu olabilir. Üretim müdürüne haber ver.
- **Boş tablo** → Sistem yeni kurulmuş veya batch gelmiyor. Entegratör konfigürasyonunu kontrol et.

---

## 10. Ne Zaman Hangi Raporu Okumalıyım?

### 10.1 Günlük (5 dk)

- **Muhasebe panosu:** Vadesi gelmiş çekler + karşılıksız uyarıları
- **SCADA panosu:** Bugünkü batch sayısı + köprü durumu

### 10.2 Haftalık (30 dk)

- **Rapor merkezi KPI'ları:** Bu haftaki revenus vs charges
- **Alacak yaşlandırma:** 90+ gün grubu → kolleksiyon aksiyonları
- **BL-Fatura eşleştirme:** Bekleyen tutar → fatura kesim önceliklendirme

### 10.3 Aylık (2 saat)

- **Muhasebe panosu detaylı analiz** — trend grafikleri
- **Stok değerleme** — envanter değeri, rupture uyarıları
- **Üretim verimi** — reçete/reaktör/operatör performansı
- **Cari hesap özeti (top 10 müşteri)** — yıllık büyüme analizi

### 10.4 Üç Aylık (yönetim kurulu)

- Rapor merkezi P&L
- Tüm müşteri portföyü analizi
- Tedarikçi performansı
- Kalite metrikleri (FAIL oranı, NCR sayısı, CAPA etkinliği)

### 10.5 Yıllık (dış denetim + vergi)

- Yıllık P&L (SCF PCN 2010 formatı)
- Tam mizan
- Envanter değeri (31 Aralık kesim)
- Yıllık TVA beyanı (12 aylık G50 özet)
- FPC audit + ISO 9001 audit hazırlığı

---

## 11. Sık Sorulan Sorular

**S: Rapordaki rakamlar hangi para biriminde?**
C: Hepsi **DZD** (Cezayir Dinarı). Cezayir Fransız formatında: `1.234.567,89 DZD` (nokta binlik, virgül ondalık).

**S: Aging bucket'ları nasıl hesaplanır?**
C: Fatura vade tarihi (`due_date`) ile bugün arasındaki gün farkı. `due_date` boşsa `date` (fatura tarihi) kullanılır.

**S: Stok değeri neden mizanla uyuşmuyor?**
C: Muhasebede stok periyodik güncellenir (ay sonu). Portal rapor **canlı** — anlık gösterir. Ay sonu kapatmada uyuşur.

**S: Verim raporu SCADA batch'lerinde farklı çıkıyor?**
C: SCADA otomatik ölçüm daha hassas. Manuel batch'lerde operatör hatası olabilir.

**S: Cari hesap özeti PDF olarak indirilebilir mi?**
C: Şu an değil — ekran görüntüsü + Excel export gelecek. Yakında.

**S: Ay sonu itibariyle rapor almam gerekiyor, snapshot alabilir miyim?**
C: Tarayıcı ile Ctrl+P (yazdır → PDF) yapabilirsiniz. Otomatik snapshot özelliği gelecek.

**S: SCADA panosunda bir batch görmüyorum ama üretimde var?**
C: Batch **SCADA-** prefixi ile kaydedilmemiş demektir (manuel oluşturulmuş). SCADA batchlerin `production_order.order_number` alanı `SCADA-` ile başlar.

---

## 12. Uygulama Egzersizi

1. **Rapor merkezi:** 5 dakikada tüm KPI'ları oku, notlar al
2. **Aging analizi:** Top 3 riskli müşteriyi belirle, aksiyon önerisi yaz
3. **Verim analizi:** Bir üründe %95 altı batch'leri listele, sebepleri sorgula
4. **Cari hesap:** Bir müşteri için relevé ekran görüntüsü al
5. **SCADA sağlık:** Son 24 saat aktivite grafiğinden en yoğun saati belirle

Her egzersizi bitirdiğinizde ilgili müdüre gösterin.
