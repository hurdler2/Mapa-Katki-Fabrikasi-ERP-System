# Sektör Araştırması — Kimyasal Katkı Üreticileri ERP Sistemleri

**Rapor tarihi:** 21 Ağustos 2026
**Amaç:** Sika, BASF, Mapei, Chryso, Fosroc gibi büyük katkı üreticilerinin
kullandığı ERP sistemlerini araştırıp ADMIX-ERP'de eksik olabilecek özellikleri
belirlemek.
**Yöntem:** 6 web araması, 40+ sektörel kaynak analizi.

---

## 1. Sektör Standartları ve Piyasa Liderleri

### Referans üreticiler
- **Sika** (İsviçre) — 60+ ülke, dünya lideri
- **BASF Master Builders Solutions** (Almanya)
- **Mapei** (İtalya) — yapıştırıcı + katkı lideri
- **Chryso** (Fransa, Saint-Gobain grubu) — Cezayir'de aktif
- **Fosroc** (İngiltere)
- **MC-Bauchemie** (Almanya)

Hepsi **ISO 9001 + OHSAS 18001 + EN 934-2** sertifikalıdır.

### Ana ERP çözümleri (kimyasal proses)
- **BatchMaster ERP** — kimyasal katkı özel sürümü
- **Deacom (ECI) ERP** — GHS/SDS entegre
- **SAP S/4HANA Chemicals** — büyük üreticiler için
- **Oracle NetSuite Chemical** — orta ölçek
- **Aptean Process Manufacturing ERP**

---

## 2. Kritik Modüller — Bizdeki Karşılığı ve Eksikler

### ✅ Zaten sağladıklarımız (S1-S8)

| Sektör gereksinimi | ADMIX-ERP karşılığı |
|---|---|
| FEFO envanter yönetimi | `record_dosing` + `_select_fefo_lot` |
| Batch genealogy forward/backward | `forward_trace` / `backward_trace` |
| Shelf life alert | `ShelfLifeAlert` + `expiry_date` |
| Formulation version control | `Recipe.version` + is_active kuralı |
| Batch tracking | `ProductionBatch` + 5-katmanlı ID |
| COA generation | `CertificateOfAnalysis` |
| QC Spec versioning + QA approval | Sprint 2 |
| Sampling plans | Sprint 2 (BR-QA-12) |
| Quality holds/release | `qc_status` state machine |
| SCADA data integration | `scada/models.py` (RecipeDownload) |
| CMMS | `cmms/` |
| Multi-facility | `BusinessLine` |
| E-fatura hazırlığı | Invoice + attachment |

### ❌ Sektörde standart ama bizde EKSİK

#### 🔴 KRİTİK (Yasal / Sertifikasyon)

| # | Eksik | Neden kritik | Referans |
|---|-------|-------------|----------|
| 1 | **SDS/GHS Safety Data Sheet** üretimi | CLP Regulation (EU), GHS zorunlu — ürün taşırken/satarken | Deacom, ERA-EHS, eQgest |
| 2 | **CE Marking + DoP** (Declaration of Performance) | EN 934-2 System 2+ — EU'ya ihracat için ZORUNLU | Mapei/Sika DoP örnekleri |
| 3 | **REACH SVHC substance tracking** | Restricted substance downstream notification | Trace One |
| 4 | **Notified Body FPC audit** kayıtları | System 2+ NB inspection trail — CE için |
| 5 | **EN 480 test method** referansları | Spec'lerde her parametreye standart metot linki | EN 934-2 conformity |

#### 🟠 YÜKSEK (Kalite/Ticari)

| # | Eksik | Değer |
|---|-------|-------|
| 6 | **Trial batch management** | Ücretsiz numune, müşteri deneme sonuçları — satış öncesi çevrim |
| 7 | **Customer site test data** | 7/14/28 gün küp mukavemet, slump, sıcaklık — QA döngüsü tamamlar |
| 8 | **Mix design consultation** | Müşteri özel reçete önerileri — teknik destek CRM'i |
| 9 | **Applicator training records** | Uygulayıcı eğitim izleri — Sika/Chryso modeli |
| 10 | **Slump retention over time test** | Sıcak iklim (Cezayir) için özellikle kritik |

#### 🟡 ORTA (Lojistik / Operasyon)

