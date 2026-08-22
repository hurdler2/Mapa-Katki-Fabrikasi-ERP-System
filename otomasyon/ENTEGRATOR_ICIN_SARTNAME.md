# Entegratöre Teknik Şartname — ERP ile Tam Entegrasyon

**Proje:** SARL MAPA Algérie — Sıvı beton katkısı üretim otomasyonu
**Kapsam:** PLC + SCADA + HMI + Elektrik panoları + Entegrasyon
**ERP:** ADMIX-ERP (Django 5.1 + PostgreSQL — hazır, çalışıyor)
**Hedef:** SCADA/PLC otomasyon sistemi ile ADMIX-ERP arasında sorunsuz iki yönlü veri akışı

> **Bu belge kritiktir.** Entegratörle ilk toplantıda bu 15 maddeyi tek tek geçin ve
> yazılı taahhüt alın. Her maddeyle ilgili sözleşmede net satır olması, ilerideki
> uyuşmazlıkların %90'ını önler.

---

## ÖZET — Entegratöre 3 Cümlelik Anlatım

> ADMIX-ERP hazır ve çalışıyor. Sizin işiniz PLC + SCADA + pano + saha montajını
> yapmak ve **HTTP REST API + Modbus TCP** üzerinden veriyi karşılıklı taşımak.
> ERP tarafında "SCADA giriş kapısı" ve "reçete çıkış kapısı" hazır — sizin
> Node-RED veya WinCC/Ignition ile bu iki kapıya bağlanmanız yeterli.

---

## 1. Mimari Çizim — Sözleşmede Bulunması Gereken

```
┌──────────────────┐          ┌──────────────────┐
│ SAHA / OPERATÖR  │          │  ADMIX-ERP       │
│                  │          │  (Sizin taraf)   │
│  HMI (KTP700)    │◀────────▶│  Django REST API │
│  Kontrol odası   │          │  PostgreSQL      │
└────────┬─────────┘          └────────▲─────────┘
         │                             │
         │ Ethernet TCP/IP             │ HTTPS / JSON
         │                             │
┌────────▼─────────┐          ┌────────▼─────────┐
│  Siemens PLC     │◀────────▶│  Node-RED /      │
│  S7-1215C        │  Modbus  │  SCADA sunucusu  │
│  Batch state     │   TCP    │  (Entegratör     │
│  I/O + Historian │  port    │   sorumluluğu)   │
│                  │   502    │                  │
└────────┬─────────┘          └──────────────────┘
         │
         │ 4-20mA / mV / DI / DO
         │
┌────────▼─────────┐
│  SAHA CİHAZLARI  │
│  Load cell × 8   │
│  pH, T, Cl       │
│  Vana × 5        │
│  Pompa × 5       │
│  Mixer VFD       │
└──────────────────┘
```

**Entegratörün teslim ettiği taraf:** SAHA + PLC + HMI + SCADA + kablolama + pano
**Bizim (ERP'nin) teslim ettiği taraf:** Django REST API + PostgreSQL + Portal UI
**Sözleşme sınırı:** Modbus TCP register haritası + REST endpoint şartnamesi

---

## 2. On Beş Kritik Madde — Toplantıda Sorulacaklar

### 2.1 Ağ Mimarisi ve VLAN Ayrımı

**Sorulacak:**
- Kaç VLAN kurulacak? (Öneri: 3 — Saha/PLC, SCADA, Ofis/ERP)
- ERP sunucusu hangi VLAN'de olacak? (Öneri: ofis VLAN'ında, firewall arkasında)
- SCADA sunucusu ile ERP sunucusu arasındaki route nasıl açılacak?
- Firewall kuralları kim yazacak?

**Bekleniyor:**
- Yazılı ağ topoloji şeması (Visio/Draw.io)
- IP adresleme planı
- VLAN → VLAN erişim matrisi

**Sözleşmede olması gerek:**
> "Entegratör; SCADA VLAN'ından ERP sunucusuna TCP/443 (HTTPS) ve TCP/5432
> (PostgreSQL) portlarında erişim açılmasını sağlayacak firewall kurallarını
> yazılı olarak belgeler."

### 2.2 Modbus TCP Register Haritası

