# SARL MAPA ALGÉRIE — Otomasyon + Sunucu Odası Maliyet Analizi

**Tarih:** 22 Ağustos 2026
**Kapsam:** Sıvı beton katkısı fabrikası için PLC/SCADA/HMI + sunucu odası + ERP altyapı + elektrik panosu
**Kur varsayımı:** 1 EUR ≈ 145 DZD (2026 ortalama)
**Fabrika profili varsayımı:**
- 4-6 reaktör (500-2000 L)
- 15-25 motor (pompa, karıştırıcı, konveyör, vana)
- IBC/tanker dolum hattı
- 300-500 I/O noktası
- 500-1000 SCADA tag
- 20 ERP kullanıcı (3 vardiya)

---

## 1. PANO TARAFI — Elektrik + Kontrol

### 1.1 Ana Elektrik Panosu + Baralar
| Kalem | Marka önerisi | Tutar (EUR) |
|---|---|---|
| Ana giriş kesici (630-1000A) | ABB Emax / Schneider Masterpact | 2,500 – 4,000 |
| Ana baralar + dağıtım | Rittal | 1,500 – 2,500 |
| SPD (yıldırım koruma) | Dehn / Phoenix Contact | 800 – 1,500 |
| Topraklama sistemi | — | 500 – 1,000 |
| **Alt toplam** | | **5,300 – 9,000** |

### 1.2 Motor Control Center (MCC)
| Kalem | Marka önerisi | Tutar (EUR) |
|---|---|---|
| MCC kabini (form 3b/4b, 15-20 çekmece) | Schneider Model 6 iMCC / ABB MNS | 12,000 – 20,000 |
| VFD sürücüler (× 8, çeşitli boyut) | ABB ACS580 / Siemens G120 | 6,000 – 10,000 |
| Soft-starter (× 5) | Schneider ATS22 | 2,500 – 4,000 |
| Kontaktörler + termik röleler | Schneider / Siemens | 2,000 – 3,500 |
| Kablo, klemens, işaretleme | — | 2,000 – 3,000 |
| **Alt toplam** | | **24,500 – 40,500** |

### 1.3 Kontrol Panosu (PLC + I/O muhafazası)
| Kalem | Marka önerisi | Tutar (EUR) |
|---|---|---|
| Rittal AX/TS8 kabinler × 3 (IP54) | Rittal | 2,500 – 4,000 |
| İç düzenleme + DIN ray + kanal | — | 1,000 – 1,500 |
| 24VDC güç kaynakları (yedekli) | Phoenix Contact QUINT | 800 – 1,500 |
| Kablo + klemens + etiketleme | — | 1,500 – 2,500 |
| **Alt toplam** | | **5,800 – 9,500** |

### **PANO TOPLAMI: €35,600 – €59,000**

---

## 2. PLC + I/O

| Kalem | Model | Adet | Birim (EUR) | Tutar (EUR) |
|---|---|---|---|---|
| Ana CPU | Siemens S7-1516F PN/DP (safety) | 1 | 6,600 – 6,800 | 6,600 – 6,800 |
| Yedek CPU | Siemens S7-1513 PN | 1 | 1,870 – 2,220 | 1,870 – 2,220 |
| Dağıtık I/O IM155-6 PN | ET 200SP | 6 | 400 – 600 | 2,400 – 3,600 |
| Dijital giriş 16DI (× 15) | ET 200SP DI 16×24VDC | 15 | 250 – 350 | 3,750 – 5,250 |
| Dijital çıkış 16DO (× 12) | ET 200SP DQ 16×24VDC | 12 | 280 – 380 | 3,360 – 4,560 |
| Analog giriş AI 8× | ET 200SP AI 8×U/I HF | 8 | 400 – 550 | 3,200 – 4,400 |
| Analog çıkış AQ 4× | ET 200SP AQ 4×U/I | 4 | 350 – 500 | 1,400 – 2,000 |
| Güvenlik modülleri | Safety I/O | 4 | 500 – 800 | 2,000 – 3,200 |
| TIA Portal V19 Professional | Siemens yazılım | 1 | 2,500 – 4,000 | 2,500 – 4,000 |
| STEP 7 Safety Advanced | Siemens | 1 | 1,500 – 2,500 | 1,500 – 2,500 |
| **PLC TOPLAM** | | | | **28,580 – 38,530** |

**Ekonomik alternatif:** Delta AH500 + ISPSoft — %40 daha ucuz (€17,000-24,000) ancak destek/entegrasyon Cezayir'de daha zor.

