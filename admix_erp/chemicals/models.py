"""Kimyasal modelleri: GHS/CLP, SDS (Reg EU 2020/878), tehlike depolama,
EN 934-2 AVCP/CoC, retention numunesi, raf ömrü izleme.

Referanslar:
- GHS 8. revizyon (UN)
- CLP Regulation (EC) No 1272/2008
- EU 2020/878 (SDS format, 16 bölüm)
- REACH Article 31 (SDS zorunluluğu)
- EN 934-2:2009+A1:2012 (beton katkısı uygunluk + CE)
- ADR (Karayolu tehlikeli madde)
"""
from __future__ import annotations

import datetime as dt

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from simple_history.models import HistoricalRecords

from common.models import TimeStamped
from inventory.models import RawMaterialLot
from masterdata.models import Container, Product, RawMaterial
from production.models import ProductionBatch


# ---------------------------------------------------------------------------
# GHS: piktogram, sinyal, H/P ifadeleri
# ---------------------------------------------------------------------------

class Pictogram(TimeStamped):
    """GHS piktogramı (GHS01 patlayıcı ... GHS09 çevre)."""

    class Code(models.TextChoices):
        GHS01 = "GHS01", "Patlayıcı (Bomba)"
        GHS02 = "GHS02", "Alevlenir (Alev)"
        GHS03 = "GHS03", "Oksitleyici (Alev üzerinde daire)"
        GHS04 = "GHS04", "Basınçlı gaz (Silindir)"
        GHS05 = "GHS05", "Korozif"
        GHS06 = "GHS06", "Toksik (Ölü kafa)"
        GHS07 = "GHS07", "Zararlı / Tahriş edici (Ünlem)"
        GHS08 = "GHS08", "Sağlık tehlikesi (Silüet)"
        GHS09 = "GHS09", "Çevresel tehlike (Ölü balık)"

    code = models.CharField("Kod", max_length=6, choices=Code.choices, unique=True)
    name = models.CharField("Ad", max_length=120)
    image = models.ImageField(
        "Piktogram", upload_to="ghs/", null=True, blank=True,
    )

    class Meta:
        verbose_name = "GHS Piktogram"
        verbose_name_plural = "GHS Piktogramlar"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class SignalWord(models.TextChoices):
    DANGER = "DANGER", "Tehlike"
    WARNING = "WARNING", "Uyarı"
    NONE = "NONE", "Yok"


class HazardStatement(TimeStamped):
    """CLP/GHS H ifadesi (H200 patlayıcı, H315 ciltte tahriş, ...)."""

    code = models.CharField(
        "Kod", max_length=8, unique=True,
        validators=[RegexValidator(r"^H\d{3}[A-Za-z]*$", "Format: H### veya H###X")],
        help_text="Örn. H315, H319, H400.",
    )
    statement = models.CharField("İfade (TR)", max_length=255)
    statement_en = models.CharField("Statement (EN)", max_length=255, blank=True)
    hazard_class = models.CharField(
        "Tehlike sınıfı", max_length=120, blank=True,
        help_text="Örn. Skin corrosion/irritation Category 2",
    )

    class Meta:
        verbose_name = "H İfadesi"
        verbose_name_plural = "H İfadeleri"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.statement}"


class PrecautionaryStatement(TimeStamped):
    """CLP/GHS P ifadesi (P210 ısıdan uzak tut, P280 eldiven kullan, ...)."""

    class Category(models.TextChoices):
        GENERAL = "GENERAL", "Genel"
        PREVENTION = "PREVENTION", "Önleme"
        RESPONSE = "RESPONSE", "Müdahale"
        STORAGE = "STORAGE", "Depolama"
        DISPOSAL = "DISPOSAL", "Bertaraf"

    code = models.CharField(
        "Kod", max_length=8, unique=True,
        validators=[RegexValidator(r"^P\d{3}[+\d]*$", "Format: P###, P###+P###")],
    )
    statement = models.CharField("İfade (TR)", max_length=255)
    statement_en = models.CharField("Statement (EN)", max_length=255, blank=True)
    category = models.CharField(
        "Kategori", max_length=12, choices=Category.choices, default=Category.PREVENTION
    )

    class Meta:
        verbose_name = "P İfadesi"
        verbose_name_plural = "P İfadeleri"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.statement}"


