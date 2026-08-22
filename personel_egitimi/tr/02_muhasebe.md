# 02 — Muhasebe Modülü

**Kime yönelik:** Muhasebeciler, muhasebe müdürü, finans sorumlusu
**Süre:** 90 dakika
**Ön koşul:** `01_giris.md` okundu

Bu belge Muhasebe modülünün tüm kısımlarını içerir:
1. Fatura Kesme (Satış / Alım)
2. Ödeme Kaydı (Çek / Havale / Nakit)
3. Müşteri Avansı (§23) ve Tahsis
4. Gider Faturaları (Facture de Dépense)
5. Cari Hesap Görüntüleme
6. Mizan ve Dönem Kapatma
7. Raporlar

---

## 1. Fatura Kesme

### 1.1 Yeni Satış Faturası (AR)

**Yol:** Sol menü → **Muhasebe** → **Yeni Fatura**

1. **Fatura No** yazın — sistem `INV-2026-001` gibi bir öneri sunar
2. **Fatura Tipi:** `Satış (AR)` seçin
3. **Fatura Tarihi:** Bugün (varsayılan) veya seçin
4. **Vade Tarihi:** Boş bırakabilirsiniz; girmek isterseniz genelde 30 gün sonra
5. **Müşteri** dropdown'undan seçin
   - **Önemli:** Müşteri seçildiğinde, o müşteriye tanımlı **iskonto** varsa otomatik gelir
   - Ör. C002 GICA Groupe için `%15` iskonto tanımlıysa "İskonto Oranı" alanı otomatik `15,00` olur
6. **Fatura Satırı:**
   - Açıklama: ör. `Superplasticizer ADX-100 · 5000 kg`
   - Miktar: `5000`
   - Birim Fiyat (HT): `120,00` (DZD)
   - TVA Oranı: `TVA 19` (Cezayir varsayılan)
7. **Fatura Eki (opsiyonel):** Orijinal fatura PDF/JPG dosyası
8. **Notlar:** Serbest metin
9. **Faturayı Kaydet (Taslak)** butonuna basın

Fatura **Taslak (DRAFT)** durumunda oluşturulur — muhasebeye işlenmesi için ayrıca onaylama gereklidir.

### 1.2 Satın Alma Faturası (AP)

Aynı akış, sadece:
- **Fatura Tipi:** `Satın alma (AP)` seçin
- **Müşteri** alanı gizlenir, **Tedarikçi** alanı görünür — oradan seçin
- Fatura eki genellikle tedarikçinin orijinali (DGI tebliği için)

### 1.3 Alacak Dekontu (Avoir)

Müşteri iadesi veya düzeltmeler için:
- **Fatura Tipi:** `Alacak dekontu - satış (avoir)`
- Diğer alanlar aynı; tutar negatif olarak muhasebeleşir

### 1.4 Faturanın PDF Çıktısı

1. Faturalar listesinden faturaya tıklayın
2. Sağ üstteki **📄 PDF** butonuna basın
3. Yeni sekmede fatura A4 formatında açılır:
   - Şirket logosu + tam adres
   - NIF, NIS, RC, art. import numaraları (Cezayir yasal)
   - Émetteur / Facturé à kutuları
   - Satır tablosu (mavi başlık)
   - Toplam kutusu (HT + TVA + TTC + iskonto)
   - Banka/RIB bilgisi
   - İmza satırı + yasal footer
4. **Yazdır** (Ctrl+P) veya **PDF indir**

---

## 2. Ödeme Kaydı

### 2.1 Nakit veya Havale Ödemesi

**Yol:** Fatura detayı sayfasında → **Yeni Ödeme** butonu

1. **Yöntem** dropdown'undan seçin:
   - `Nakit (Espèces)`
   - `Havale / EFT (Virement)`
   - `Çek (Chèque)`
   - `Akreditif`
   - `Kart CIB`
2. **Yön:** `Tahsilat (müşteriden)` veya `Tediye (tedarikçiye)`
3. **Tarih** ve **Tutar** girin

### 2.2 Havale Ödemesi (Özel)

Yöntem `Havale / EFT` seçildiğinde ek panel açılır:
- **Transfer Bankası:** BEA, BNA, CPA, BADR gibi 13 Cezayir bankasından seçin
- **IBAN** yazın (Cezayir 24 hane RIB)
- **Transfer Tarihi**

### 2.3 Çek Ödemesi (Özel — Cezayir'de yaygın)

Yöntem `Çek (Chèque)` seçildiğinde detaylı panel açılır:
- **Çek Bankası:** 13 banka arasından seçin
- **Çek No**
- **Keşide Tarihi**
- **Vade Tarihi** (post-dated çek yaygındır)
- **Çek Durumu:** Alındı / Bankaya verildi / Karşılıksız (bounce)
- **Keşideci Adı** (çekin çıktığı hesap sahibi)
- **Çek Görseli** (fotoğraf/tarama — opsiyonel)

### 2.4 Ödemeden Sonra Fatura Durumu