---

## 3. HMI OPERATÖR EKRANLARI

| Kalem | Model | Adet | Birim (EUR) | Tutar (EUR) |
|---|---|---|---|---|
| Baş operatör (kontrol odası) | Siemens TP1900 Comfort 19" | 1 | 3,500 – 4,500 | 3,500 – 4,500 |
| Vardiya operatörü (üretim) | Siemens KTP1200 Comfort 12" | 2 | 1,800 – 2,300 | 3,600 – 4,600 |
| Laboratuvar operatörü | Siemens KTP900 Comfort 9" | 1 | 1,400 – 1,800 | 1,400 – 1,800 |
| Mobil el terminali | Siemens KTP700 Basic 7" + kablo | 1 | 700 – 1,000 | 700 – 1,000 |
| Ethernet kablolama + PROFINET switch | Hirschmann / Scalance | — | 800 – 1,200 | 800 – 1,200 |
| **HMI TOPLAM** | | | | **10,000 – 13,100** |

---

## 4. SCADA YAZILIMI

**Önerilen: Inductive Automation Ignition (unlimited tag/client, modern web mimarisi)**

| Kalem | Tutar (EUR) |
|---|---|
| Ignition Gateway (unlimited) | 3,290 – 3,500 |
| Vision Client modülü | 800 – 1,000 |
| Perspective (mobil/web) modülü | 1,200 – 1,500 |
| SQL Bridge + Reporting modülü | 1,500 – 2,500 |
| MQTT Engine (SCADA-ERP entegrasyonu) | 1,500 – 2,000 |
| Alarm Notification (SMS/email) | 800 – 1,500 |
| Yıllık bakım + destek | 1,500 – 2,500 |
| **SCADA TOPLAM (Ignition)** | **10,590 – 14,500** |

**Alternatifler:**
| Platform | Tag başına maliyet | 500-1000 tag için toplam |
|---|---|---|
| Siemens WinCC Runtime Advanced (1500 tag) | Tag başı ~€8-15 | €12,000 – 22,000 |
| AVEVA InTouch + System Platform | Yüksek başlangıç + client | €35,000 – 80,000 |
| Ignition (unlimited) | Sabit lisans | €10,590 – 14,500 |

**Öneri:** Ignition — orta ölçek kimyasal katkı fabrikası için en iyi maliyet/özellik dengesi.

---

## 5. SAHA CİHAZLARI (Sensör + Aktüatör)

| Kalem | Marka önerisi | Adet | Birim (EUR) | Tutar (EUR) |
|---|---|---|---|---|
| Sıcaklık sensörü PT100 4-tel | Endress+Hauser TR13 | 20 | 150 – 200 | 3,000 – 4,000 |
| Basınç transmitteri 4-20 mA | E+H Cerabar / Siemens SITRANS P | 10 | 400 – 600 | 4,000 – 6,000 |
| Seviye ölçüm (radar) | E+H Micropilot FMR20 | 4 | 1,500 – 2,200 | 6,000 – 8,800 |
| Seviye ölçüm (ultrasonik) | Siemens SITRANS LU | 2 | 800 – 1,200 | 1,600 – 2,400 |
| Debi ölçer Coriolis | E+H Promass F | 2 | 4,500 – 6,500 | 9,000 – 13,000 |
| Debi ölçer manyetik | E+H Promag P | 2 | 1,500 – 2,500 | 3,000 – 5,000 |
| Yük hücreleri + gösterge | Mettler Toledo IND570 | 6 | 800 – 1,200 | 4,800 – 7,200 |
| pH + iletkenlik probu | E+H Liquiline | 2 | 1,000 – 1,500 | 2,000 – 3,000 |
| Otomatik vana pnömatik + aktüatör | Bürkert / Georg Fischer | 20 | 400 – 700 | 8,000 – 14,000 |
| Solenoid ventil + basınç düzenleyici | Festo | 15 | 100 – 200 | 1,500 – 3,000 |
| Emniyet valfi + acil durdurma butonları | — | — | 1,500 – 2,500 | 1,500 – 2,500 |
| **SAHA CİHAZ TOPLAMI** | | | | **44,400 – 68,900** |

---

## 6. SUNUCU ODASI (Server Room)

