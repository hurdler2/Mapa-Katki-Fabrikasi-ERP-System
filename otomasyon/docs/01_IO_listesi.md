# I/O Listesi — MAPA Katkı Dozaj Hattı

**Proje:** SARL MAPA Algérie — Sıvı beton katkısı dozaj/karışım hattı
**Kapasite:** 20 ton/gün · 3 vardiya
**PLC:** Siemens S7-1215C DC/DC/DC + genişleme modülleri
**HMI:** KTP700 Basic 7"
**SCADA:** Node-RED Dashboard (web)

---

## 1. Tag Adlandırma Standardı (ISA-5.1 + KKS bileşik)

Format: **`<Tip>_<Konum>_<İşlev>_<Sıra>`**

| Ön ek | Anlam | Örnek |
|-------|-------|-------|
| `WT` | Weight (tartım) | `WT_R01_MAIN` |
| `AT` | Analytical Transmitter (pH, klor) | `AT_R01_PH` |
| `TT` | Temperature Transmitter | `TT_R01_TEMP` |
| `LT` | Level Transmitter | — |
| `FV` | Flow control Valve (solenoid) | `FV_T01_INLET` |
| `PP` | Pump (dozaj) | `PP_T01_DOSE` |
| `MX` | Mixer motor | `MX_R01_MAIN` |
| `HS` | Hand Switch (buton) | `HS_PANEL_ESTOP` |
| `XS` | Xtra Sensor (limit, prox) | `XS_R01_LOWLVL` |
| `YA` | Alarm output (lamp/buzzer) | `YA_PANEL_HIGH` |

**Konum kodları:**
- `R01` — Reaktör 1 (ana reaktör)
- `T01`–`T05` — Hammadde tankları 1-5
- `T06` — Su tankı
- `PANEL` — Kontrol panosu

---

## 2. Ekipman Envanteri

### 2.1 Load Cell (8 adet) — Tartım Sensörleri

| Tag | Konum | Ölçüm aralığı | Amaç |
|-----|-------|---------------|------|
| `WT_R01_MAIN` | Reaktör 1 | 0-3000 kg | Ana reaktör toplam ağırlık |
| `WT_T01_RAW` | Hammadde tankı 1 | 0-1500 kg | RM1 stok (ör. monomer A) |
| `WT_T02_RAW` | Hammadde tankı 2 | 0-1500 kg | RM2 stok (ör. monomer B) |
| `WT_T03_RAW` | Hammadde tankı 3 | 0-1500 kg | RM3 stok (ör. inisiyatör) |
| `WT_T04_RAW` | Hammadde tankı 4 | 0-1500 kg | RM4 stok (ör. zincir transfer) |
| `WT_T05_RAW` | Hammadde tankı 5 | 0-1500 kg | RM5 stok (ör. baz/asit) |
| `WT_T06_WATER` | Su tankı | 0-3000 kg | Su stok |
| `WT_PROD_OUT` | Çıkış tartısı | 0-3000 kg | Ürün doldurma kontrolü |

### 2.2 Analog Sensörler (3 adet)

| Tag | Konum | Ölçüm aralığı | Amaç |
|-----|-------|---------------|------|
| `AT_R01_PH` | Reaktör 1 | 0-14 pH | Reaksiyon pH kontrolü |
| `TT_R01_TEMP` | Reaktör 1 | 0-100 °C | Reaksiyon sıcaklığı |
| `AT_R01_CL` | Reaktör 1 / ürün | 0-5000 ppm | Klorür iyonu (EN 480-10) |

### 2.3 Solenoid Vanalar (5 adet) — Hammadde Girişleri

| Tag | Konum | Amaç |
|-----|-------|------|
| `FV_T01_INLET` | Tank 1 → Reaktör | RM1 dozajlama vanası |
| `FV_T02_INLET` | Tank 2 → Reaktör | RM2 dozajlama vanası |
| `FV_T03_INLET` | Tank 3 → Reaktör | RM3 dozajlama vanası |
| `FV_T04_INLET` | Tank 4 → Reaktör | RM4 dozajlama vanası |
| `FV_T05_INLET` | Tank 5 → Reaktör | RM5 dozajlama vanası |

### 2.4 Pompalar (5 adet)

| Tag | Konum | Tip | Amaç |
|-----|-------|-----|------|
| `PP_T01_DOSE` | Tank 1 | Diafragma (Grundfos DDA) | RM1 dozajlama |
| `PP_T02_DOSE` | Tank 2 | Diafragma | RM2 dozajlama |
| `PP_T03_DOSE` | Tank 3 | Diafragma | RM3 dozajlama |
| `PP_T04_DOSE` | Tank 4 | Diafragma | RM4 dozajlama |
| `PP_T05_DOSE` | Tank 5 | Diafragma | RM5 dozajlama |

### 2.5 Mixer

| Tag | Konum | Güç | Amaç |
|-----|-------|-----|------|
| `MX_R01_MAIN` | Reaktör 1 | 2.2 kW | Ana reaktör karıştırıcı (VFD kontrollü) |

### 2.6 Buton / Anahtar (operatör paneli)

