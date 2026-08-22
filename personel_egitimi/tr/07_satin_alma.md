# 07 — Satın Alma Modülü

**Kime yönelik:** Satın alma sorumluları, satın alma müdürü, tedarik zinciri
**Süre:** 60 dakika
**Ön koşul:** `01_giris.md` okundu

Bu belge Satın Alma modülünün tüm kısımlarını içerir:
1. Tedarikçi Yönetimi
2. Satın Alma Siparişi (Purchase Order — PO)
3. Mal Kabul (Goods Receipt — GR)
4. Satın Alma Faturası (Purchase Invoice — AP)
5. Ödeme
6. Portal İzleme ve Raporlar

---

## 1. Tedarikçi Yönetimi

### 1.1 Yeni Tedarikçi

**Yol:** Admin → `/admin/masterdata/supplier/add/`

1. **Kod:** Ör. `S-2026-005`
2. **Ad:** Ör. `BASF Master Builders Solutions Algérie`
3. **İletişim (contact):** Telefon, e-posta
4. **Adres**
5. **NIF:** Cezayir vergi numarası
6. **NIS:** İstatistik kayıt no
7. **RC:** Ticaret sicil no
8. **IBAN/RIB:** Banka hesap bilgisi
9. **Ödeme koşulları:** Ör. `Net 30`, `Net 60`
10. **Aktif:** True

### 1.2 Tedarikçi Listesi

**Yol:** Admin → `/admin/masterdata/supplier/`

- Kod, ad, NIF görüntüsü
- Search: kod, ad, NIF
- Aktif/pasif filtresi

### 1.3 Cezayir Yasal Bilgiler