### 6.1 Fiziki altyapı
| Kalem | Model önerisi | Tutar (EUR) |
|---|---|---|
| 42U rack × 2 (siyah, ön/arka cam kapı) | APC NetShelter SX | 1,200 – 1,600 |
| PDU (yönetilebilir, dual feed) | APC AP8681 × 4 | 1,200 – 1,800 |
| Yükseltilmiş döşeme (18 m²) | — | 2,500 – 4,000 |
| Duvar/tavan alçı + panel + izolasyon | — | 1,500 – 2,500 |
| Yangın algılama + FM200 gaz | Bosch / Honeywell | 4,000 – 8,000 |
| Yangın kapısı EI-60 | — | 800 – 1,500 |
| Kartlı erişim + kamera IP × 2 | Hikvision / Axis | 1,500 – 3,000 |
| Sıcaklık/nem izleme | APC NetBotz | 800 – 1,500 |
| **6.1 Alt toplam** | | **13,500 – 23,900** |

### 6.2 Güç (UPS + Enerji)
| Kalem | Tutar (EUR) |
|---|---|
| UPS Online 10-15 kVA (2+1 redundant) — APC Smart-UPS SRT | 4,500 – 7,500 |
| Yedek akü paketi (ek 15-30 dk) | 1,500 – 3,000 |
| Otomatik transfer şalter (ATS) | 800 – 1,500 |
| Jeneratör bağlantısı (opsiyonel, sunucu odası için mini 20 kVA) | 8,000 – 15,000 |
| **6.2 Alt toplam (jeneratör dahil)** | **14,800 – 27,000** |

### 6.3 Soğutma
| Kalem | Tutar (EUR) |
|---|---|
| Klima — In-row veya split 5 kW (2+1 redundant) | 3,500 – 6,500 |
| Kanal + tesisat | 1,000 – 2,000 |
| Sıcak/soğuk koridor kapatma | 1,500 – 3,000 |
| **6.3 Alt toplam** | **6,000 – 11,500** |

### 6.4 Sunucular
| Kalem | Model önerisi | Tutar (EUR) |
|---|---|---|
| SCADA sunucu (Ignition + Historian) | Dell R650 · 2× Xeon Gold · 128 GB · 4× SSD | 5,500 – 7,500 |
| ERP sunucu (Django + PostgreSQL) | Dell R650 · 2× Xeon Gold · 128 GB · 4× NVMe | 5,500 – 7,500 |
| Domain controller / dosya sunucu | Dell R450 · 64 GB | 3,500 – 5,000 |
| Yedek/DR sunucu (soğuk yedek) | Dell R450 · 64 GB | 3,000 – 4,500 |
| NAS 40TB (yedekleme) | Synology RS3621 + diskler | 4,000 – 6,000 |
| **6.4 Alt toplam** | | **21,500 – 30,500** |

### **SUNUCU ODASI TOPLAMI: €55,800 – €92,900**

---

## 7. AĞ ALTYAPISI

| Kalem | Model önerisi | Adet | Tutar (EUR) |
|---|---|---|---|
| Endüstriyel L3 switch (SCADA VLAN) | Hirschmann RSP35 / Cisco IE-4000 | 2 | 3,500 – 5,000 |
| Endüstriyel L2 switch (saha) | Ruggedcom RSG2100 | 3 | 2,400 – 3,600 |
| Ofis switch L2/L3 (24-port PoE+) | HPE Aruba 2530 | 3 | 2,000 – 3,500 |
| Firewall (UTM) | Fortinet FortiGate 100F | 1 (+HA) | 2,500 – 4,500 |
| WiFi 6 access point | Aruba AP-515 / Cisco Meraki | 8 | 2,400 – 3,600 |
| Fiber patch panel + patch cord | — | — | 1,500 – 3,000 |
| CAT6 kablolama + prize (fabrika + ofis, 60 nokta) | — | — | 3,000 – 5,000 |
| Kabinet aksesuarları | — | — | 800 – 1,500 |
| **AĞ TOPLAMI** | | | **18,100 – 29,700** |

---

## 8. ERP + Yazılım Lisansları

| Kalem | Tutar (EUR) |
|---|---|
| Windows Server 2022 Standard × 3 | 6,000 – 7,500 |
| Windows Server CAL × 25 | 700 – 900 |
| Antivirüs endpoint (25 lisans, 3 yıl) | 800 – 1,500 |
| Backup yazılımı — Veeam Data Platform Essentials | 2,000 – 3,500 |
| Monitoring — PRTG 500 sensor | 1,000 – 2,000 |
| Ubuntu Server (SCADA/ERP host — ücretsiz) | 0 |
| PostgreSQL (ADMIX-ERP için — ücretsiz) | 0 |
| MS Office 365 Business × 25 (yıllık) | 3,600 |
| **YAZILIM TOPLAMI** | **14,100 – 19,000** |

