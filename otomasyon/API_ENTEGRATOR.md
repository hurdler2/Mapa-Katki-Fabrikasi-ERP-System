# SCADA ↔ ADMIX-ERP API — Entegratöre Teslim Belgesi

**ERP:** ADMIX-ERP (hazır ve çalışıyor)
**Baz URL:** `http://ERP_HOST:8000/api/v1/`
**Kimlik doğrulama:** Token authentication
**İçerik tipi:** `application/json`

Bu belge SCADA entegratörünün ADMIX-ERP ile konuşması için gereken **tek şey**.
3 endpoint var; hepsinin örneği ve dönüşü aşağıda.

---

## Kurulum — İlk Adım

ERP tarafında bir kez bu komut çalıştırılır:

```bash
python manage.py scada_setup
```

Çıktı:
```
========================================================================
SCADA BRIDGE BILGILERI
========================================================================
Username:      scada_bridge
Token:         6a9eb8cf07dc0331558e7e778b2927ef2743be9c

Node-RED / SCADA icin HTTP header:
  Authorization: Token 6a9eb8cf07dc0331558e7e778b2927ef2743be9c
========================================================================
```

Bu token'i Node-RED'e **güvenli** olarak saklayın (credentials node).

Token yenilemek için: `python manage.py scada_setup --rotate` (6 ayda bir).

---

## 1. Batch Tamamlandı → ERP'ye Bildir

**Endpoint:**
```
POST /api/v1/production/batches/from-scada/
```

**Header:**
```http
Authorization: Token 6a9eb8cf07dc0331558e7e778b2927ef2743be9c
Content-Type: application/json
```

**Gövde:**
```json
{
    "batch_number": "BATCH-20260915-042",
    "recipe_code": "ADX-100-v3",
    "target_kg": 1000.0,
    "actual_kg": 999.7,
    "started_at": "2026-09-15T14:23:07Z",
    "completed_at": "2026-09-15T15:03:12Z",
    "operator": "Mohamed Belaidi",
    "consumptions": [
        {"code": "W",  "target": 600.0, "actual": 600.2},
        {"code": "M1", "target": 250.0, "actual": 249.8},
        {"code": "M2", "target": 80.0,  "actual": 80.1},
        {"code": "IN", "target": 15.0,  "actual": 14.9},
        {"code": "ZT", "target": 8.0,   "actual": 8.0},
        {"code": "BZ", "target": 47.0,  "actual": 47.1}
    ],
    "qc_results": [
        {"parameter": "PH", "value": 5.8, "verdict": "PASS"},
        {"parameter": "TEMP", "value": 32.5, "verdict": "PASS"},
        {"parameter": "CHLORIDE", "value": 245.0, "verdict": "PASS"}
    ]
}
```

**Alan açıklamaları:**

| Alan | Zorunlu | Not |
|------|---------|-----|
| `batch_number` | ✅ | Benzersiz. Ör. `BATCH-YYYYMMDD-NNN`. Idempotent — aynı numara iki kez gönderilirse 200 döner. |
| `recipe_code` | ✅ | `<ProductCode>-v<Version>` format. Ör. `ADX-100-v3`. Product kod-versiyon ayrımını `-v` yapar. |
| `target_kg` | ✅ | Hedef batch ağırlığı. |
| `actual_kg` | ✅ | Gerçek üretilen ağırlık. |
| `started_at` | ✅ | ISO 8601 UTC. |
| `completed_at` | Opsiyonel | ISO 8601 UTC. |
| `operator` | Opsiyonel | Yoksa "SCADA-AUTO" yazılır. Maks 120 karakter. |
| `consumptions[]` | Opsiyonel | Boş liste kabul edilir. `code` bulunmayan hammadde `warnings.missing_raw_material_codes` altında döner. |
| `qc_results[]` | Opsiyonel | `verdict` = `PASS`/`FAIL`/`NA`. Tanınmayan parametre uyarı olarak döner. |

**Başarılı yanıt (201 Created):**
```json
{
    "batch_id": 1247,
    "batch_number": "BATCH-20260915-042",
    "consumption_ids": [3841, 3842, 3843, 3844, 3845, 3846],
    "qc_result_ids": [821, 822, 823],
    "warnings": null,
    "message": "Batch BATCH-20260915-042 SCADA'dan alındı."
}
```