Cezayir'de tedarikçi kaydı için **zorunlu** alanlar:
- **NIF (Numéro d'Identification Fiscale)**
- **NIS (Numéro d'Identification Statistique)**
- **RC (Registre de Commerce)**

Bu bilgiler faturalarda ve DGI beyannamelerinde kullanılır.

---

## 2. Satın Alma Siparişi (Purchase Order)

### 2.1 Yeni PO

**Yol:** Admin → `/admin/purchasing/purchaseorder/add/`

1. **PO No:** Ör. `PO-2026-042`
2. **Tedarikçi**
3. **Sipariş tarihi**
4. **Vade tarihi** (expected delivery)
5. **Durum:** DRAFT (varsayılan)
6. **Notlar**

**Satırlar (PO Lines inline):**
- Hammadde
- Miktar
- Birim
- Birim fiyat (DZD)
- Beklenen tarih

### 2.2 PO Durum Akışı

```
DRAFT → APPROVED → PARTIAL_RECEIVED → RECEIVED
                                    ↘ CLOSED
```

- **DRAFT:** Taslak
- **APPROVED:** Onaylandı, tedarikçiye gönderildi
- **PARTIAL_RECEIVED:** Kısmi mal kabul
- **RECEIVED:** Tam mal kabul
- **CLOSED:** Kapatıldı (fatura kesildi + ödendi)
- **CANCELLED:** İptal

### 2.3 PO PDF Üretimi

*(Şu an admin action ile — portal formu gelecek sürümde)*

---

## 3. Mal Kabul (Goods Receipt — GR)

### 3.1 Portal'dan Mal Kabul

**Yol:** Sol menü → **Stok / Depo** → **Yeni Mal Kabul**

*Bu bölüm `05_stok.md`'de detaylıca anlatıldı — burada özet.*

1. **Tedarikçi**
2. **Purchase Order** (opsiyonel bağlantı)
3. **Hammadde**
4. **Miktar**
5. **Lot No** (tedarikçinin verdiği)
6. **Son kullanma tarihi**
7. **COA referansı**
8. **Birim maliyet**
9. **Container/Depo yeri**
10. **Kaydet**

Sistem otomatik:
- Yeni `RawMaterialLot` (qc_status = PENDING)
- `StockMovement (RECEIPT)`
- PO satırının `received_qty` alanı güncellenir

### 3.2 Kısmi Mal Kabul

PO'da 5000 kg sipariş verildi, tedarikçi 3000 kg gönderdi:
- Mal kabul kaydı: `quantity=3000`
- PO durumu: `PARTIAL_RECEIVED`
- Kalan miktar: `2000 kg` (sonraki sevkiyat için beklenir)

### 3.3 Fazla Mal Kabul

Tedarikçi hatalı olarak 5500 kg gönderdi (sipariş 5000 kg):
- Fazla 500 kg için:
  - Kabul edin → NCR açın (Supplier root cause)
  - Reddedin → iade et
  - Görüşme sonrası karar → CAPA açılabilir

---

## 4. Satın Alma Faturası (AP Invoice)

### 4.1 Yeni Purchase Invoice

**Yol:** Sol menü → **Muhasebe** → **Yeni Fatura**

- **Fatura Tipi:** `Satın alma (AP)` seçin
- **Tedarikçi** dropdown (Customer alanı gizlenir)
- **Fatura No:** Tedarikçinin verdiği belge no
- **Fatura tarihi + Vade tarihi**
- **Fatura satırı** (Ürün/Hammadde, miktar, HT fiyat, TVA)
- **Fatura eki:** Tedarikçinin orijinal faturasının PDF/JPG'si (DGI tebliği için zorunlu)

### 4.2 Fatura ile Mal Kabul Eşleştirme (Three-Way Match)

Muhasebeye fatura girildikten sonra üç veri kontrol edilir:
1. **PO** — sipariş verilen miktar + fiyat
2. **GR** — gerçek gelen miktar
3. **Invoice** — tedarikçinin faturadaki miktar + fiyat

**Uyuşmazlık senaryoları:**
- Fatura miktarı > GR → tedarikçiyle görüş
- Fatura fiyatı > PO fiyatı → tedarikçiyle görüş
- Miktar/fiyat uyumlu → onayla ve öde

---

## 5. Ödeme

### 5.1 Tedarikçiye Ödeme

Muhasebe modülünde detaylıca anlatıldı (`02_muhasebe.md`).

**Yol:** Purchase Invoice detayı → **Yeni Ödeme**

1. **Yön:** `Tediye (tedarikçiye)`
2. **Yöntem:** Havale (yaygın) / Çek / Nakit
3. **Tutar** ve **tarih**
4. **Banka detayları** (havale/çek için)

### 5.2 Havale ile Ödeme (Yaygın)

- Cezayir bankasından RIB üzerinden EFT
- Yöntem `Havale / EFT` seçin
- Transfer bankası: **BEA / BNA / CPA** vs. seçin
- IBAN yazın
- Transfer tarihi

### 5.3 Çek ile Ödeme

- Çek yöntemi seçildiğinde ek panel
- Çek numarası, keşide tarihi, vade tarihi
- Post-dated çek yaygın: örn. 60 gün vadeli
- Çek durumu: `Verildi` → banka tarafından ödenince `Ödendi`

---

## 6. Portal İzleme ve Raporlar

### 6.1 Satın Alma Panosu

**Yol:** Sol menü → **Satın Alma Panosu**

Gösterir:
- Bekleyen PO'lar (DRAFT + APPROVED)
- Beklenen mal kabul (son 30 gün)
- Kritik stoklar (rupture/alerte durumunda olan)
- Toplam satın alma tutarı (bu ay)

### 6.2 Alacak Yaşlandırma (Tedarikçi Tarafı — Aging Fournisseurs)

**Yol:** Sol menü → **Raporlar** → **Alacak Yaşlandırma** (Fournisseurs)

- Yaş grubu: 0-30, 31-60, 61-90, 90+ gün
- Toplam açık borç
- Tedarikçi bazlı kırılım

### 6.3 Tedarikçi Cari Hesabı

Bir tedarikçinin tüm faturalarını, ödemelerini görme:

**Yol:** Ör. `/portal/muhasebe/tedarikci-cari/<supplier_pk>/` *(gelecek özellik)*

Şu an admin arayüzünden Purchase Invoice listesini filtreleyerek görülebilir.

### 6.4 Rendements Fournisseurs (Tedarikçi Verimi)

*(Gelecek özellik — tedarikçi teslim süresi, kalite, zamanında gönderim skoru)*

---

## 7. Sık Sorulan Sorular

**S: PO oluşturdum ama tedarikçi kısmi malzeme gönderdi, kalanı nasıl takip ederim?**
C: PO durumu otomatik `PARTIAL_RECEIVED` olur. Her satırın `received_qty` alanına bakın — sipariş vs kabul edilen farkı gösterir.

**S: Fatura miktarı mal kabulden farklı, nasıl işlerim?**
C: Muhasebeye bildirin. Fark küçükse (< %2) tolerans kabul edilebilir. Büyükse tedarikçiden düzeltme talep edin veya credit note isteyin.

**S: Yeni tedarikçi için NIF/NIS/RC bilgisi yok, kaydı geciktirmeliyim?**
C: Evet — Cezayir DGI kaydınız için bu bilgiler zorunlu. Fatura almadan önce tedarikçiden yasal belgeleri isteyin.

**S: Post-dated çek yazdım ama banka çeki reddetti, ne yapmalıyım?**
C: Payment kaydına git → check_status = `BOUNCED`, check_bounce_reason doldur. Fatura otomatik `PARTIALLY_PAID` durumuna döner. Tedarikçiyle iletişime geçin.

**S: PO'yu iptal etmem gerekiyor, tedarikçi kabul etmez mi?**
C: Sözleşme koşullarınıza bağlı. İptal talep edin; kabul edilirse PO durumu `CANCELLED` yapılır. Reddedilirse sipariş geçerli kalır.

**S: Aynı tedarikçiden farklı hammaddeleri tek PO'da toplayabilir miyim?**
C: Evet. PO çoklu satır destekler — farklı hammaddeleri aynı sipariş içinde yönetebilirsiniz.

**S: Tedarikçi indirim (early payment discount) verdi, sistemde nasıl işlerim?**
C: Faturaya `discount_pct` alanı doldurulur (satış tarafındaki gibi). Ödeme kaydında indirim tutarı ayrı belirtilir.

---

## 8. Uygulama Egzersizi

1. **Yeni tedarikçi:** NIF/NIS/RC dolu, RIB bilgisi tam
2. **PO oluştur:** 3 hammadde, farklı miktarlar
3. **Mal kabul:** Yukarıdaki PO'nun 2 satırı için kısmi mal kabul
4. **Purchase Invoice:** Kabul edilen malın faturası + tedarikçi PDF eki
5. **Ödeme:** BEA bankasından havale ile ödeme kaydı

Her egzersizi bitirdiğinizde satın alma müdürüne gösterin.