---

## 9. MÜHENDİSLİK + Devreye Alma

| Kalem | Süre | Tutar (EUR) |
|---|---|---|
| SCADA + PLC yazılım geliştirme | 8-12 hafta | 15,000 – 30,000 |
| Sistem entegrasyonu (FAT + SAT) | 4-6 hafta | 8,000 – 15,000 |
| I/O check + loop test | 2 hafta | 4,000 – 6,000 |
| Operatör eğitimi (5 gün × 5 kişi) | — | 2,500 – 4,500 |
| Yönetici/mühendis eğitimi | — | 2,000 – 3,500 |
| P&ID + Loop diagram + as-built doküman | — | 3,000 – 5,000 |
| Fonksiyonel safety analiz (SIL2/3) | — | 3,000 – 6,000 |
| **MÜHENDİSLİK TOPLAMI** | | **37,500 – 70,000** |

---

## 10. YEDEK PARÇA + Garanti + Bakım

| Kalem | Tutar (EUR) |
|---|---|
| Kritik yedek parça (CPU + I/O modül + sensör) | 5,000 – 8,000 |
| 1 yıl garanti sonrası bakım sözleşmesi | 4,000 – 8,000 |
| SCADA versiyon güncellemeleri (yıllık) | 1,500 – 2,500 |
| **BAKIM TOPLAMI** | **10,500 – 18,500** |

---

## 📊 GENEL TOPLAM

| Modül | Alt sınır (EUR) | Üst sınır (EUR) |
|---|---|---|
| 1. Pano tarafı | 35,600 | 59,000 |
| 2. PLC + I/O | 28,580 | 38,530 |
| 3. HMI operatör ekranları | 10,000 | 13,100 |
| 4. SCADA yazılımı (Ignition) | 10,590 | 14,500 |
| 5. Saha cihazları | 44,400 | 68,900 |
| 6. Sunucu odası | 55,800 | 92,900 |
| 7. Ağ altyapısı | 18,100 | 29,700 |
| 8. Yazılım lisansları | 14,100 | 19,000 |
| 9. Mühendislik + devreye alma | 37,500 | 70,000 |
| 10. Yedek parça + bakım | 10,500 | 18,500 |
| **TOPLAM** | **€265,170** | **€424,130** |
| **TOPLAM (DZD)** | **~38,4 M DZD** | **~61,5 M DZD** |
| **ORTA SENARYO** | **€344,650** | **~50 M DZD** |

---

## 🔄 Alternatif Senaryolar

### A) Ekonomik (Türk/Çin markalar)
Delta PLC + Weintek HMI + Ignition SCADA + Huawei ağ + Dell EMC PowerEdge R450
- **Toplam: €140,000 – €200,000 (~20-29 M DZD)**
- Risk: Cezayir'de Delta/Weintek servisi kısıtlı, entegratör bulmak zor
- Avantaj: %40-50 tasarruf

### B) Orta (Siemens + Ignition — yukarıdaki plan)
- **Toplam: €265,000 – €425,000 (~38-62 M DZD)**
- Siemens çok yaygın, Cezayir'de servis kolay
- Ignition SCADA modern, unlimited license

### C) Premium (DCS: Emerson DeltaV veya Yokogawa Centum)
- Foundation Fieldbus altyapısı
- Yerleşik reçete/parti yönetimi (Batch Manager)
- 3 yıllık ISO 62443 sertifikası
- **Toplam: €600,000 – €1,200,000 (~87-174 M DZD)**
- Genellikle petrokimya/rafineri için — sıvı katkı için abartılı

---

## 🎯 Önerilen Yol (Cezayir bağlamı)

**Senaryo B (Siemens + Ignition) — ~€350,000 (50 M DZD)**

Gerekçe:
1. **Siemens Cezayir**: Siemens'in Alger ofisi + yerel entegratör partneri (SIA, ETB) var, saha desteği kolay
2. **Chryso/BASF referansı**: Bu üreticiler de Cezayir tesislerinde Siemens S7-1500 + WinCC/Ignition kullanıyor
3. **Yedek parça stoku**: TIA Portal + S7-1500 komponentleri Alger'de 48 saatte tedarik edilebilir
4. **Ignition unlimited license**: Sonradan tag/client eklerken ekstra ücret yok
5. **Operatör eğitimi**: Cezayir üniversitelerinde Siemens PLC eğitimi standart (INELEC, USTHB)