# ---------------------------------------------------------------------------
# Kimyasal profil: RawMaterial ve Product için ortak
# ---------------------------------------------------------------------------

class HazardClass(models.TextChoices):
    """Tehlike depolama için ana sınıflar (basitleştirilmiş)."""
    NON_HAZARDOUS = "NON_HAZARDOUS", "Tehlikesiz"
    FLAMMABLE = "FLAMMABLE", "Yanıcı"
    OXIDIZER = "OXIDIZER", "Oksitleyici"
    ACID = "ACID", "Asit"
    BASE = "BASE", "Baz"
    TOXIC = "TOXIC", "Toksik"
    CORROSIVE = "CORROSIVE", "Korozif"
    ENV_HAZARD = "ENV_HAZARD", "Çevresel tehlike"
    COMPRESSED_GAS = "COMPRESSED_GAS", "Basınçlı gaz"
    EXPLOSIVE = "EXPLOSIVE", "Patlayıcı"


class ChemicalProfile(TimeStamped):
    """Bir hammadde veya ürünün kimyasal / tehlike profili.

    Her RawMaterial veya Product için tek profil (OneToOne).
    """

    raw_material = models.OneToOneField(
        RawMaterial, on_delete=models.CASCADE, null=True, blank=True,
        related_name="chemical_profile", verbose_name="Hammadde",
    )
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, null=True, blank=True,
        related_name="chemical_profile", verbose_name="Ürün",
    )

    cas_no = models.CharField(
        "CAS No", max_length=20, blank=True,
        help_text="Chemical Abstracts Service kimlik no",
    )
    ec_no = models.CharField("EC/EINECS No", max_length=20, blank=True)
    reach_registration = models.CharField(
        "REACH tescil no", max_length=40, blank=True,
        help_text="01-XXXXXXXXXX-XX-XXXX",
    )
    un_number = models.CharField(
        "UN No (ADR)", max_length=10, blank=True,
        help_text="Karayolu taşıma için UN numarası (örn. 1830 sülfürik asit)",
    )
    adr_class = models.CharField(
        "ADR sınıfı", max_length=10, blank=True,
        help_text="Ör. 8 (korozif), 5.1 (oksitleyici)",
    )
    packing_group = models.CharField(
        "Ambalaj grubu", max_length=5, blank=True,
        help_text="I / II / III",
    )

    signal_word = models.CharField(
        "Sinyal kelime", max_length=10, choices=SignalWord.choices, default=SignalWord.NONE
    )
    pictograms = models.ManyToManyField(Pictogram, blank=True, verbose_name="Piktogramlar")
    hazard_statements = models.ManyToManyField(
        HazardStatement, blank=True, verbose_name="H ifadeleri"
    )
    precautionary_statements = models.ManyToManyField(
        PrecautionaryStatement, blank=True, verbose_name="P ifadeleri"
    )

    hazard_class = models.CharField(
        "Tehlike sınıfı", max_length=20, choices=HazardClass.choices,
        default=HazardClass.NON_HAZARDOUS,
    )

    physical_state = models.CharField(
        "Fiziksel hal", max_length=30, blank=True,
        help_text="Sıvı / Katı / Gaz / Aerosol",
    )
    ph_range = models.CharField("pH aralığı", max_length=30, blank=True)
    flash_point_c = models.DecimalField(
        "Parlama noktası (°C)", max_digits=6, decimal_places=1, null=True, blank=True
    )
    boiling_point_c = models.DecimalField(
        "Kaynama noktası (°C)", max_digits=6, decimal_places=1, null=True, blank=True
    )
    melting_point_c = models.DecimalField(
        "Erime noktası (°C)", max_digits=6, decimal_places=1, null=True, blank=True
    )
    solubility_water = models.CharField(
        "Sudaki çözünürlük", max_length=100, blank=True,
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Kimyasal Profil"
        verbose_name_plural = "Kimyasal Profiller"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(raw_material__isnull=False, product__isnull=True)
                    | models.Q(raw_material__isnull=True, product__isnull=False)
                ),
                name="chemprofile_rm_xor_product",
            ),
        ]

    def __str__(self) -> str:
        target = self.raw_material or self.product
        return f"Profil · {target}"


# ---------------------------------------------------------------------------
# SDS (Safety Data Sheet) — Reg EU 2020/878, 16 bölüm
# ---------------------------------------------------------------------------

