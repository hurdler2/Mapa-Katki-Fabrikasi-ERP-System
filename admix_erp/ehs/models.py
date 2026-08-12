"""EHS modelleri: İSG olay, PPE, maruziyet, çevresel yön/ölçüm, yasal
yükümlülük, JSA, iş izin sistemi.

Referanslar:
- ISO 45001:2018 (OHS) — §6.1.2 tehlike tanımlama, §8.1.2 iş izin, §10.2 olay
- ISO 14001:2015 (EMS) — §6.1.2 çevresel yönler, §6.1.3 yasal uyum, §9.1.2 uyum değerlendirme
- Cezayir mevzuat: Loi 88-07 (İSG), Loi 03-10 (çevre)
"""
from __future__ import annotations

import datetime as dt

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from chemicals.models import ChemicalProfile
from common.models import TimeStamped
from qms.models import CAPA, Nonconformance


# ---------------------------------------------------------------------------
# İSG olay
# ---------------------------------------------------------------------------

class Incident(TimeStamped):
    """İSG / çevre olayı. Kaza, ramak kala, meslek hastalığı, çevresel olay."""

    class Type(models.TextChoices):
        INJURY = "INJURY", "Yaralanma"
        NEAR_MISS = "NEAR_MISS", "Ramak kala"
        OCCUPATIONAL_DISEASE = "OCCUPATIONAL_DISEASE", "Meslek hastalığı"
        PROPERTY_DAMAGE = "PROPERTY_DAMAGE", "Mal hasarı"
        ENVIRONMENTAL = "ENVIRONMENTAL", "Çevresel olay (sızıntı vb.)"
        FIRE = "FIRE", "Yangın / patlama"
        CHEMICAL_EXPOSURE = "CHEMICAL_EXPOSURE", "Kimyasal maruziyet"
        OTHER = "OTHER", "Diğer"

    class Severity(models.TextChoices):
        FIRST_AID = "FIRST_AID", "İlk yardım"
        MEDICAL = "MEDICAL", "Medikal müdahale"
        LOST_TIME = "LOST_TIME", "İşgünü kaybı"
        SERIOUS = "SERIOUS", "Ciddi yaralanma"
        FATAL = "FATAL", "Ölümcül"
        MINOR = "MINOR", "Küçük"
        SIGNIFICANT = "SIGNIFICANT", "Önemli"
        MAJOR = "MAJOR", "Büyük"

    class Status(models.TextChoices):
        REPORTED = "REPORTED", "Bildirildi"
        INVESTIGATING = "INVESTIGATING", "İnceleme"
        ACTION_PENDING = "ACTION_PENDING", "Aksiyon bekliyor"
        CLOSED = "CLOSED", "Kapatıldı"

    incident_number = models.CharField("Olay No", max_length=40, unique=True)
    case = models.ForeignKey(
        "records.Case", on_delete=models.PROTECT,
        null=True, blank=True, related_name="incidents",
        verbose_name="MCOS Case",
    )
    type = models.CharField("Tip", max_length=24, choices=Type.choices)
    severity = models.CharField(
        "Ağırlık", max_length=16, choices=Severity.choices, default=Severity.MINOR
    )
    occurred_at = models.DateTimeField("Olay zamanı")
    reported_at = models.DateTimeField("Bildirim zamanı", auto_now_add=True)
    location = models.CharField(
        "Yer", max_length=200,
        help_text="Örn. Reaktör 1 alanı / SP Deposu",
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="reported_incidents", verbose_name="Bildiren",
    )
    investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="investigated_incidents", verbose_name="İnceleyici",
    )

    description = models.TextField("Olay açıklaması")
    immediate_actions = models.TextField("Anlık alınan önlemler", blank=True)

    # Yaralanma detayları
    affected_persons = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name="affected_incidents", verbose_name="Etkilenen personel",
    )
    body_parts = models.CharField(
        "Vücut bölgesi", max_length=200, blank=True,
        help_text="Baş, göz, el, sırt vb.",
    )
    days_lost = models.PositiveIntegerField("Kayıp işgünü", default=0)

    # Çevresel olay detayları
    environmental_medium = models.CharField(
        "Etkilenen çevre bileşeni", max_length=60, blank=True,
        help_text="Toprak / Su / Hava",
    )
    spilled_material = models.CharField("Yayılan malzeme", max_length=200, blank=True)
    spilled_quantity_kg = models.DecimalField(
        "Yayılan miktar (kg)", max_digits=12, decimal_places=4, null=True, blank=True
    )

    # Kök neden ve bağlantılar
    root_cause_analysis = models.TextField("Kök neden analizi", blank=True)
    ncr = models.ForeignKey(
        Nonconformance, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="incidents", verbose_name="Bağlı NCR",
    )
    capa = models.ForeignKey(
        CAPA, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="incidents", verbose_name="Bağlı CAPA",
    )

    status = models.CharField(
        "Durum", max_length=16, choices=Status.choices, default=Status.REPORTED
    )
    closed_at = models.DateTimeField("Kapanış", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "İSG / Çevre Olayı"
        verbose_name_plural = "İSG / Çevre Olayları"
        ordering = ["-occurred_at"]

    def __str__(self) -> str:
        return f"{self.incident_number} · {self.get_type_display()}"


# ---------------------------------------------------------------------------
# PPE (KKD)
# ---------------------------------------------------------------------------

class PPEItem(TimeStamped):
    """Kişisel Koruyucu Ekipman (KKD) türü."""

    class Category(models.TextChoices):
        HEAD = "HEAD", "Baş (kask)"
        EYE = "EYE", "Göz (gözlük/vizör)"
        EAR = "EAR", "Kulak"
        RESPIRATORY = "RESPIRATORY", "Solunum (maske/respiratör)"
        HAND = "HAND", "El (eldiven)"
        FOOT = "FOOT", "Ayak (çelik burun/lastik çizme)"
        BODY = "BODY", "Vücut (tulum/önlük)"
        FALL_PROTECTION = "FALL_PROTECTION", "Düşme koruması (paraşüt tipi kemer)"
        OTHER = "OTHER", "Diğer"

    code = models.CharField("Kod", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=120)
    category = models.CharField("Kategori", max_length=20, choices=Category.choices)
    standard = models.CharField(
        "Standart", max_length=80, blank=True,
        help_text="EN 166 (göz), EN 388 (mekanik el), EN 374 (kimyasal el) vb.",
    )
    supplier = models.CharField("Tedarikçi", max_length=120, blank=True)
    replacement_days = models.PositiveIntegerField(
        "Değişim periyodu (gün)", null=True, blank=True,
        help_text="Boşsa tek kullanımlık veya sınırsız.",
    )
    stock_quantity = models.PositiveIntegerField("Stok adet", default=0)
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "PPE (KKD)"
        verbose_name_plural = "PPE (KKD) Kalemleri"
        ordering = ["category", "code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class PPEIssuance(TimeStamped):
    """Kullanıcıya KKD teslim / iade kaydı."""

    class Status(models.TextChoices):
        ISSUED = "ISSUED", "Teslim edildi"
        RETURNED = "RETURNED", "İade alındı"
        LOST = "LOST", "Kayıp"
        DAMAGED = "DAMAGED", "Hasarlı"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="ppe_issuances", verbose_name="Personel",
    )
    item = models.ForeignKey(
        PPEItem, on_delete=models.PROTECT,
        related_name="issuances", verbose_name="Kalem",
    )
    quantity = models.PositiveIntegerField("Adet", default=1)
    issued_at = models.DateField("Teslim tarihi")
    replace_by = models.DateField("Değişim tarihi", null=True, blank=True)
    returned_at = models.DateField("İade tarihi", null=True, blank=True)
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.ISSUED
    )
    notes = models.TextField("Not", blank=True)

    class Meta:
        verbose_name = "PPE Teslim Kaydı"
        verbose_name_plural = "PPE Teslim Kayıtları"
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return f"{self.user.get_username()} · {self.item.code} × {self.quantity}"


