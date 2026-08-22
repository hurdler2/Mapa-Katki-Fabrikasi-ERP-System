# P&ID ve Proses Sekans — MAPA Katkı Dozaj Hattı

## 1. Fiziksel Akış Diyagramı (P&ID Basitleştirilmiş)

```mermaid
flowchart TB
    subgraph HAM["🏭 HAMMADDE TANKLARI"]
        T1[Tank 1<br/>Monomer A<br/>WT_T01<br/>0-1500 kg]
        T2[Tank 2<br/>Monomer B<br/>WT_T02<br/>0-1500 kg]
        T3[Tank 3<br/>İnisiyatör<br/>WT_T03<br/>0-1500 kg]
        T4[Tank 4<br/>Zincir transferi<br/>WT_T04<br/>0-1500 kg]
        T5[Tank 5<br/>Baz/Asit<br/>WT_T05<br/>0-1500 kg]
        T6[Su Tankı<br/>WT_T06<br/>0-3000 kg]
    end

    subgraph DOZAJ["🔧 DOZAJ HATTI"]
        FV1[FV_T01<br/>Vana]
        FV2[FV_T02<br/>Vana]
        FV3[FV_T03<br/>Vana]
        FV4[FV_T04<br/>Vana]
        FV5[FV_T05<br/>Vana]

        PP1[PP_T01<br/>Pompa]
        PP2[PP_T02<br/>Pompa]
        PP3[PP_T03<br/>Pompa]
        PP4[PP_T04<br/>Pompa]
        PP5[PP_T05<br/>Pompa]
    end

    subgraph REAKTOR["⚗️ REAKTÖR R-01"]
        R01[Ana Reaktör<br/>WT_R01_MAIN<br/>0-3000 kg]
        MX[MX_R01_MAIN<br/>Mixer 2.2 kW]
        AT_PH[AT_R01_PH<br/>0-14]
        TT[TT_R01_TEMP<br/>0-100°C]
        AT_CL[AT_R01_CL<br/>0-5000 ppm]
    end

    subgraph CIKIS["📦 ÇIKIŞ"]
        OUT[Ürün<br/>WT_PROD_OUT<br/>IBC dolum]
    end

    T1 --> FV1 --> PP1 --> R01
    T2 --> FV2 --> PP2 --> R01
    T3 --> FV3 --> PP3 --> R01
    T4 --> FV4 --> PP4 --> R01
    T5 --> FV5 --> PP5 --> R01
    T6 -- Ana besleme --> R01

    R01 --- MX
    R01 -.- AT_PH
    R01 -.- TT
    R01 -.- AT_CL

    R01 --> OUT

    style REAKTOR fill:#EEF6FF,stroke:#2B4F71,stroke-width:2px
    style HAM fill:#F5F1E8
    style CIKIS fill:#E4EDE5
```

---

## 2. Batch Sekans Durum Diyagramı

```mermaid
stateDiagram-v2
    [*] --> IDLE: Sistem hazır

    IDLE --> RECIPE_LOAD: Operatör "Batch Başlat"
    RECIPE_LOAD --> PRECHECK: Reçete yüklendi

    PRECHECK --> ABORTED: Stok yetersiz / Reaktör dolu
    PRECHECK --> WATER_FILL: OK

    WATER_FILL --> DOSE_RM1: Su tam
    DOSE_RM1 --> DOSE_RM2: Ağırlık ± tolerans
    DOSE_RM2 --> DOSE_RM3
    DOSE_RM3 --> DOSE_RM4
    DOSE_RM4 --> DOSE_RM5
    DOSE_RM5 --> MIXING

    MIXING --> QC_SAMPLE: Süre tamam
    QC_SAMPLE --> QC_PASS: pH+T+Cl OK
    QC_SAMPLE --> QC_FAIL: Sınır dışı

    QC_PASS --> DISCHARGE: Ürün onaylandı
    QC_FAIL --> HOLD: Kalite bekleme
    HOLD --> QC_SAMPLE: Ek karıştırma sonrası
    HOLD --> ABORTED: QA reddi

    DISCHARGE --> CIP_CLEAN: IBC dolum tamam
    CIP_CLEAN --> IDLE: Temizlik OK

    ABORTED --> IDLE: Operatör reset

    note right of DOSE_RM1
        Vana + pompa aç
        Hedef ağırlığa - overshoot
        Pompa kapa, vana kapa
        Ağırlık kontrolü
    end note

    note right of MIXING
        Mixer VFD %75
        Süre: reçetede tanımlı
        Sıcaklık monitör
    end note

    note right of QC_SAMPLE
        pH kontrol
        Sıcaklık kontrol
        Klorür ölçüm
        Tüm sınırlar OK mi?
    end note
```

---

## 3. Reçete Veri Yapısı

Her katkı ürünü için bir reçete = 5 hammaddenin oranı + karışım süresi + hedef kalite.

### 3.1 Reçete DB (PLC tarafı)