class SafetyDataSheet(TimeStamped):
    """SDS ana kaydı. Her ürün/hammadde için versiyonlu SDS.

    16 bölüm alanları TextField olarak — SDS'nin resmi yapısına uyum:
    1. Kimlik  2. Tehlike  3. Bileşim  4. İlk yardım  5. Yangınla mücadele
    6. Kaza  7. Elleçleme  8. Maruziyet kontrolü  9. Fiziksel/kimyasal
    10. Kararlılık  11. Toksikolojik  12. Ekolojik  13. Bertaraf
    14. Taşıma  15. Mevzuat  16. Diğer
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        APPROVED = "APPROVED", "Onaylı"
        SUPERSEDED = "SUPERSEDED", "Yerine yenisi geldi"
        WITHDRAWN = "WITHDRAWN", "Geri çekildi"

    sds_number = models.CharField("SDS No", max_length=40, unique=True)
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="sds_sheets",
        verbose_name="İş Kolu",
    )
    profile = models.ForeignKey(
        ChemicalProfile, on_delete=models.PROTECT,
        related_name="sds_versions", verbose_name="Kimyasal profil",
    )
    version = models.CharField("Versiyon", max_length=10, default="1.0")
    language = models.CharField(
        "Dil", max_length=5, default="tr",
        help_text="tr, en, fr, ar",
    )
    issue_date = models.DateField("Yayım tarihi", null=True, blank=True)
    revision_date = models.DateField("Revizyon tarihi", null=True, blank=True)
    next_review_date = models.DateField("Sonraki gözden geçirme", null=True, blank=True)

    # Reg EU 2020/878'in 16 bölümü — özet metinler; ayrıntı ekli PDF ile
    section_1_identification = models.TextField("1. Kimlik", blank=True)
    section_2_hazards = models.TextField("2. Tehlike tanımlaması", blank=True)
    section_3_composition = models.TextField("3. Bileşim / bileşenler", blank=True)
    section_4_first_aid = models.TextField("4. İlk yardım", blank=True)
    section_5_fire = models.TextField("5. Yangınla mücadele", blank=True)
    section_6_accidental = models.TextField("6. Kaza sonucu yayılma", blank=True)
    section_7_handling = models.TextField("7. Elleçleme ve depolama", blank=True)
    section_8_exposure = models.TextField("8. Maruziyet kontrolleri / KKD", blank=True)
    section_9_physical = models.TextField("9. Fiziksel ve kimyasal özellikler", blank=True)
    section_10_stability = models.TextField("10. Kararlılık ve reaktivite", blank=True)
    section_11_toxicological = models.TextField("11. Toksikolojik bilgiler", blank=True)
    section_12_ecological = models.TextField("12. Ekolojik bilgiler", blank=True)
    section_13_disposal = models.TextField("13. Bertaraf", blank=True)
    section_14_transport = models.TextField("14. Taşıma bilgileri", blank=True)
    section_15_regulatory = models.TextField("15. Mevzuat bilgileri", blank=True)
    section_16_other = models.TextField("16. Diğer bilgiler", blank=True)

    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="prepared_sds", verbose_name="Hazırlayan",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_sds", verbose_name="Onaylayan",
    )
    approved_at = models.DateTimeField("Onay zamanı", null=True, blank=True)

    file = models.FileField("Ek dosya (PDF)", upload_to="sds/%Y/", null=True, blank=True)
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.DRAFT
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Güvenlik Bilgi Formu (SDS)"
        verbose_name_plural = "SDS Kayıtları"
        ordering = ["-revision_date", "-created_at"]
        unique_together = (("profile", "version", "language"),)

    def __str__(self) -> str:
        return f"{self.sds_number} v{self.version} ({self.language})"


# ---------------------------------------------------------------------------
# Depolama uyumluluğu
# ---------------------------------------------------------------------------

class StorageZone(TimeStamped):
    """Depo bölgesi — tehlike sınıfına göre ayrılmış lokasyon."""

    code = models.CharField("Kod", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=120)
    location = models.CharField("Konum tanımı", max_length=200, blank=True)
    allowed_hazard_classes = models.CharField(
        "İzin verilen tehlike sınıfları (virgülle)", max_length=255, blank=True,
        help_text="Boşsa tüm sınıflar; aksi halde yalnız listelenen sınıflar.",
    )
    max_capacity_kg = models.DecimalField(
        "Maks. kapasite (kg)", max_digits=14, decimal_places=2, null=True, blank=True
    )
    temperature_min = models.DecimalField(
        "Min. sıcaklık (°C)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    temperature_max = models.DecimalField(
        "Maks. sıcaklık (°C)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    ventilation = models.CharField(
        "Havalandırma", max_length=60, blank=True,
        help_text="Doğal / Mekanik / Patlamaya dayanıklı",
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Depo Bölgesi"
        verbose_name_plural = "Depo Bölgeleri"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class StorageIncompatibility(TimeStamped):
    """Hangi iki tehlike sınıfı birlikte depolanamaz."""

    class_a = models.CharField("Sınıf A", max_length=20, choices=HazardClass.choices)
    class_b = models.CharField("Sınıf B", max_length=20, choices=HazardClass.choices)
    reason = models.CharField("Uyumsuzluk gerekçesi", max_length=255)

    class Meta:
        verbose_name = "Depolama Uyumsuzluğu"
        verbose_name_plural = "Depolama Uyumsuzlukları"
        unique_together = (("class_a", "class_b"),)

    def __str__(self) -> str:
        return f"{self.class_a} ⨯ {self.class_b}"


# ---------------------------------------------------------------------------
# EN 934-2 AVCP + Factory Production Control + CoC
# ---------------------------------------------------------------------------

class AVCPSystem(models.TextChoices):
    """EN 934-2 için AVCP sistemleri. Beton katkısı için genellikle 2+."""
    SYSTEM_1PLUS = "1+", "System 1+"
    SYSTEM_1 = "1", "System 1"
    SYSTEM_2PLUS = "2+", "System 2+"  # tipik: admixtures
    SYSTEM_3 = "3", "System 3"
    SYSTEM_4 = "4", "System 4"


class NotifiedBody(TimeStamped):
    """Onaylanmış kuruluş (notified body) — CE marking için."""

    number = models.CharField("NB No", max_length=10, unique=True)
    name = models.CharField("Ad", max_length=200)
    country = models.CharField("Ülke", max_length=60, blank=True)

    class Meta:
        verbose_name = "Onaylanmış Kuruluş"
        verbose_name_plural = "Onaylanmış Kuruluşlar"

    def __str__(self) -> str:
        return f"NB {self.number} · {self.name}"


class FPCTestPlan(TimeStamped):
    """Fabrika Üretim Kontrolü (FPC) test planı — ürün başına periyodik testler.

    EN 934-2 ürün için düzenli test frekansları tanımlar.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name="fpc_plans", verbose_name="Ürün",
    )
    avcp_system = models.CharField(
        "AVCP sistemi", max_length=4, choices=AVCPSystem.choices,
        default=AVCPSystem.SYSTEM_2PLUS,
    )
    notified_body = models.ForeignKey(
        NotifiedBody, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fpc_plans", verbose_name="Onaylanmış kuruluş",
    )
    effective_from = models.DateField("Yürürlük başlangıcı")
    frequency_per_batch = models.CharField(
        "Her parti için testler", max_length=255, blank=True,
        help_text="Virgüllü QCParameter kod listesi (örn. DENSITY,PH,SOLIDS,CHLORIDE)",
    )
    weekly_tests = models.CharField(
        "Haftalık testler", max_length=255, blank=True,
    )
    monthly_tests = models.CharField(
        "Aylık testler", max_length=255, blank=True,
    )
    annual_tests = models.CharField(
        "Yıllık testler", max_length=255, blank=True,
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "FPC Test Planı"
        verbose_name_plural = "FPC Test Planları"
        ordering = ["-effective_from"]

    def __str__(self) -> str:
        return f"FPC {self.product.code} · {self.avcp_system}"


class CertificateOfConformity(TimeStamped):
    """EN 934-2 uygunluk sertifikası (CoC) + CE marking dosyası."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        ISSUED = "ISSUED", "Yayımlandı"
        SUSPENDED = "SUSPENDED", "Askıya alındı"
        REVOKED = "REVOKED", "İptal"

    coc_number = models.CharField("CoC No", max_length=40, unique=True)
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name="conformity_certificates", verbose_name="Ürün",
    )
    fpc_plan = models.ForeignKey(
        FPCTestPlan, on_delete=models.PROTECT,
        related_name="certificates", verbose_name="FPC Planı",
    )
    standard = models.CharField(
        "Standart", max_length=40, default="EN 934-2:2009+A1:2012",
    )
    admixture_type = models.CharField(
        "Katkı tipi", max_length=80,
        help_text="Örn. Superplasticizer / High Range Water Reducer",
    )
    ce_marking_year = models.PositiveIntegerField(
        "CE marking yılı", null=True, blank=True,
    )
    dop_number = models.CharField(
        "DoP No", max_length=40, blank=True,
        help_text="Declaration of Performance numarası",
    )
    issue_date = models.DateField("Yayım tarihi")
    valid_until = models.DateField("Geçerlilik sonu", null=True, blank=True)
    issuing_body = models.ForeignKey(
        NotifiedBody, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="issued_cocs", verbose_name="Düzenleyen kuruluş",
    )
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField("Notlar", blank=True)
    file = models.FileField("PDF", upload_to="coc/%Y/", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Uygunluk Sertifikası (CoC)"
        verbose_name_plural = "Uygunluk Sertifikaları"
        ordering = ["-issue_date"]

    def __str__(self) -> str:
        return f"{self.coc_number} · {self.product.code}"


# ---------------------------------------------------------------------------
# Retention numunesi + raf ömrü izleme
# ---------------------------------------------------------------------------

class RetentionSample(TimeStamped):
    """Her partiden alınan referans numune (retention sample).

    Raf ömrü + 6 ay saklanır, sonra imha edilir. Şikayet/uyuşmazlık halinde
    yeniden analiz kaynağı.
    """

    class Status(models.TextChoices):
        STORED = "STORED", "Saklıda"
        RETESTED = "RETESTED", "Yeniden test edildi"
        DISPOSED = "DISPOSED", "İmha edildi"
        LOST = "LOST", "Kayıp"

    sample_number = models.CharField("Numune No", max_length=40, unique=True)
    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.PROTECT,
        related_name="retention_samples", verbose_name="Parti",
    )
    quantity = models.DecimalField("Miktar", max_digits=10, decimal_places=3)
    unit_label = models.CharField("Birim", max_length=10, default="kg")
    container = models.ForeignKey(
        Container, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="retention_samples", verbose_name="Kap",
    )
    storage_location = models.CharField("Saklama yeri", max_length=120)
    sampled_at = models.DateField("Alım tarihi")
    keep_until = models.DateField("Saklama sonu")
    disposed_at = models.DateField("İmha tarihi", null=True, blank=True)
    disposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="disposed_samples", verbose_name="İmha eden",
    )
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.STORED
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Retention Numunesi"
        verbose_name_plural = "Retention Numuneleri"
        ordering = ["-sampled_at"]

    def __str__(self) -> str:
        return f"{self.sample_number} · {self.batch.batch_number}"


class ShelfLifeAlert(TimeStamped):
    """Raf ömrü / son kullanma yaklaşan hammadde lotu için alert kaydı.

    `check_shelf_life` yönetim komutu bu tabloyu doldurur; kalite / depo
    ekibi izler.
    """

    class Severity(models.TextChoices):
        EXPIRED = "EXPIRED", "Süresi geçti"
        CRITICAL = "CRITICAL", "≤ 7 gün"
        WARNING = "WARNING", "≤ 30 gün"
        INFO = "INFO", "≤ 90 gün"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Açık"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Bilgi alındı"
        RESOLVED = "RESOLVED", "Çözüldü"

    lot = models.ForeignKey(
        RawMaterialLot, on_delete=models.CASCADE,
        related_name="shelf_alerts", verbose_name="Lot",
    )
    days_to_expiry = models.IntegerField("Kalan gün (negatif = geçmiş)")
    severity = models.CharField("Ağırlık", max_length=10, choices=Severity.choices)
    status = models.CharField("Durum", max_length=14, choices=Status.choices,
                              default=Status.OPEN)
    detected_on = models.DateField("Tespit tarihi", auto_now_add=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="acknowledged_shelf_alerts", verbose_name="Onaylayan",
    )
    acknowledged_at = models.DateTimeField("Onay zamanı", null=True, blank=True)
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name = "Raf Ömrü Alertı"
        verbose_name_plural = "Raf Ömrü Alertları"
        ordering = ["-detected_on", "days_to_expiry"]
        unique_together = (("lot", "detected_on"),)

    def __str__(self) -> str:
        return f"{self.lot.lot_number} · {self.severity} ({self.days_to_expiry}g)"