| # | Eksik | Değer |
|---|-------|-------|
| 11 | **Fleet management + GPS truck tracking** | Real-time delivery status |
| 12 | **Route optimization** | Yakıt %20 tasarruf, %30 turnaround azalması |
| 13 | **90-minute delivery timer** | Hazır beton için karışım sonrası kritik zaman |
| 14 | **MES campaign / super batch** | Kampanya bazlı planlama (bizde tekil batch) |
| 15 | **CMMS-SCADA otomatik köprü** | Sensor alert → work order otomasyonu |
| 16 | **Digital SOP step-by-step** | Operatör ekranı adım-adım rehber |

#### 🟢 DÜŞÜK (Gelecek hazırlığı)

| # | Eksik | Değer |
|---|-------|-------|
| 17 | **Product Digital Passport (DPP)** | 2027+ EU regülasyonu |
| 18 | **Continuous Transaction Control (CTC)** — DGI e-fatura | 2027'ye ertelendi |

---

## 3. Cezayir Özel Notlar

- **DGI e-fatura**: Ocak 2026 mandat ertelendi, 2027 sonrası bekleniyor. 5-corner CTC modeli hedefleniyor (İtalya/Türkiye benzeri).
- **G50 declaration**: aylık — Régime du Réel mükellefler ayın 20'sine kadar TVA + IBS avansları + diğer vergiler tek beyanname olarak veriyor. ✅ Bizde hazır.
- **ISO 9001 + OHSAS 18001** — Chryso Cezayir örneği: bölgesel operasyonlar sertifikalı. ✅ Bizde MCOS bunun üzerine kurulu.

---

## 4. Öncelik Sıralı Sprint 9-11 Yol Haritası

### Sprint 9 (KRİTİK yasal) — 2 hafta
- **S9.1**: `ProductSDS` modeli + GHS/CLP-uyumlu PDF üretimi (16-bölüm)
- **S9.2**: `DeclarationOfPerformance` modeli + EN 934-2 CE marking PDF
- **S9.3**: `RawMaterial.svhc_flag` + REACH downstream notification
- **S9.4**: `QCParameter.en480_method_ref` (EN 480 test metot alanı)
- **S9.5**: `FPCAudit` modeli (Factory Production Control — Notified Body)

### Sprint 10 (Ticari/Kalite) — 2 hafta
- **S10.1**: `TrialBatch` — deneme partisi, saha sonuçları
- **S10.2**: `CustomerSiteTest` — 7/14/28 gün küp mukavemet, slump, sıcaklık kayıtları
- **S10.3**: `MixDesignConsultation` — müşteri özel reçete önerisi
- **S10.4**: `ApplicatorTraining` — uygulayıcı eğitim izleri
- **S10.5**: `PerformanceWarranty` — garanti belgesi PDF

### Sprint 11 (Lojistik/Operasyon) — 2 hafta
- **S11.1**: `Truck` + `DeliveryTrip` — filo/sefer takibi
- **S11.2**: GPS tracking altyapısı (dış API/webhook)
- **S11.3**: `ProductionCampaign` — MES super/sub batch
- **S11.4**: SCADA→CMMS köprü (`SensorAlert` → otomatik `WorkOrder`)
- **S11.5**: Digital SOP portal ekranı (operatör view)

**Toplam süre:** ~6 hafta, tahmini test kazanımı: +40 test yeşil

---

## 5. Nihai Değerlendirme

**Bizim güçlü olduğumuz alanlar (sektör lideri seviyesinde):**
- MCOS 8-Part Gate + 12 non-negotiable rules (rakipte yok)
- 5-katmanlı ID (Case/Record/Evidence/Decision/Signature) — audit üstün
- Cezayir SCF (PCN 2010) + TVA G50 tam entegre
- BusinessLine (MCS/MPT/MFT/MLTS) çoklu iş kolu ayrımı
- COMPLÉMENT §22 + Facteur d'échelle (UsineERP paritesi)
- BL Client + Facture de Dépense + Cari hesap (Sprint 6-8)

**Sektörle boy ölçüşmek için EN KRİTİK 5 eksik:**
1. **SDS/GHS PDF üretimi** — CLP zorunlu
2. **CE Marking + DoP** — EN 934-2 System 2+
3. **REACH SVHC tracking** — EU ihracatı için
4. **Trial batch + Customer site test** — satış öncesi teknik destek
5. **Fleet/GPS delivery tracking** — 90-min beton teslim penceresi