```
Recipe:
  code             : STRING[20]        // Ör. "ADX-100-v3"
  batch_target_kg  : REAL              // Ör. 1000.0 (batch başına)
  water_kg         : REAL              // Su miktarı
  rm1_kg           : REAL              // RM1 dozajı
  rm2_kg           : REAL              // RM2 dozajı
  rm3_kg           : REAL              // RM3 dozajı
  rm4_kg           : REAL              // RM4 dozajı
  rm5_kg           : REAL              // RM5 dozajı
  tolerance_pct    : REAL              // Ör. 0.5 (%)
  mix_time_sec     : INT               // Ör. 1800 (30 dk)
  mix_speed_pct    : INT               // Ör. 75 (VFD)
  target_ph_min    : REAL              // Ör. 4.5
  target_ph_max    : REAL              // Ör. 7.0
  target_temp_max  : REAL              // Ör. 45.0 °C
  target_cl_max    : REAL              // Ör. 800 ppm (BR-QA-05)
```

### 3.2 Örnek reçete (ADX-100 superplastifiyan)

| Alan | Değer |
|------|-------|
| `code` | `ADX-100-v3` |
| `batch_target_kg` | 1000.0 kg |
| `water_kg` | 600.0 kg |
| `rm1_kg` | 250.0 kg (Monomer A / PEG) |
| `rm2_kg` | 80.0 kg (Monomer B / Acrylic acid) |
| `rm3_kg` | 15.0 kg (İnisiyatör / Persulfat) |
| `rm4_kg` | 8.0 kg (Zincir transferi / mercaptan) |
| `rm5_kg` | 47.0 kg (NaOH nötralizasyon) |
| `tolerance_pct` | 0.5 % |
| `mix_time_sec` | 1800 sn (30 dk) |
| `mix_speed_pct` | 75 % |
| `target_ph_min` | 4.5 |
| `target_ph_max` | 7.0 |
| `target_temp_max` | 45 °C |
| `target_cl_max` | 800 ppm |

**Toplam kontrol:** 600 + 250 + 80 + 15 + 8 + 47 = 1000 kg ✓

---

## 4. Dozajlama Algoritması (İki Aşamalı — Coarse + Fine)

Endüstriyel dozajlama için standart yaklaşım:

```
Hedef ağırlık: Target = W_current + RM_dose_kg
Coarse limit:  Coarse_stop = Target - Overshoot
   Overshoot = Pompa kapanışından sonra düşecek miktar (~2-5 kg)
Fine limit:    Fine_stop = Target (± tolerance)

Adım 1 [COARSE]: Pompa hızlı akış (%100)
   Ağırlık ≥ Coarse_stop → hıza düş
Adım 2 [FINE]:   Pompa yavaş akış (%20-30)
   Ağırlık ≥ Fine_stop → pompa kapat, vana kapat
Adım 3 [SETTLE]: 5 sn bekle (sıvı durulsun)
Adım 4 [VERIFY]: Ölçülen değer içinde mi?
   |Actual - Target| ≤ tolerance → OK
   Aksi halde → ALARM + DEVIATION_LOG
```

**Alternatif — pompa AN/OF ise (Grundfos DDA):**
- Pompa strokes count ile dozaj (litre bazlı) + load cell ile teyit

---

## 5. Emniyet Interlock Matrisi

Hangi durumda hangi çıkış BLOKLANIR:

| Koşul | FV vanalar | Pompalar | Mixer | Not |
|-------|-----------|----------|-------|-----|
| `HS_PANEL_ESTOP` basıldı | ❌ hepsi | ❌ hepsi | ❌ | Manuel reset gerek |
| `WT_R01_MAIN` > 2950 kg (HH) | ❌ hepsi | ❌ hepsi | — | Reaktör dolu |
| `TT_R01_TEMP` > 60 °C (HH) | ❌ hepsi | ❌ hepsi | ❌ | Termal alarm |
| `AT_R01_PH` sınır dışı | — | — | — | Sadece alarm, QC HOLD |
| Load cell arıza (fault) | ❌ ilgili tank | ❌ ilgili pompa | — | Sensör alarmı |
| Vana pozisyon geri besleme yok (2 sn) | ❌ ilgili vana | ❌ ilgili pompa | — | Vana arıza |
| PLC-HMI iletişim koptu | ❌ hepsi | ❌ hepsi | ❌ | Fail-safe |

---

## 6. Alarm Kategorileri

| Kategori | Renk | Reset? | Örnek |
|----------|------|--------|-------|
| **CRITICAL** | Kırmızı + korna | Manuel | E-Stop, HH sıcaklık, HH ağırlık |
| **WARNING** | Sarı | Otomatik (sebep düzelince) | pH out of range, düşük stok |
| **INFO** | Yeşil | Otomatik | Batch tamamlandı, reçete yüklendi |

Alarm log format:
```
YYYY-MM-DD HH:MM:SS.mmm | LEVEL | TAG | VALUE | MESSAGE
2026-09-15 14:23:07.123 | CRITICAL | WT_R01_MAIN | 2967.5 | HH weight alarm
```

---

## 7. Sonraki Adım

- **03_plc_iskelet.md**: TIA Portal proje yapısı, DB tanımları, ana FB/FC listesi
- **PLC/SCL kaynak dosyaları**: `plc/src/` altında
- **Node-RED dashboard mockup**: `scada/flows.json`