**Sorulacak:**
- PLC'de Modbus TCP Server aktif edilecek mi? (Zorunlu — cevap EVET olmalı)
- Register haritası hangi belgede yazılı olacak?
- Hangi register READ ONLY, hangi READ/WRITE?
- Float değerler için byte order (Big-endian mı, Little-endian mı)?

**Vermeniz gereken:**
- Bu proje için `otomasyon/scada/README.md` dosyasındaki tam Modbus adres haritası
- Bu haritanın **imzalı sözleşme eki** olarak eklenmesi

### 2.3 REST API — SCADA'dan ERP'ye Yazım

**ERP tarafında zaten hazır endpoint (Entegratöre bu bilgi verilir):**

```
URL:      POST /api/v1/production/batches/from-scada/
Method:   POST
Auth:     Token <token> (ERP tarafından verilir)
Content:  application/json

Payload:  batch_number, recipe_code, target_kg, actual_kg,
          started_at, completed_at, consumptions[], qc_results[]

Response: 201 Created + {batch_id, batch_number, message}
```

**Detay şartname:** `otomasyon/scada/README.md` § "ADMIX-ERP Entegrasyonu"

**Sözleşmede olması gerek:**
> "Entegratör; her tamamlanan batch için bu endpoint'e POST atmayı sağlar.
> Cevap 201 değilse yerel bir kuyrukta 24 saat saklayıp tekrar dener
> (offline resilience)."

### 2.4 Reçete Gönderim — ERP'den PLC'ye

**Sorulacak:**
- ERP'de tanımlanan reçete PLC'ye nasıl inecek?
- Manuel (operatör HMI'den yükler) mi yoksa otomatik (POST edildiğinde çeker) mi?

**Öneri:** Otomatik + manuel karışık
- ERP'de operatör "Şu reçeteyi hatta gönder" der
- ERP → Node-RED / SCADA → PLC Modbus Write (holding register 40100+)
- PLC HMI'de "Yeni reçete geldi, onayla" uyarısı çıkar

**Sözleşmede olması gerek:**
> "Entegratör; ERP'nin gönderdiği reçete verisini PLC Modbus register
> 40100-40200 aralığına yazacak Node-RED flow'unu teslim eder."

### 2.5 Kimlik Doğrulama

**ERP tarafından sağlanan:**
- Node-RED / SCADA için özel bir Django user (`username=scada_bridge`)
- Token authentication (`rest_framework.authtoken`)
- IP whitelist (sadece SCADA sunucusundan gelen istekler kabul edilir)

**Entegratöre söylenecek:**
- Node-RED tarafında token güvenli saklanmalı (`credentials` config)
- Token 6 ayda bir rotate edilecek — otomatik güncelleme prosedürü sözleşmede

### 2.6 Zaman Senkronizasyonu (NTP)

**Sorulacak:**
- Tüm sistemler aynı NTP sunucusundan zaman alacak mı?
- Fabrikada yerel NTP sunucu kurulacak mı yoksa cezayir.pool.ntp.org gibi harici mi?

**Öneri:** Fabrikada yerel NTP (ERP sunucusu üzerine `chrony`) — internet koparsa bile PLC/SCADA/ERP saatleri sync kalır.

**Sözleşmede olması gerek:**
> "Tüm PLC, HMI, SCADA sunucu ve ADMIX-ERP sunucusu ortak NTP kaynağı
> kullanacaktır. Zaman farkı ≤ 100 ms olmalıdır."

**Neden kritik:** Batch başlangıç/bitiş zamanları uyuşmazsa `MaterialConsumption`
kayıtları yanlış sıralanır.

### 2.7 Historian — Time-Series Veri Nereye

**Sorulacak:**
- Load cell/pH/T verilerini kim saklayacak? (SCADA lokal DB mi, ERP DB mi?)
- Örnekleme sıklığı? (Öneri: 1 sn PLC, 5 sn SCADA, 1 dk ERP historian)
- Ne kadar geriye tutulacak? (Öneri: PLC 1 saat, SCADA 30 gün, ERP 5 yıl)

**Öneri:** Katmanlı historian
- PLC: son 1 saat (RAM buffer)
- SCADA: son 30 gün (Node-RED → PostgreSQL scada_historian tablosu)
- ERP: özet + kritik olaylar (batch record, alarm, QC — sonsuza kadar)

### 2.8 Alarm İletimi

**Sorulacak:**
- SCADA alarmları ERP'ye gelecek mi? (Öneri: SADECE kritik ve batch-bağlı olanlar)
- E-posta/SMS bildirimi kim gönderir?
- Alarm log iki tarafta da tutulacak mı?

**Karar:**
- SCADA: tüm alarmlar (INFO/WARN/CRITICAL) yerel Node-RED historian'a
- ERP: sadece batch-etkileyen alarmlar (`NonConformance` kaydı olarak)
- E-posta: SCADA gönderir, ERP kopyasını alır

### 2.9 Kalite Verisi — SCADA vs. Manuel Giriş

**Sorulacak:**
- pH, sıcaklık, klor sensörleri **her batch'te ölçüm mü** verecek?
- Yoksa laboratuvarda manuel ölçüm mü yapılacak?

**Karar (öneri):** Hibrit
- Her batch tamamlandığında SCADA otomatik değerleri ERP'ye POST eder
- QA operatörü labda ek testleri (viskozite, katı %) manuel girer
- ADMIX-ERP `QCTestResult.tester` alanında ayrım yapılır: "SCADA-AUTO" veya kullanıcı adı

### 2.10 Batch Record (Belge Çıktısı)

**Sorulacak:**
- Batch record PDF'ini kim üretir? (SCADA mı, ERP mi?)
- İçeriği neler olacak?

**Karar:** ERP üretir
- ADMIX-ERP zaten `render_coa_pdf` fonksiyonu var
- SCADA sadece veri POST eder, ERP standart formatta PDF üretir
- Cezayir yasal uyumlu (SCF, EN 934-2 referansları) format kullanılır

**Sözleşmede olması gerek:**
> "SCADA sistemi batch record PDF'i üretmez. Bu görev ADMIX-ERP tarafındadır.
> Entegratör yalnızca ham veriyi ERP'ye ileterek batch record altyapısını
> besler."

### 2.11 Kullanıcı Yetkisi ve Operatör Aksiyonu

**Sorulacak:**
- Operatör SCADA HMI'de kim olarak login olur?
- ERP'ye yazılan batch'te "operator" alanı nereden gelir?

**Karar:**
- SCADA HMI'de operatör kendi kartı ile login olur (opsiyonel — MVP'de sabit isim)
- SCADA batch POST'unda `"operator": "Mohamed Belaidi"` gibi bilgi eklenir
- ERP'de ProductionBatch.operator alanına yazılır