**Idempotency yanıtı (200 OK):**
```json
{
    "batch_id": 1247,
    "batch_number": "BATCH-20260915-042",
    "duplicate": true,
    "message": "Bu batch daha önce ERP'ye kaydedilmişti."
}
```

**Hata yanıtları:**

| Kod | Anlamı | Ne yap? |
|-----|--------|---------|
| `400` | Zorunlu alan eksik / geçersiz sayı | JSON'u kontrol et |
| `401` | Token yanlış | scada_setup çalıştır |
| `404` | Reçete bulunamadı | ERP'de reçete tanımlı mı? |
| `500` | ERP tarafı hata | Log paylaş, ERP ekibine haber ver |

---

## 2. Aktif Reçeteyi Çek (PLC'ye yazmak için)

**Endpoint:**
```
GET /api/v1/production/active-recipe/
GET /api/v1/production/active-recipe/?product_code=ADX-100
```

**Header:**
```http
Authorization: Token 6a9eb8cf07dc0331558e7e778b2927ef2743be9c
```

**Query parametresi:**

| Alan | Zorunlu | Not |
|------|---------|-----|
| `product_code` | Opsiyonel | Belirli bir ürün için aktif reçete. Verilmezse ilk aktif reçete. |

**Başarılı yanıt (200 OK):**
```json
{
    "product_code": "ADX-100",
    "product_name": "Superplasticizer PCE",
    "recipe_code": "ADX-100-v3",
    "version": 3,
    "base_batch_size": 1000.0,
    "unit": "kg",
    "lines": [
        {
            "sequence": 1,
            "code": "W",
            "name": "Su",
            "quantity": 600.0,
            "tolerance_pct": 0.5,
            "is_complement": true
        },
        {
            "sequence": 2,
            "code": "M1",
            "name": "Monomer A",
            "quantity": 250.0,
            "tolerance_pct": 0.5,
            "is_complement": false
        }
    ],
    "quality_targets": {
        "ph_min": 4.5,
        "ph_max": 7.0,
        "temp_max_c": 45.0,
        "chloride_max_ppm": 800.0
    },
    "fetched_at": "2026-09-15T14:00:00Z"
}
```

**Bu veriyi Node-RED'de PLC Modbus register 40100+'a yazın:**

| Modbus Register | Değer | Kaynak |
|-----------------|-------|--------|
| `40100-40101` | `lines[0].quantity` (Real) | Su miktarı |
| `40102-40103` | `lines[1].quantity` | RM1 |
| `40104-40105` | `lines[2].quantity` | RM2 |
| ... | ... | ... |
| `40140-40141` | `base_batch_size` | Hedef batch |
| `40142-40143` | `quality_targets.ph_min` | pH alt limit |
| `40144-40145` | `quality_targets.ph_max` | pH üst limit |
| `40146-40147` | `quality_targets.temp_max_c` | Sıcaklık max |
| `40148-40149` | `quality_targets.chloride_max_ppm` | Klor max |

---

## 3. ERP Sağlık Kontrolü + Son Batch Listesi

**Endpoint:**
```
GET /api/v1/production/scada/status/
```

**Kullanım:** Node-RED health check her 5 dakikada bir bu endpoint'i çağırıp
200 dönüyor mu diye kontrol eder. Dashboardda "ERP Online/Offline" göstergesi.

**Başarılı yanıt (200 OK):**
```json
{
    "erp_status": "OK",
    "server_time": "2026-09-15T15:04:12Z",
    "authenticated_as": "scada_bridge",
    "stats": {
        "scada_batches_today": 8,
        "scada_batches_week": 41,
        "last_batch_at": "2026-09-15T15:03:12Z"
    },
    "recent_batches": [
        {
            "batch_number": "BATCH-20260915-042",
            "recipe": "ADX-100-v3",
            "target_kg": 1000.0,
            "actual_kg": 999.7,
            "operator": "Mohamed Belaidi",
            "started_at": "2026-09-15T14:23:07Z",
            "completed_at": "2026-09-15T15:03:12Z"
        }
    ]
}
```

---

## Test Komutları (curl)

### 1. Sağlık kontrolü:
```bash
curl -H "Authorization: Token 6a9eb8cf07dc0331558e7e778b2927ef2743be9c" \
     http://192.168.1.100:8000/api/v1/production/scada/status/
```