| Tag | Fonksiyon |
|-----|-----------|
| `HS_PANEL_ESTOP` | Acil Durdurma (emniyet kilidi) |
| `HS_PANEL_START` | Batch Başlat |
| `HS_PANEL_STOP` | Batch Durdur (soft) |
| `HS_PANEL_RESET` | Alarm Reset |
| `HS_PANEL_AUTO_MAN` | Otomatik/Manuel seçici |

### 2.7 Alarm Çıkışları (panosuna lamba/kornah)

| Tag | Renk | Anlam |
|-----|------|-------|
| `YA_PANEL_RUN` | Yeşil lamba | Sistem çalışıyor |
| `YA_PANEL_ALARM` | Sarı lamba | Alarm var (uyarı) |
| `YA_PANEL_CRIT` | Kırmızı lamba + korna | Kritik alarm |

---

## 3. Toplam I/O Sayımı

| Tip | Sayı | PLC modülü |
|-----|------|-----------|
| **AI (analog input)** — RTD (PT100) | 1 | SM 1231 AI 8× RTD |
| **AI** — mV (load cell köprüsü) | 8 | SM 1231 AI 8× |
| **AI** — 4-20 mA (pH, klor) | 2 | SM 1231 AI 4× |
| **DI (digital input)** — buton, feedback | 12 | S7-1215C dahili + SM 1223 |
| **DO (digital output)** — vana, pompa, mixer, alarm | 14 | SM 1223 DI16/DQ16 |
| **AO (analog output)** — VFD referansı | 1 | Dahili PWM |
| **TOPLAM** | **~38 nokta** | |

---

## 4. PLC Adresleme Haritası

Aşağıdaki PLC hafıza adreslemesi TIA Portal projesi için başlangıç noktasıdır.
Data Block (DB) tabanlı optimize edilmiş (S7-1200 önerisi).

### 4.1 Input Adresleri (I)

| Tag | Adres | Modül |
|-----|-------|-------|
| `HS_PANEL_START` | `%I0.0` | S7-1215C dahili |
| `HS_PANEL_STOP` | `%I0.1` | dahili |
| `HS_PANEL_RESET` | `%I0.2` | dahili |
| `HS_PANEL_ESTOP` | `%I0.3` | dahili (safety) |
| `HS_PANEL_AUTO_MAN` | `%I0.4` | dahili |
| Pompa 1-5 çalışıyor geri besleme | `%I1.0` – `%I1.4` | SM 1223 |
| Mixer çalışıyor geri besleme | `%I1.5` | SM 1223 |
| Vana pozisyon geri besleme (opsiyonel) | `%I2.0` – `%I2.4` | SM 1223 |

### 4.2 Output Adresleri (Q)

| Tag | Adres | Modül |
|-----|-------|-------|
| Vana 1-5 (`FV_T01`..`FV_T05`) | `%Q0.0` – `%Q0.4` | SM 1223 |
| Pompa 1-5 (`PP_T01`..`PP_T05`) | `%Q0.5` – `%Q1.1` | SM 1223 |
| Mixer (`MX_R01_MAIN`) | `%Q1.2` | SM 1223 |
| Alarm lamba yeşil | `%Q1.3` | SM 1223 |
| Alarm lamba sarı | `%Q1.4` | SM 1223 |
| Alarm lamba kırmızı + korna | `%Q1.5` – `%Q1.6` | SM 1223 |

### 4.3 Analog Adresleri (PIW/PQW)

| Tag | Adres | Modül |
|-----|-------|-------|
| Load cell 1-8 | `%IW96` – `%IW110` | SM 1231 AI 8× (mV) |
| PT100 sıcaklık | `%IW112` | SM 1231 AI 8× RTD |
| pH sensörü (4-20 mA) | `%IW114` | SM 1231 AI 4× |
| Klor sensörü (4-20 mA) | `%IW116` | SM 1231 AI 4× |
| VFD referans (mixer hız) | `%QW96` | Dahili PWM |

---

## 5. Alarm Sınırları (İlk taslak — devreye almada tune edilir)

| Tag | LL | L | H | HH | Birim |
|-----|-----|---|---|-----|-------|
| `WT_R01_MAIN` | 50 | 100 | 2800 | 2950 | kg |
| `AT_R01_PH` | 3.5 | 4.5 | 7.0 | 8.0 | pH |
| `TT_R01_TEMP` | 5 | 15 | 45 | 60 | °C |
| `AT_R01_CL` | — | — | 800 | 1000 | ppm |
| Tank RM 1-5 | 30 | 100 | — | — | kg (düşük stok) |

- `LL` = Low Low (kritik alarm)
- `L` = Low (uyarı)
- `H` = High (uyarı)
- `HH` = High High (kritik alarm)

---

## 6. Sonraki Adım

Bu doküman **P&ID + sekans diyagramına** temel olur. Bir sonraki adımda:
1. Fiziksel akış diyagramı (`docs/02_pid_ve_sekans.md`)
2. Batch adımlarının Mermaid state diagramı
3. Reçete veri modeli (DB yapısı)