Ödeme kaydedildikten sonra fatura otomatik güncellenir:
- Tam tutar ödendiyse → `PAID (Ödendi)`
- Kısmi ödeme → `PARTIALLY_PAID (Kısmi ödendi)`
- Ödeme öncesi → `DRAFT` veya `POSTED`

---

## 3. Müşteri Avansı ve Tahsis (§23)

Müşteri fatura kesilmeden önce ön ödeme yapmışsa avans olarak kaydedilir.

### 3.1 Yeni Avans Kaydı

**Yol:** Sol menü → **Müşteri Avansları** → **+ Yeni Avans** (sağ üstte)

Alternatif: Admin arayüzü → `/admin/accounting/customeradvance/add/`

1. **Avans No:** `ADV-2026-001` gibi
2. **Müşteri:** dropdown'dan seçin
3. **Tarih**
4. **Tutar** (TTC)
5. **Yöntem:** Havale / Çek / Nakit
6. **Belge Referansı:** Havale ref no, çek no veya makbuz no
7. **Kaydet**

Avans **OPEN (Açık)** durumuyla oluşur.

### 3.2 Avansı Faturaya Tahsis Etme

Müşteriye fatura kesildikten sonra avansı o faturaya bağlamak istersiniz:

1. **Müşteri Avansları** listesine gidin
2. İlgili avansın yanındaki **"Tahsis Et"** butonuna basın
3. Açılan formda:
   - **Fatura** dropdown'dan seçin (aynı müşterinin faturaları listelenir)
   - **Tahsis Tutarı** girin (maksimum: avansın kalan tutarı)
4. **Tahsis Et** butonuna basın

Sistem otomatik:
- Faturanın `amount_paid` alanını arttırır
- Fatura tam ödendiyse `PAID` yapar
- Avans tam tükendiyse `FULLY_ALLOCATED` yapar

### 3.3 Avans Bölme (Birden Fazla Faturaya)

Bir avans birden çok faturaya bölünebilir. Ör:
- Avans: 150.000 DZD
- Fatura 1: 80.000 DZD → 80.000 DZD tahsis
- Fatura 2: 50.000 DZD → 50.000 DZD tahsis
- Avans kalan: 20.000 DZD (yeni faturaya kadar bekler)

---

## 4. Gider Faturaları (Facture de Dépense)

Bakım/tamir, kira, danışmanlık, elektrik gibi işletme giderleri **ayrı** belgelenir.

### 4.1 Yeni Gider Faturası

**Yol:** Sol menü → **Gider Faturaları** → **+ Yeni Gider Faturası**

1. **Fournisseur (Tedarikçi):** Bakım firması, danışman, kira sahibi
2. **Catégorie (Kategori):** 11 seçenek
   - Réparation / Maintenance
   - Elektrik / Su / Doğalgaz
   - Kira
   - Danışmanlık / Etüd
   - Nakliye / Yakıt
   - Temizlik / Hijyen
   - Güvenlik
   - Ofis / Kırtasiye
   - Hukuk / Vergi
   - Pazarlama / Reklam
   - Autre / Diğer
3. **Fatura Tarihi** ve **Vade Tarihi**
4. **Fournisseur Invoice N°:** Tedarikçinin belge numarası
5. **Détails / Récapitulatif:** İş açıklaması (ör. "Reactor R-101 pompa değişimi")
6. **Ekipman / Yer Referansı:** Hangi ekipman/lokasyon için
7. **Montant HT** ve **TVA Oranı** girin
   - TVA otomatik hesaplanır
   - TTC otomatik güncellenir
8. **Fatura belgesi:** PDF/JPG (Cezayir yasal — orijinal saklanmalı)
9. **Kaydet (Taslak)**

### 4.2 Gider Faturası Onay Akışı

Yeni gider faturası **DRAFT (Taslak)** olarak oluşur. Ödeme için onay gerekir:

1. **DRAFT** → Muhasebeci **"Onaya Sun"** butonuna basar → **SUBMITTED**
2. **SUBMITTED** → Müdür detaya girer, **✓ Onayla** veya **✗ Reddet** butonuna basar
3. **APPROVED** → Ödeme yapılınca **"💳 Ödendi olarak işaretle"** + ödeme referansı girilir → **PAID**

### 4.3 Kimin Ne Yetkisi Var

- **Muhasebeci:** Taslak oluşturma + onaya sunma
- **Muhasebe Müdürü:** Onaylama + reddetme + ödeme işaretleme
- **Genel Müdür:** Tüm işlemler + değişiklik

---

## 5. Cari Hesap Görüntüleme (Relevé de Compte Client)

Bir müşterinin tüm faturalarını, ödemelerini ve avanslarını tek ekranda görün.

### 5.1 Cari Hesap Nasıl Açılır

**Yol:** Sol menü → **Raporlar** → **Alacak Yaşlandırma** → müşteri satırındaki **Detay** butonu

Alternatif: URL doğrudan `/portal/muhasebe/cari/<müşteri_id>/`

### 5.2 Sayfada Neler Var