### 2.12 Failsafe — Ağ Kesintisi Olursa

**Sorulacak:**
- ERP sunucusu çökerse SCADA çalışmaya devam eder mi? (EVET olmalı)
- ERP'ye POST başarısız olursa veri nerede birikir?

**Zorunlu şartname:**
> "SCADA sistemi ERP bağlantı kaybında **24 saat** boyunca yerel kuyrukta
> batch verilerini saklar. Bağlantı geri geldiğinde kronolojik sırayla POST
> eder. Kuyruk dolarsa (24 sa+) operatöre HMI üzerinden uyarı verilir."

### 2.13 Test Senaryoları — FAT ve SAT

**Entegratörle yazılı test protokolü hazırlanacak. En az bu senaryolar:**

| # | Senaryo | Beklenen |
|---|---------|----------|
| 1 | Batch tam çevrim (idle→complete) | ERP'de ProductionBatch oluşur, tüm consumptions eklenir |
| 2 | ERP kapalıyken batch | SCADA kuyruğa alır, ERP açılınca POST |
| 3 | Reçete gönderimi (ERP→PLC) | HMI'de yeni reçete görünür |
| 4 | E-Stop basma | Tüm çıkışlar kapanır, HMI kırmızı |
| 5 | Load cell arıza simülasyonu | Fault bit + alarm + ERP'de NCR kaydı |
| 6 | Ağ kesintisi 5 dk | Kuyruk çalışıyor, sonra sync |
| 7 | Aynı batch iki kez POST | ERP idempotent, 200 warning döner |
| 8 | Yanlış token | ERP 401 döner, SCADA kuyruğa alır |

**Sözleşmede olması gerek:**
> "FAT (Factory Acceptance Test) ve SAT (Site Acceptance Test) protokolleri
> yazılı olarak imzalanacak. Yukarıdaki 8 senaryonun tamamı geçmediği sürece
> nihai kabul yapılmaz."