### 2. Aktif reçete çek:
```bash
curl -H "Authorization: Token 6a9eb8cf07dc0331558e7e778b2927ef2743be9c" \
     "http://192.168.1.100:8000/api/v1/production/active-recipe/?product_code=ADX-100"
```

### 3. Test batch POST:
```bash
curl -X POST \
     -H "Authorization: Token 6a9eb8cf07dc0331558e7e778b2927ef2743be9c" \
     -H "Content-Type: application/json" \
     -d '{
       "batch_number": "BATCH-TEST-001",
       "recipe_code": "ADX-100-v3",
       "target_kg": 1000,
       "actual_kg": 999.5,
       "started_at": "2026-09-15T14:00:00Z",
       "completed_at": "2026-09-15T14:30:00Z",
       "operator": "Test User",
       "consumptions": [],
       "qc_results": []
     }' \
     http://192.168.1.100:8000/api/v1/production/batches/from-scada/
```

---

## Failsafe — Ağ Kesintisi

**Node-RED tarafında yapılması gereken:**

Batch tamamlandığında POST 200/201 dönmezse (timeout, 5xx, ağ kopuk):

```javascript
// Node-RED function node — retry queue
if (msg.statusCode >= 500 || !msg.statusCode) {
    // Kuyruğa ekle
    const queue = flow.get('failed_queue') || [];
    queue.push({
        payload: msg.original_payload,
        first_attempt: new Date(),
        retry_count: 0
    });
    flow.set('failed_queue', queue);

    // Retry: Her 5 dk'da bir dene, max 24 saat
    node.warn(`Batch queued for retry (queue size: ${queue.length})`);
}
```

**24 saat sonra queue temizlenmezse:**
- Operatöre HMI üzerinden uyarı ver
- E-posta gönder (yönetici)
- ERP açıldığında kronolojik sırayla POST et

---

## Modbus TCP — İkinci Kanal (Opsiyonel)

Bazı entegratörler REST yerine Modbus TCP direkt tercih edebilir. Bu durumda
Node-RED **hem** PLC'yi Modbus okur **hem de** ERP'ye REST POST atar.
İki yol da paralel çalışır.

Modbus register haritası: `otomasyon/scada/README.md` § Modbus Adres Haritası.

---

## ADMIX-ERP Tarafında Kontrol

Entegratör POST attıktan sonra sonuç ERP portal'ında görünür:

**URL:** `http://ERP_HOST:8000/portal/scada/`

Bu sayfada:
- ✅ Bugün / bu hafta / toplam SCADA batch sayısı
- ✅ Son 24 saat aktivite grafiği
- ✅ Son 20 batch listesi (verim yüzdesi ile)
- ✅ Bridge kullanıcı + token durumu
- ✅ API endpoint listesi

Entegratörün başarısız olduğu her batch bu ekranda GÖRÜNMEZ — sadece başarılı olanlar. Failsafe (retry queue) çalışmıyorsa boşluk oluşur → uyarı.

---

## Sorun Giderme

| Belirti | Muhtemel sebep | Çözüm |
|---------|----------------|-------|
| `401 Unauthorized` | Token yanlış / süresi doldu | `scada_setup --rotate` |
| `404 Not Found` (URL) | URL yolu yanlış | Baz URL'i doğrula: `/api/v1/` |
| `404 Not Found` (recipe) | Reçete kodu yanlış | ERP'de reçete tanımlı mı? Portal'dan bakın |
| `400 Bad Request` | JSON alan eksik | Response body'i oku, hangi alan? |
| Portal'da batch görünmüyor | POST 201 dönmedi | Node-RED debug'ta yanıtı incele |
| Reçete GET 200 ama boş | is_active reçete yok | Portal'dan reçeteyi aktifleştir |

---

## İletişim

Entegrasyon sorusu, gerçek sunucudaki test için:
- ERP mühendislik ekibi: [ERP_TEAM_EMAIL]
- Şirket içi: [MAPA_IT_CONTACT]

**Not:** Bu belgedeki tüm endpoint'ler test edilmiştir (10/10 pytest).
Sözleşme öncesi entegratör isterse test ortamına erişim sağlanır.

---

**Belge sürümü:** 1.0
**Tarih:** 22 Ağustos 2026