**4 KPI Kartı:**
- Toplam Fatura (TTC)
- Toplam Ödeme
- Açık Avans
- **Bakiye (Solde)** — alacaklıyız mı yoksa denk mi?

**Faturalar Tablosu:**
- Fatura no, tarih, TTC, ödenen, kalan, durum

**Avanslar Tablosu:**
- Avans no, tarih, tutar, tahsis, kalan, durum

### 5.3 Cari Hesabı PDF Olarak İndirme

*(Bu özellik yakında gelecek — şu an ekran görüntüsü alarak yazdırılabilir)*

---

## 6. Mizan ve Dönem Kapatma

### 6.1 Mizan (Trial Balance)

**Yol:** Sol menü → **Mizan (Balance)**

Cezayir SCF (PCN 2010) hesap planına göre:
- **1'ler:** Öz sermaye (Capitaux propres)
- **2'ler:** Duran varlıklar (Immobilisations)
- **3'ler:** Stoklar (Stocks)
- **4'ler:** Alacaklar/Borçlar (Créances/Dettes)
- **5'ler:** Nakit ve banka (Trésorerie)
- **6'lar:** Giderler (Charges)
- **7'ler:** Gelirler (Produits)

Her hesap için:
- Borç (Débit)
- Alacak (Crédit)
- Bakiye (Solde)

### 6.2 Hesap Detayı (Ledger)

Bir hesabın hareketlerini görmek için:
- Mizan tablosundaki hesap numarasına tıklayın
- Tüm yevmiye satırları listelenir (tarih, açıklama, borç, alacak)

### 6.3 Aylık Dönem Kapatma

Ay sonu geldiğinde:
1. Tüm gider faturaları **APPROVED** durumunda olmalı
2. Tüm satış faturaları **POSTED** durumunda olmalı
3. Muhasebe müdürü dönemi kapatır: `/admin/accounting/period/` üzerinden
4. **CLOSED** duruma çekilen dönemde artık yeni fatura kesilemez
5. G50 beyannamesi hazırlığı — ayın 20'sine kadar DGI'ye teslim

---

## 7. Raporlar

### 7.1 Muhasebe Panosu

**Yol:** Sol menü → **Muhasebe Panosu**

- 8 KPI kart (bugünkü gelir, açık alacak vs.)
- 6 Chart.js grafik (aylık trend, ödeme türleri, aging vs.)
- 2 tablo (yaklaşan çekler, gecikmiş faturalar)

### 7.2 Alacak Yaşlandırma (Échéancier Clients)

**Yol:** Sol menü → **Raporlar** → **Alacak Yaşlandırma**

- Yaş grubu: 0-30, 31-60, 61-90, 90+ gün
- Toplam açık alacak
- Müşteri bazlı kırılım
- Her müşteri için **Detay** butonu ile cari hesaba git

### 7.3 Borç Yaşlandırma (Échéancier Fournisseurs)

Aynı mantık, ama tedarikçi tarafında.

---

## 8. Sık Sorulan Sorular

**S: Fatura kestim ama iskonto otomatik gelmedi, ne yapmalıyım?**
C: Müşteri kaydında `default_discount_pct` alanı boş demektir. Müşteri kaydını açıp iskonto oranını yazın (`/admin/masterdata/customer/`), sonra tekrar fatura kesin.

**S: Ödemeyi yanlış müşteriye kaydettim, silebilir miyim?**
C: Direkt silinemez (audit trail). Ters kayıt (negatif ödeme) girmeniz gerekir. Muhasebe müdürüne bilgi verin.

**S: Çek karşılıksız çıktı, nasıl işlerim?**
C: İlgili Payment kaydına git → `check_status` alanını `BOUNCED` yap + `check_bounce_reason` doldur. Fatura otomatik olarak `PARTIALLY_PAID`'e döner.

**S: Gider faturasını onayladım ama silmek istiyorum?**
C: Onaylanmış fatura silinemez. Muhasebe müdürüne başvur; ters kayıt (credit note) girebilir.

**S: Müşteri avansı ile fatura arasında farklı müşteri seçtiğimde hata veriyor?**
C: Bu doğru davranış. Bir avans **sadece kendi müşterisinin** faturasına tahsis edilebilir. Yanlış müşteri seçtiyseniz **İptal** edin.

**S: Cezayir sayı formatı yerine noktalı format çıkıyor?**
C: Tarayıcı dil ayarınızı kontrol edin. Chrome → Ayarlar → Dil → **Français (Algérie)** olmalı.

---

## 9. Uygulama Egzersizi

Eğitimin sonunda bu 5 örneği yapın:

1. **Yeni fatura:** 3 satırlı, 2 farklı ürün, %19 TVA, %10 iskonto
2. **Ödeme:** Yukarıdaki faturaya %60 çek + %40 havale bölünmüş ödeme
3. **Avans:** Yeni müşteriden 100.000 DZD nakit avans kaydı
4. **Gider faturası:** MECATECH bakım faturası (Réparation Machine)
5. **Cari hesap:** Bir müşterinin cari hesabını görüntüle + ekran görüntüsü al

Her egzersizi bitirdiğinizde eğitmene gösterin.