Bu 5 kalem Sprint 9-10 içinde tamamlanırsa ADMIX-ERP; Sika/BASF/Chryso'nun
Cezayir'de kullandığı sistemlerle **fonksiyonel paritede** olur — hatta MCOS
metodolojisi + Cezayir SCF entegrasyonuyla bazı yönlerden ileride kalır.

---

## 6. Kaynakça

- [Chemical Manufacturing ERP Software (BatchMaster)](https://www.batchmaster.com/erp-for-chemicals-industries/)
- [Deacom SDS/GHS Labeling](https://www.ecisolutions.com/blog/manufacturing/deacom-erp-software/sds-and-ghs-labeling-with-deacom-erp/)
- [ERA-EHS SDS Authoring](https://www.era-environmental.com/solutions/sds-authoring)
- [eQgest CLP Labeling](https://www.eqgest.com/en/module/clp-labelling)
- [Trace One SDS Compliance](https://www.traceone.com/resources/plm-compliance-blog/what-is-sds-software-chemical-companies)
- [EN 934-2 CE Marking & DoP](https://www.admixtures.org.uk/publications/the-cpr-admixture-ce-marking-and-dop/)
- [Applus Laboratories — CE Marking of Admixtures](https://www.appluslaboratories.com/global/en/what-we-do/service-sheet/ce-marking-of-admixtures)
- [Sika Concrete Admixture Standards](https://gbr.sika.com/en/construction/concrete/standards/admixture-standards.html)
- [Sika Group](https://www.sika.com/)
- [Mapei DoP Example](https://cdnmediautt.mapei.com/docs/librariesprovider5/products-documents/3_ise_ce-dop_2274_en-934-2_gb_2_b70c71e5deb04aa59ff3500851a542a2.pdf)
- [Chemical ERP Batch Traceability (NetSuite/Folio3)](https://netsuite.folio3.com/blog/chemical-manufacturing-batch-lot-traceability/)
- [Algeria e-Invoicing Slipped Beyond 2026 (VATcalc)](https://www.vatcalc.com/algeria/algeria-e-invoicing-mandate-slips/)
- [DGI E-Invoicing API Guide](https://tax2gov.com/algeria-dgi-e-invoicing-api/)
- [Algeria VAT Guide 2026 (Quaderno)](https://quaderno.io/guides/algeria-vat-guide/)
- [Concrete Fleet Management (Fleetrabbit)](https://fleetrabbit.com/blogs/post/concrete-ready-mix-fleet-management-software)
- [Ready-Mix Dispatch Software (Linkoper)](https://linkoper.com/solutions/concrete-plant-software)
- [Cement Logistics Optimization (OxMaint)](https://oxmaint.com/industries/cement-plant/cement-logistics-optimization-fleet-dispatch)
- [Slump Retention Solutions (SidleyChem)](https://sidleychem.com/concrete-slump-loss-causes-solutions/)
- [Sakshi Chem — Slump Retention Admixtures](https://sakshichemsciences.com/slump-retention-admixtures/)
- [CMMS-ERP-MES-SCADA-IoT Integration (OxMaint)](https://oxmaint.com/industries/manufacturing-plant/cmms-integration-erp-mes-scada-iot-manufacturing-connectivity)
- [ERP MES SCADA PLC IoT Integration Challenges (BlueNet)](https://www.bluenetinc.com/erp-mes-scada-plc-iot-integration-challenges-manufacturing/)
- [ERP for Chemical Manufacturing 2026 (CorningData)](https://corningdata.com/resources/blog/how-to-select-the-best-erp-for-chemical-manufacturing-in-2026/)
- [ERP for Chemical Manufacturing 2026 DPPs (AstraCanyon)](https://www.astracanyon.com/blog/erp-for-chemical-manufacturing)
- [Concrete Industry ERP (ERPlax)](https://erplax.com/concrete-industry-erp-software)
- [Top 10 Ready Mix Concrete ERP (NYGGS)](https://nyggs.com/blog/top-10-erp-software-for-ready-mix-concrete-industry/)
- [Fosroc Admixtures](https://www.fosroc.com/solutions/concrete-admixtures)
- [Cemex Advanced Admixture](https://www.cemexusa.com/products/concrete-admixtures-and-additives)