### 2.14 Dokümantasyon Teslimatı

**Entegratörden alınması zorunlu belgeler:**

| # | Belge | Format |
|---|-------|--------|
| 1 | P&ID as-built | AutoCAD DWG + PDF |
| 2 | Elektrik şeması as-built | EPLAN + PDF |
| 3 | Pano imalat resimleri | PDF |
| 4 | Kablo listesi | Excel |
| 5 | I/O listesi son hali | Excel |
| 6 | PLC programı kaynak kodu | TIA Portal proje dosyası + PDF export |
| 7 | HMI proje dosyası | WinCC/KTP proje |
| 8 | SCADA Node-RED flow.json | JSON |
| 9 | Modbus register haritası | Excel |
| 10 | Alarm listesi (tam) | Excel |
| 11 | Sensör kalibrasyon sertifikaları | PDF |
| 12 | O&M manuel (operasyon + bakım) | Türkçe + Fransızca PDF |
| 13 | FAT test raporu | Kırmızı Nokta imzalı |
| 14 | SAT test raporu | Kırmızı Nokta imzalı |
| 15 | Devreye alma yetki belgesi | Notified Body onaylı |

**Sözleşmede olması gerek:**
> "Yukarıdaki 15 belge, ödeme son taksitinden ÖNCE teslim edilir. Kaynak
> kodları (PLC + HMI + SCADA) tam ve açık (parola yok) olarak teslim edilir.
> Müşteri bu kaynaklar üzerinde ileride değişiklik yapabilir."

### 2.15 Sonraki Yıllarda Kim Değişiklik Yapabilir

**Sorulacak:**
- Kaynak kod bize teslim edilecek mi? (EVET zorunlu)
- Şifreli/kilitli bir yazılım kısmı var mı? (OLMAYACAK — sözleşmeye eklenmeli)
- Entegratör ile bağı kestikten sonra biz bakım yapabilir miyiz?

**Zorunlu şartname:**
> "PLC ve HMI programları müşteri erişimine açık teslim edilir. Şifreli
> bloklar, encapsulated FB'ler, kısıtlı erişim bulunmayacaktır. Müşterinin
> kendi mühendisleri veya seçtiği başka bir servis sağlayıcı, ileride bakım
> ve modifikasyon yapabilir."

---

## 3. Sözleşme Ödemesi — Kilometre Taşları

Ödemenin teknik teslimatlara bağlanması çok önemlidir. Öneri:

| Aşama | Ödeme % | Şart |
|-------|---------|------|
| Sipariş + mühendislik | 25 % | Şartname + P&ID imzalı |
| Ekipman teslimi | 25 % | Ürünler saha depoya girdi |
| Pano imalat + montaj | 20 % | Pano IEC 61439 testi geçti |
| FAT (fabrika testi) | 15 % | 8 senaryonun tamamı geçti + yazılı rapor |
| SAT (saha testi) + eğitim | 10 % | Test üretimi + operatör eğitimi tamam |
| Nihai kabul + garanti | 5 % | 30 gün başarılı üretim + dokümantasyon teslim |

---

## 4. Garanti + Bakım Sözleşmesi

- **Garanti süresi:** En az 24 ay (Cezayir standardı)
- **Yerinde müdahale süresi:** 24 saat (garanti içi)
- **Uzaktan destek:** VPN üzerinden 4 saat
- **Yıllık bakım opsiyonu:** 4 preventive ziyaret + acil çağrı desteği
- **Yedek parça garantisi:** 10 yıl (Siemens standart)

---

## 5. Kırmızı Çizgiler — Kabul Edilmemesi Gereken Şeyler

Aşağıdakiler entegratör önerse bile REDDET:

❌ **"Kaynak kodu bizde kalır"** — Bu kabul edilemez. Kod SIZE aittir.
❌ **"Bakım için bize aylık ödeme yapmalısınız"** — Bakım opsiyonel olmalı.
❌ **"ERP entegrasyonu bizim işimiz değil"** — Sözleşmede bu var olmalı.
❌ **"Yıllık lisans yenileme"** — Perpetual (sonsuz) lisans olmalı (Ignition zaten böyle).
❌ **"Uzaktan bağlantı için kalıcı VPN veriyoruz"** — Sadece talep üzerine.
❌ **"Alarm sınırlarını biz belirleriz"** — Operatör sizin, karar sizin.
❌ **"HMI'de sabit reçete olur"** — Reçete ERP'den gelmeli, dinamik.