# ---------------------------------------------------------------------------
# Kimyasal maruziyet
# ---------------------------------------------------------------------------

class ExposureMeasurement(TimeStamped):
    """Kişisel / alan bazlı kimyasal maruziyet ölçümü."""

    class Method(models.TextChoices):
        PERSONAL_SAMPLING = "PERSONAL", "Kişisel örnekleme"
        AREA_SAMPLING = "AREA", "Alan örnekleme"
        BIOLOGICAL = "BIO", "Biyolojik izleme"

    class Route(models.TextChoices):
        INHALATION = "INHALATION", "Solunum"
        SKIN = "SKIN", "Cilt"
        EYE = "EYE", "Göz"
        INGESTION = "INGESTION", "Yutma"

    measurement_number = models.CharField("Ölçüm No", max_length=40, unique=True)
    chemical_profile = models.ForeignKey(
        ChemicalProfile, on_delete=models.PROTECT,
        related_name="exposures", verbose_name="Kimyasal",
    )
    person = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="exposure_records", verbose_name="Ölçülen kişi",
    )
    area = models.CharField(
        "Alan", max_length=120, blank=True,
        help_text="Alan ölçümüyse buraya lokasyon yazın",
    )
    method = models.CharField("Yöntem", max_length=10, choices=Method.choices)
    route = models.CharField("Maruziyet yolu", max_length=12, choices=Route.choices)
    measured_value = models.DecimalField(
        "Ölçüm değeri", max_digits=12, decimal_places=4
    )
    unit = models.CharField("Birim", max_length=30, help_text="mg/m³, ppm, µg/L ...")
    twa_limit = models.DecimalField(
        "TWA sınırı (8s)", max_digits=12, decimal_places=4, null=True, blank=True,
        help_text="OEL / TLV / STEL",
    )
    measured_at = models.DateTimeField("Ölçüm zamanı")
    laboratory = models.CharField("Laboratuvar", max_length=120, blank=True)
    coa_reference = models.CharField("Rapor referansı", max_length=80, blank=True)

    class Meta:
        verbose_name = "Maruziyet Ölçümü"
        verbose_name_plural = "Maruziyet Ölçümleri"
        ordering = ["-measured_at"]

    def __str__(self) -> str:
        return f"{self.measurement_number} · {self.chemical_profile}"

    @property
    def above_limit(self) -> bool | None:
        if self.twa_limit is None:
            return None
        return self.measured_value > self.twa_limit


