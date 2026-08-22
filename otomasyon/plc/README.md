# PLC Yazılımı — TIA Portal Projesi

**Platform:** Siemens TIA Portal V19 (V17+ uyumlu)
**PLC:** S7-1215C DC/DC/DC (6ES7 215-1AG40-0XB0)
**HMI:** KTP700 Basic (6AV2 123-2GB03-0AX0)
**Dil:** SCL (Structured Control Language) + LAD karışık

---

## Proje Yapısı (TIA Portal)

```
MAPA_Dosage_v1/
├── Program Blocks/
│   ├── Main [OB1]                    // Ana döngü — sadece FB çağırıcı
│   ├── Cyclic interrupt [OB35]       // 100 ms tarama (kontrol döngüleri)
│   ├── Startup [OB100]               // Boot init
│   ├── Diagnostic error [OB82]       // Modül arıza
│   │
│   ├── FC_ReadInputs                 // Tüm I okuma + skaling
│   ├── FC_WriteOutputs               // Tüm Q yazma
│   ├── FC_Alarms                     // Alarm mantığı
│   ├── FC_Interlocks                 // Emniyet kilit matrisi
│   │
│   ├── FB_DoseController [DB_Dose_1..5]   // Her hammadde için ayrı instance
│   ├── FB_BatchSequencer [DB_Batch]       // Ana state machine
│   ├── FB_MixerControl [DB_Mixer]         // Mixer VFD kontrolü
│   ├── FB_WeightScaling [DB_Weight_1..8]  // Load cell mV → kg dönüşümü
│   ├── FB_QCMonitor [DB_QC]               // pH/T/Cl kalite ölçüm
│   └── FB_RecipeLoader [DB_Recipe]        // Reçete yükleme
│
├── Data Blocks/
│   ├── DB_Recipe             // Aktif reçete
│   ├── DB_Batch              // Batch durumu + timer'lar
│   ├── DB_Weights            // 8 load cell current + tare
│   ├── DB_QC                 // pH, T, Cl değerleri + limit'ler
│   ├── DB_Alarms             // Alarm bit alanı + zaman damgaları
│   ├── DB_Interlocks         // Kilit durumları
│   └── DB_HMI_Interface      // HMI ↔ PLC değişkenler
│
└── PLC Tags/
    ├── IO_Inputs (%I)
    ├── IO_Outputs (%Q)
    ├── IO_Analog (%IW / %QW)
    └── Constants
```

---

## OB1 (Main) — Yalın çağırıcı

```pascal
// OB1 — Sadece ana FB'leri çağırır
CALL "FC_ReadInputs"          // Tüm I ve AI oku, skaling
CALL "FC_Interlocks"          // Emniyet kilit matrisini değerlendir
CALL "FB_BatchSequencer", "DB_Batch"    // Ana state machine
CALL "FB_MixerControl", "DB_Mixer"      // Mixer PID
CALL "FB_QCMonitor", "DB_QC"            // Kalite ölçüm
CALL "FC_Alarms"              // Alarm bit'lerini set
CALL "FC_WriteOutputs"        // Tüm Q çıkışları yaz
```

---

## OB35 (Cyclic 100 ms) — Kontrol döngüleri

```pascal
// 100 ms tarama — pompa PID / dozaj rate control
CALL "FB_DoseController", "DB_Dose_1"
CALL "FB_DoseController", "DB_Dose_2"
CALL "FB_DoseController", "DB_Dose_3"
CALL "FB_DoseController", "DB_Dose_4"
CALL "FB_DoseController", "DB_Dose_5"
```

---

## Kaynak Dosyalar

- [`src/FB_BatchSequencer.scl`](src/FB_BatchSequencer.scl) — Ana state machine (13 state)
- [`src/FB_DoseController.scl`](src/FB_DoseController.scl) — Coarse+Fine dozajlama
- [`src/FB_WeightScaling.scl`](src/FB_WeightScaling.scl) — Load cell mV → kg
- [`src/FC_Interlocks.scl`](src/FC_Interlocks.scl) — Emniyet kilit matrisi
- [`src/DB_Recipe.udt`](src/DB_Recipe.udt) — Reçete veri yapısı

---

## Sonraki Adım

TIA Portal V19'da proje oluştur:
1. `Create new project` → Name: `MAPA_Dosage_v1`
2. `Add new device` → PLC → S7-1215C
3. `Program blocks` altına yukarıdaki dosyaları import et:
   - Sağ tık → `External source files` → SCL dosyalarını seç
   - Sağ tık → dosya → `Generate blocks from source`
4. Compile (Ctrl+B) → hatasız derlenmeli
5. Bilgisayarda PLCSIM Advanced ile simüle et (donanım gelene kadar)

## Test Simulasyonu

Donanım gelene kadar PLCSIM V19 ile:
- Load cell değerini elle giriyoruz
- Batch sekansını çalıştırıyoruz
- HMI davranışını doğruluyoruz
