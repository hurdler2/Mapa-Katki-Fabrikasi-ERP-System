# 01 — Sisteme Giriş ve Arayüz

**Kime yönelik:** Tüm çalışanlara
**Süre:** 30 dakika
**Ön koşul:** Yok — ilk okunacak belge

---

## 1. Sisteme İlk Kez Giriş

### 1.1 Erişim Bilgileri

Sistem yöneticiniz size şu bilgileri verir:
- **Web adresi:** `http://erp.mapa.dz` veya `http://192.168.1.100:8000` (fabrika içi)
- **Kullanıcı adı:** Ör. `ahmet.yilmaz` veya `mohamed.belaidi`
- **Geçici parola:** İlk girişte değiştireceğiniz parola

### 1.2 İlk Giriş Adımları

1. Tarayıcınızı açın (Chrome, Firefox veya Edge önerilir)
2. Adres çubuğuna sisteminizin URL'sini yazın
3. **Giriş ekranı** açılır — kullanıcı adı ve parolanızı girin
4. **"Giriş Yap"** butonuna basın
5. İlk girişte parola değiştirme ekranı gelirse **güçlü bir parola** seçin:
   - En az 8 karakter
   - Büyük harf, küçük harf, rakam
   - Ör. `Mapa2026!` gibi

### 1.3 Parolanızı Unutursanız

- IT sorumlusunu arayın — parolanızı sıfırlayabilir
- Kimseyle **kesinlikle** parolanızı paylaşmayın

---

## 2. Arayüz Tanıtımı

Giriş yaptıktan sonra karşınıza **Ana Ekran (Panel)** çıkar. Ekranın üç ana bölümü var:

```
┌─────────────────────────────────────────────────────────┐
│  ADMIX-ERP     Ahmet Kaya · Muhasebe        [Çıkış]    │  ← ÜST ŞERİT
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│   SOL    │              ANA İÇERİK ALANI                │
│  MENÜ    │           (seçtiğiniz sayfa)                 │
│          │                                              │
│  🏠 Panom │                                              │
│  💰 Muha- │                                              │
│     sebe │                                              │
│  🏭 Üretim│                                              │
│  🔬 Kalite│                                              │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

### 2.1 Üst Şerit

- **Solda:** ADMIX-ERP logosu (buraya tıklarsanız ana ekrana dönersiniz)
- **Sağda:** Adınız + rolünüz + **Çıkış Yap** butonu
- Ayrıca **onay bekleyen işleriniz** varsa bildirim rozeti görünür

### 2.2 Sol Menü

Rolünüze göre farklı menüler görürsünüz. Ana grup başlıkları:

| Grup | İçerik |
|------|--------|
| **Ana Ekran** | Panom, Onay Bekleyenler, Bildirimler |
| **Üretim** | Reçeteler, Üretim emirleri, Batch'ler |
| **Kalite** | Şartnameler, Numuneler, NCR |
| **Stok / Depo** | Hammadde, Lotlar, Ajustement |
| **Satış** | Müşteriler, BL Client, Faturalar |
| **Satın Alma** | Tedarikçiler, Siparişler |
| **Muhasebe** | Faturalar, Avanslar, Gider faturaları |
| **Yasal Uyum** | SDS, DoP, REACH, FPC Audit |
| **Yönetim Raporları** | BI Dashboard, Rapor Merkezi |

**Not:** Menüde bazı bölümleri göremiyorsanız — o role yetkiniz yok. Yöneticinizle konuşun.

### 2.3 Ana İçerik Alanı

Bu, seçtiğiniz sayfa/formun gösterildiği yerdir. Genelde üç kısımdan oluşur:

- **KPI kartları (üstte):** Özet rakamlar — bugün / hafta / toplam
- **Filtre çubuğu:** Statü, tarih, kategori filtreleri
- **Ana tablo / form:** Kayıt listesi veya doldurulacak form

---

## 3. Ortak İşlemler

Tüm modüllerde tekrar eden temel işlemler:

### 3.1 Kayıt Listesini Görüntüleme

Örnek: Faturalar sayfası → tüm faturalarınızın listesi tablo olarak görünür.

- **Arama kutusu** (varsa): kayıt numarası veya isim yazın
- **Filtre butonları:** "Tümü", "Onay bekleyen", "Ödendi" gibi
- **Sıralama:** Sütun başlıklarına tıklayarak sıralayın

### 3.2 Yeni Kayıt Ekleme

- Sayfanın sağ üst köşesindeki mavi **"+ Yeni ..."** butonu
- Boş form açılır — zorunlu alanlar `*` ile işaretli
- **Kaydet** butonu ile tamamlarsınız

### 3.3 Kayıt Görüntüleme / Düzenleme

- Tablodaki bir satıra tıklayın → detay sayfası açılır
- Sağ üstteki **Düzenle** butonuyla değiştirebilirsiniz
- Yetkiniz yoksa **Düzenle** butonu gri görünür

### 3.4 Dosya Ekleme

Çoğu forma dosya ekleyebilirsiniz (PDF fatura, JPG kalibrasyon belgesi vs.):

1. **"Dosya seç"** butonuna basın
2. Bilgisayarınızdan PDF/JPG/PNG seçin (maks 10 MB)
3. **Kaydet** sonrası dosya otomatik yüklenir
4. İndirmek için dosya adına tıklarsınız

### 3.5 Rapor / PDF İndirme

Fatura, SDS, DoP gibi belgeleri PDF olarak indirebilirsiniz:

- Detay sayfasında sağ üstte **"📄 PDF"** butonu
- Tıklayınca yeni sekmede belge açılır — indirebilir veya yazdırabilirsiniz

---

## 4. Roller ve Yetkiler

Her kullanıcının bir **rolü** vardır. Rol, ne görebileceğinizi ve ne yapabileceğinizi belirler.

| Rol | Ne yapabilir |
|-----|--------------|
| **Muhasebeci** | Fatura kesme, tahsilat, cari hesap görüntüleme |
| **Muhasebe Müdürü** | Muhasebeci + gider faturası onaylama, dönem kapatma |
| **Üretim Sorumlusu** | Reçete seçme, batch başlatma, üretim emri açma |
| **Kalite / QA** | Şartname onaylama, NCR açma, numune yönetimi |
| **Depo Sorumlusu** | Mal kabul, stok düzeltme, sevkiyat |
| **Satış Temsilcisi** | Müşteri kaydı, BL kesme, sipariş takibi |
| **Satın Alma** | Tedarikçi, sipariş, mal kabul |
| **Genel Müdür** | Herşeyi görebilir, raporlara erişim |

**"Bu sayfaya yetkiniz yok"** hatası alırsanız → yöneticinize gidin, rol atanması gerekiyor.

---

## 5. Cezayir Sayı Formatı

Sistem **Fransız/Cezayir formatını** kullanır:

- ✅ Doğru: `1.234.567,89 DZD` (nokta binlik, virgül ondalık)
- ❌ Yanlış: `1,234,567.89` (İngiliz formatı — sistemde kullanmayın)

**Dikkat:** Yeni fatura girerken tutarları `1234.56` olarak (Excel gibi) yazın; sistem otomatik olarak `1.234,56` olarak gösterir.

---

## 6. Sık Kullanılan Kısayollar

| Kısayol | Sonuç |
|---------|-------|
| Ana ekran ikonu tıkla | Ana panele dön |
| Sağ üst **Çıkış Yap** | Oturumu güvenle kapat |
| Tarayıcı **F5** | Sayfayı yenile |
| Sağ tık → **Yeni sekmede aç** | Başka sekmede aç |

---

## 7. Güvenlik Kuralları

**Yapılması gerekenler:**
- ✅ Bilgisayarınızdan kalkarken **oturumu kapatın** (özellikle vardiya değişiminde)
- ✅ Parolanızı **6 ayda bir** değiştirin
- ✅ Şüpheli e-postayı IT'ye bildirin

**Yapılmaması gerekenler:**
- ❌ Parolanızı kimseye vermeyin (yönetici bile)
- ❌ Yazılı kağıda parola yazıp masaya bırakmayın
- ❌ Başka biri sistemi kullanıyorken oradan çıkmayın

---

## 8. Sorun Yaşarsanız

**Adım 1 — Kendiniz çözmeyi deneyin:**
- Sayfayı yenileyin (F5)
- Farklı bir tarayıcı deneyin
- Oturumu kapatıp yeniden girin

**Adım 2 — İlk kademe destek:**
- Modül sahibinize sorun (muhasebe için muhasebe müdürüne)
- Bu belgenin ilgili bölümüne yeniden bakın

**Adım 3 — İkinci kademe:**
- IT sorumlusunu arayın: [TELEFON]
- E-posta ile bildirim gönderin: [MAIL]
- Ekran görüntüsü hatayla birlikte gönderin (sorununuzu hızlı çözer)

---

## 9. Sonraki Adım

Kendi rolünüze uygun modül belgesini okuyun:

- Muhasebeci → `02_muhasebe.md`
- Üretim → `03_uretim.md`
- Kalite → `04_kalite.md`
- Depo → `05_stok.md` *(hazırlanıyor)*
- Satış → `06_satis.md` *(hazırlanıyor)*