---

## 6. Yeşil Işıklar — Bu Öneriler Gelirse "İYİ"

✅ **"Kaynak kodu tam açık teslim ediyoruz"**
✅ **"Modbus TCP haritasını Excel olarak veriyoruz"**
✅ **"ERP endpoint'inize test için mock veri gönderelim"** (entegrasyon konusunda deneyimli)
✅ **"Siemens Cezayir onaylı entegratörüz"** (yerel destek)
✅ **"FAT'te ERP mühendisiniz de olsun"** (şeffaflık)
✅ **"Node-RED yerine önerdiğiniz stack'i tercih edelim"** (esneklik)

---

## 7. İlk Toplantı Kontrol Listesi

Entegratörle ilk oturuma bu belgeyle gidin. Yanınızda olsun:

- [ ] Bu şartname belgesi (yazdırılmış)
- [ ] `otomasyon/docs/01_IO_listesi.md` — I/O envanteri
- [ ] `otomasyon/docs/02_pid_ve_sekans.md` — Proses akışı
- [ ] `otomasyon/scada/README.md` — Modbus register haritası
- [ ] ADMIX-ERP demo hesabı — canlı gösterim için
- [ ] `otomasyon/plc/src/` klasörü — PLC iskelet kodları (referans olarak paylaşabilirsiniz)

**Toplantıda gündem:**
1. Ürün + kapasite açıklaması (5 dk)
2. ADMIX-ERP canlı demo (10 dk) — özellikle SCADA endpoint kısmı
3. Bu 15 maddenin tek tek gözden geçirilmesi (60 dk)
4. Entegratörün karşı önerileri (30 dk)
5. Sözleşme taslak takvimi (15 dk)

Toplam: **~2 saat**

---

## 8. Referans Sorular

Entegratöre başka müşterilerinden referans isteyin:

- "Cezayir'de son 3 yılda tamamladığınız 3 benzer proje?"
- "Siemens sertifikanız hangi seviyede? (Certified Solution Partner mi?)"
- "Reference visit yapabilir miyim?" (Chryso, BASF veya benzer tesise)
- "ERP entegrasyonlu bir projeniz oldu mu? Kaç yıllık deneyim?"

---

## 9. Cezayir'de Önerilen Entegratörler (2026)

Bu isimler internet araştırmasından — kendiniz teyit edin:

| Firma | Şehir | Uzmanlık | Not |
|-------|-------|----------|-----|
| SIA (Société d'Ingénierie & Automatisation) | Alger | Siemens SP | Kimyasal deneyimi var |
| ETB (Entreprise Technologies du Bâtiment) | Alger | Siemens + Schneider | Cimenterie deneyimi |
| ENIE Automation | Sidi Bel Abbès | ABB + Siemens | Devlet iş ortağı |
| CONDOR Electronics | Bordj Bou Arreridj | Yerli üretici | Küçük ölçek |
| Sonelgaz Industrie Services | Alger | Enerji ağırlıklı | Büyük ölçek |

Öneri: **3 firmadan teklif al, 2 farklı yaklaşım karşılaştır.**

---

## 10. Son Söz

**Bu belge sözleşme değil, sözleşmenin teknik ekidir.** Avukatınız asıl sözleşmeyi
Cezayir Ticaret Hukuku'na göre yazacak; siz de teknik ek olarak bu belgeyi
imzalattıracaksınız.

**Entegratör bu belgenin herhangi bir maddesini "yapamayız/yapmayız" diyorsa,
sebebini yazılı olarak isteyin.** Her ret satırının bir alternatif teklifi olmalı.

Belgede geçen tüm şartlar teknik olarak **standart** — Sika, BASF, Chryso Cezayir
tesislerinde de böyle çalışılıyor. Zorlaştırmıyorsunuz, sadece **kendinize ait ne
alacağınızı netleştiriyorsunuz.**

---

**Belge sürümü:** 1.0
**Tarih:** 22 Ağustos 2026
**Hazırlayan:** Claude + SARL MAPA Algérie
**Kime:** Otomasyon entegratör firması (imza için)