---

## 📅 Uygulama Takvimi (Senaryo B)

| Ay | Aktivite |
|---|---|
| **1-2** | Detay mühendislik + saha ölçüm + P&ID revizyonu |
| **3** | Sipariş verme (Siemens 12-14 hafta teslim süresi) |
| **4-5** | Sunucu odası inşa + pano imalatı |
| **6** | Saha cihaz montajı |
| **7** | PLC/SCADA yazılım geliştirme + FAT (fabrika kabul testi) |
| **8** | Kablolama + I/O check |
| **9** | Devreye alma + SAT (saha kabul testi) |
| **10** | Personel eğitimi + belgeleme |
| **11** | Deneme üretimi + fine-tuning |
| **12** | Full üretim + garanti başlangıcı |

---

## 💰 Toplam Sahip Olma Maliyeti (5-yıl TCO)

| Kalem | Yıl 0 | Yıl 1-5 (5×) | Toplam 5 yıl |
|---|---|---|---|
| Ana yatırım | €344,650 | — | €344,650 |
| Bakım sözleşmesi | — | €6,000/yıl | €30,000 |
| Yazılım güncelleme | — | €2,000/yıl | €10,000 |
| Elektrik + soğutma | — | €5,000/yıl | €25,000 |
| Yedek parça yenileme | — | €3,000/yıl | €15,000 |
| İnternet + destek | — | €2,500/yıl | €12,500 |
| **5-yıl TCO** | | | **€437,150 (~63 M DZD)** |

Yıllık ortalama ~€87,400 (~12,7 M DZD).

---

## ⚠ Kritik Notlar

1. **CE marking + IEC 61511 (safety)** için ek €15,000-25,000 sertifikasyon danışmanlığı bütçelenmeli
2. **ATEX bölge sınıflandırması** varsa (çözücü/alkol depolama), Ex-proof sensör/pano ek maliyet +30-50%
3. **Cezayir gümrük vergisi**: Elektronik ekipmanda %5-15 + KDV %19 → yaklaşık **%25-35 ek maliyet**
4. **Cezayir'de FOB alım yerine CIF alım tercih edilmeli** (nakliye + sigorta dahil)
5. **DA kur riski**: EUR/DZD dalgalanması için %10-15 kur farkı rezervi tutulmalı

**Gümrük + kur rezervi dahil gerçek Türkiye/EU'dan CIF alım maliyeti:**
- Senaryo B: ~€450,000-500,000 CIF Alger + gümrük + KDV
- **Toplam Cezayir'de teslim: ~€570,000-620,000 (~83-90 M DZD)**

---

## Kaynakça

- [Siemens S7-1500 CPU Price Guide (Alibaba Electronics)](https://electronics.alibaba.com/buyingguides/siemens-s7-1500-cpu-price-guide-what-you-actually-pay-why)
- [Top Siemens PLCs 2026 Guide (PLCverse)](https://plcverse.com/blog/top-siemens-plcs-industrial-automation-2026)
- [SCADA Software Cost Comparison 2026 (Voltrus)](https://voltrus.id/voltrus-scada/blog/scada-under-1000-dollars/)
- [Ignition vs Wonderware SCADA 2026 (OperaMetrix)](https://www.operametrix.com/en/compare/ignition-vs-aveva-wonderware/)
- [Best SCADA Software 2026 (PLCProgramming)](https://plcprogramming.io/blog/best-scada-software-2026)
- [Schneider Model 6 iMCC (Schneider Electric)](https://www.se.com/us/en/work/products/explore/model6-motor-control-center/)
- [ABB Motor Control Centers](https://electrification.us.abb.com/products/motor-control-centers-mccs)
- [ABB vs Siemens vs Schneider 2026 (Stoklink)](https://stoklink.com/blogs/news/abb-siemens-and-schneider-a-comparison-of-leading-industrial-brands)
- [Siemens SIMATIC HMI Panels](https://www.siemens.com/en-us/products/simatic-hmi/panels/)
- [Siemens KTP1200 Automation24](https://www.automation24.com/simatic-basic-panel-siemens-ktp1200-basic-pn-6av2123-2mb03-0ax0)
- [Small Server Room Design (Servermall)](https://servermall.com/blog/how-to-design-a-small-1-3-rack-server-room-power-cooling-noise-and-security/)
- [Server Room Cooling Guide 2026 (HVAC.best)](https://hvac.best/how-to-cool-a-server-room/)