# ---------------------------------------------------------------------------
# Çevresel yön ve etkiler (ISO 14001)
# ---------------------------------------------------------------------------

class EnvironmentalAspect(TimeStamped):
    """Çevresel yön kaydı (§6.1.2).

    Her aktivite × yön kombinasyonu için bir kayıt. Önem değerlendirmesi
    yapıldıktan sonra "önemli yön" olarak işaretlenir.
    """

    class Category(models.TextChoices):
        AIR_EMISSION = "AIR_EMISSION", "Hava emisyonu"
        WASTEWATER = "WASTEWATER", "Atık su"
        SOLID_WASTE = "SOLID_WASTE", "Katı atık"
        HAZARDOUS_WASTE = "HAZARDOUS_WASTE", "Tehlikeli atık"
        NOISE = "NOISE", "Gürültü"
        VIBRATION = "VIBRATION", "Titreşim"
        ENERGY = "ENERGY", "Enerji tüketimi"
        WATER = "WATER", "Su tüketimi"
        RAW_MATERIAL = "RAW_MATERIAL", "Hammadde tüketimi"
        LAND_USE = "LAND_USE", "Toprak / arazi"
        BIODIVERSITY = "BIODIVERSITY", "Biyoçeşitlilik"
        SPILL = "SPILL", "Dökülme / sızıntı"
        ODOR = "ODOR", "Koku"
        OTHER = "OTHER", "Diğer"

    class OperatingCondition(models.TextChoices):
        NORMAL = "NORMAL", "Normal işletim"
        ABNORMAL = "ABNORMAL", "Anormal (bakım, açılış/kapanış)"
        EMERGENCY = "EMERGENCY", "Acil durum"

    code = models.CharField("Kod", max_length=30, unique=True)
    activity = models.CharField(
        "Aktivite / Süreç", max_length=200,
        help_text="Örn. Reaktör dolumu, IBC yıkama, ürün sevkiyatı",
    )
    aspect = models.CharField(
        "Yön (impact source)", max_length=200,
        help_text="Örn. SP hammadde buharlaşması, atık su deşarjı",
    )
    category = models.CharField(
        "Kategori", max_length=20, choices=Category.choices
    )
    operating_condition = models.CharField(
        "İşletim durumu", max_length=12, choices=OperatingCondition.choices,
        default=OperatingCondition.NORMAL,
    )

    # Önem skoru (5×5): sıklık × büyüklük
    frequency_score = models.PositiveSmallIntegerField("Sıklık (1-5)", default=3)
    magnitude_score = models.PositiveSmallIntegerField("Büyüklük (1-5)", default=3)
    is_significant = models.BooleanField(
        "Önemli yön mü?", default=False,
        help_text="Önem eşiği aşıldıysa TRUE.",
    )

    control_measures = models.TextField("Mevcut kontrol önlemleri", blank=True)
    monitoring_plan = models.TextField("İzleme planı", blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_env_aspects", verbose_name="Sorumlu",
    )

    class Meta:
        verbose_name = "Çevresel Yön"
        verbose_name_plural = "Çevresel Yönler"
        ordering = ["-is_significant", "code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.activity} → {self.category}"

    @property
    def significance_score(self) -> int:
        return (self.frequency_score or 0) * (self.magnitude_score or 0)


class EnvironmentalMeasurement(TimeStamped):
    """Çevresel ölçüm / tüketim kaydı (aylık / periyodik)."""

    aspect = models.ForeignKey(
        EnvironmentalAspect, on_delete=models.CASCADE,
        related_name="measurements", verbose_name="Çevresel yön",
    )
    period_start = models.DateField("Dönem başlangıcı")
    period_end = models.DateField("Dönem sonu")
    quantity = models.DecimalField(
        "Miktar", max_digits=14, decimal_places=4,
    )
    unit = models.CharField(
        "Birim", max_length=30,
        help_text="kg, L, m³, kWh, dBA, ton CO2eq ...",
    )
    limit_value = models.DecimalField(
        "Yasal limit", max_digits=14, decimal_places=4, null=True, blank=True
    )
    measurement_method = models.CharField("Ölçüm yöntemi", max_length=120, blank=True)
    laboratory = models.CharField("Akredite lab.", max_length=120, blank=True)
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Çevresel Ölçüm"
        verbose_name_plural = "Çevresel Ölçümler"
        ordering = ["-period_end"]

    def __str__(self) -> str:
        return f"{self.aspect.code} {self.period_start}..{self.period_end} = {self.quantity} {self.unit}"

    @property
    def above_limit(self) -> bool | None:
        if self.limit_value is None:
            return None
        return self.quantity > self.limit_value


# ---------------------------------------------------------------------------
# Yasal yükümlülük (§6.1.3 EMS + §6.1.3 OHS)
# ---------------------------------------------------------------------------

class LegalRequirement(TimeStamped):
    """Yasal + diğer yükümlülük kaydı ve uyum durumu."""

    class Domain(models.TextChoices):
        OHS = "OHS", "İSG"
        ENV = "ENV", "Çevre"
        CHEMICAL = "CHEMICAL", "Kimyasal"
        LABOR = "LABOR", "Çalışma"
        FIRE = "FIRE", "Yangın"
        BUILDING = "BUILDING", "Yapı"
        OTHER = "OTHER", "Diğer"

    class Status(models.TextChoices):
        COMPLIANT = "COMPLIANT", "Uygun"
        NON_COMPLIANT = "NON_COMPLIANT", "Uygunsuz"
        PARTIAL = "PARTIAL", "Kısmen uygun"
        PENDING = "PENDING", "Değerlendirilmedi"

    code = models.CharField("Kod", max_length=40, unique=True)
    reference = models.CharField(
        "Mevzuat referansı", max_length=200,
        help_text="Örn. Loi 03-10 / Décret 06-198 / EN 934-2",
    )
    title = models.CharField("Başlık", max_length=200)
    domain = models.CharField("Alan", max_length=10, choices=Domain.choices)
    description = models.TextField("Açıklama", blank=True)
    applicable_to = models.CharField(
        "Uygulanabilirlik", max_length=200, blank=True,
        help_text="Hangi süreç/tesise uygulanır",
    )
    compliance_status = models.CharField(
        "Uyum durumu", max_length=14, choices=Status.choices, default=Status.PENDING
    )
    last_evaluated_on = models.DateField("Son değerlendirme", null=True, blank=True)
    next_review_date = models.DateField("Sonraki gözden geçirme", null=True, blank=True)
    evidence = models.TextField("Uyum kanıtı", blank=True)
    ncr = models.ForeignKey(
        Nonconformance, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="legal_gaps", verbose_name="Uygunsuzluk NCR'ı",
    )

    class Meta:
        verbose_name = "Yasal Yükümlülük"
        verbose_name_plural = "Yasal Yükümlülükler"
        ordering = ["domain", "code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.title}"


# ---------------------------------------------------------------------------
# JSA (İş Güvenliği Analizi) — ISO 45001 §6.1.2
# ---------------------------------------------------------------------------

class JobSafetyAnalysis(TimeStamped):
    """Bir iş / görev için tehlike analizi + kontrol önlemleri."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        APPROVED = "APPROVED", "Onaylı"
        ARCHIVED = "ARCHIVED", "Arşivlendi"

    jsa_number = models.CharField("JSA No", max_length=40, unique=True)
    task_name = models.CharField("İş / Görev", max_length=200)
    location = models.CharField("Yer / Ekipman", max_length=200, blank=True)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="prepared_jsas", verbose_name="Hazırlayan",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_jsas", verbose_name="Onaylayan",
    )
    approved_at = models.DateTimeField("Onay zamanı", null=True, blank=True)
    review_date = models.DateField("Yenileme tarihi", null=True, blank=True)
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    required_ppe = models.ManyToManyField(
        PPEItem, blank=True, related_name="jsas",
        verbose_name="Gerekli KKD",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "İş Güvenliği Analizi (JSA)"
        verbose_name_plural = "İş Güvenliği Analizleri"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.jsa_number} · {self.task_name}"


class JSAStep(TimeStamped):
    """JSA'nın alt adımı — her adım için tehlike ve kontrol önlemi."""

    class RiskLevel(models.TextChoices):
        LOW = "LOW", "Düşük"
        MEDIUM = "MEDIUM", "Orta"
        HIGH = "HIGH", "Yüksek"
        CRITICAL = "CRITICAL", "Kritik"

    jsa = models.ForeignKey(
        JobSafetyAnalysis, on_delete=models.CASCADE,
        related_name="steps", verbose_name="JSA",
    )
    sequence = models.PositiveIntegerField("Sıra")
    step_description = models.CharField("Adım", max_length=255)
    hazards = models.TextField("Tehlikeler")
    controls = models.TextField("Kontrol önlemleri")
    residual_risk = models.CharField(
        "Kalıntı risk", max_length=10, choices=RiskLevel.choices,
        default=RiskLevel.LOW,
    )

    class Meta:
        verbose_name = "JSA Adımı"
        verbose_name_plural = "JSA Adımları"
        ordering = ["jsa", "sequence"]
        unique_together = (("jsa", "sequence"),)

    def __str__(self) -> str:
        return f"{self.jsa.jsa_number} · #{self.sequence} {self.step_description[:40]}"


# ---------------------------------------------------------------------------
# İş İzin Sistemi (Permit To Work) — ISO 45001 §8.1.2
# ---------------------------------------------------------------------------

class WorkPermit(TimeStamped):
    """İş izin belgesi — yüksek riskli işler için.

    Sıcak çalışma, kapalı alan girişi, yüksekte çalışma, kazı, elektrik,
    line-break, kimyasal temizlik.
    """

    class Type(models.TextChoices):
        HOT_WORK = "HOT_WORK", "Sıcak çalışma"
        CONFINED_SPACE = "CONFINED_SPACE", "Kapalı alan girişi"
        WORK_AT_HEIGHT = "WORK_AT_HEIGHT", "Yüksekte çalışma"
        EXCAVATION = "EXCAVATION", "Kazı"
        ELECTRICAL = "ELECTRICAL", "Elektrik"
        LINE_BREAK = "LINE_BREAK", "Boru hattı açımı"
        CHEMICAL_CLEANING = "CHEMICAL_CLEANING", "Kimyasal temizlik"
        LOCKOUT_TAGOUT = "LOCKOUT_TAGOUT", "LOTO"
        OTHER = "OTHER", "Diğer"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        REQUESTED = "REQUESTED", "Talep edildi"
        ISSUED = "ISSUED", "Verildi (aktif)"
        SUSPENDED = "SUSPENDED", "Askıya alındı"
        CLOSED = "CLOSED", "Kapatıldı"
        EXPIRED = "EXPIRED", "Süresi doldu"
        CANCELLED = "CANCELLED", "İptal"

    permit_number = models.CharField("İzin No", max_length=40, unique=True)
    type = models.CharField("Tip", max_length=20, choices=Type.choices)
    work_description = models.TextField("İş tanımı")
    location = models.CharField("Yer", max_length=200)

    valid_from = models.DateTimeField("Geçerlilik başlangıcı")
    valid_until = models.DateTimeField("Geçerlilik sonu")

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="requested_permits", verbose_name="Talep eden",
    )
    permit_holder = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="held_permits", verbose_name="İzin sahibi (yürüten)",
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="issued_permits", verbose_name="Veren yetkili",
    )
    issued_at = models.DateTimeField("Veriliş zamanı", null=True, blank=True)
    safety_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="witnessed_permits", verbose_name="İSG uzmanı",
    )

    jsa = models.ForeignKey(
        JobSafetyAnalysis, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="permits", verbose_name="Bağlı JSA",
    )
    required_ppe = models.ManyToManyField(
        PPEItem, blank=True, related_name="permits",
        verbose_name="Zorunlu KKD",
    )
    isolation_measures = models.TextField(
        "İzolasyon önlemleri", blank=True,
        help_text="LOTO, valf kapatma, elektrik kesme, boşaltma vb.",
    )
    gas_test_result = models.CharField(
        "Gaz ölçüm sonucu", max_length=200, blank=True,
        help_text="O2 %, LEL %, H2S ppm, CO ppm — kapalı alan/sıcak çalışma için",
    )
    fire_watch_required = models.BooleanField("Yangın gözcüsü zorunlu", default=False)

    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    closed_at = models.DateTimeField("Kapanış zamanı", null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="closed_permits", verbose_name="Kapatan",
    )
    closure_notes = models.TextField("Kapanış notları", blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "İş İzni"
        verbose_name_plural = "İş İzinleri"
        ordering = ["-valid_from"]

    def __str__(self) -> str:
        return f"{self.permit_number} · {self.get_type_display()}"
