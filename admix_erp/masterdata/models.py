"""Ana veri modelleri: hammadde, ürün, tedarikçi, müşteri, kap, birim."""
from django.db import models

from common.models import TimeStamped


class UnitOfMeasure(TimeStamped):
    """Ölçü birimi (kg, L, ...)."""

    code = models.CharField("Kod", max_length=10, unique=True)
    name = models.CharField("Ad", max_length=60)

    class Meta:
        verbose_name = "Ölçü Birimi"
        verbose_name_plural = "Ölçü Birimleri"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class RawMaterial(TimeStamped):
    """Hammadde ana kaydı (W, G, SP, HD ...)."""

    class MaterialType(models.TextChoices):
        WATER = "WATER", "Su"
        RETARDER = "RETARDER", "Priz geciktirici"
        SUPERPLASTICIZER = "SUPERPLASTICIZER", "Süperplastikleştirici"
        ADDITIVE = "ADDITIVE", "Katkı bileşeni"
        OTHER = "OTHER", "Diğer"

    code = models.CharField("Kod", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=120)
    material_type = models.CharField(
        "Tip", max_length=32, choices=MaterialType.choices, default=MaterialType.OTHER
    )
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT, related_name="raw_materials", verbose_name="Birim"
    )
    density = models.DecimalField(
        "Yoğunluk (kg/L)", max_digits=8, decimal_places=4, null=True, blank=True
    )
    shelf_life_days = models.PositiveIntegerField("Raf ömrü (gün)", null=True, blank=True)
    # REACH / SVHC (Sprint 9)
    svhc_flag = models.BooleanField(
        "REACH SVHC", default=False,
        help_text="Substance of Very High Concern — REACH downstream notification zorunlu.",
    )
    svhc_pct = models.DecimalField(
        "SVHC oranı (%)", max_digits=6, decimal_places=3, null=True, blank=True,
        help_text="SVHC bileşik oranı — >0.1% ise downstream users bilgilendirilir.",
    )
    reach_registration_no = models.CharField(
        "REACH kayıt no", max_length=40, blank=True,
        help_text="01-XXXXXXXXXX-XX-XXXX formatında ECHA registration number.",
    )
    cas_number = models.CharField(
        "CAS numarası", max_length=20, blank=True,
        help_text="Chemical Abstracts Service — Ör. 9003-01-4",
    )
    ec_number = models.CharField(
        "EC numarası", max_length=20, blank=True,
    )
    alert_threshold = models.DecimalField(
        "Seuil d'alerte", max_digits=12, decimal_places=2,
        default=0,
        help_text="Bu miktarın altına düşerse sarı alarm (uyarı) verilir.",
    )
    rupture_threshold = models.DecimalField(
        "Seuil de rupture", max_digits=12, decimal_places=2,
        default=0,
        help_text="Bu miktarın altına düşerse kırmızı alarm (kritik) verilir.",
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Hammadde"
        verbose_name_plural = "Hammaddeler"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    @property
    def current_stock(self):
        """Anlık toplam RELEASED stok (RawMaterialLot.remaining_qty toplamı)."""
        from decimal import Decimal
        from django.db.models import Sum
        from inventory.models import RawMaterialLot
        total = RawMaterialLot.objects.filter(
            raw_material=self,
            qc_status=RawMaterialLot.QCStatus.RELEASED,
        ).aggregate(t=Sum("remaining_qty"))["t"] or Decimal("0")
        return total

    def stock_level(self):
        """Stok seviyesi: 'ok' | 'alert' | 'rupture'."""
        cur = self.current_stock
        if self.rupture_threshold and cur <= self.rupture_threshold:
            return "rupture"
        if self.alert_threshold and cur <= self.alert_threshold:
            return "alert"
        return "ok"


class Product(TimeStamped):
    """Mamul (beton katkı ürünü)."""

    code = models.CharField("Kod", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=120)
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT, related_name="products", verbose_name="Birim"
    )
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="products",
        verbose_name="İş Kolu",
        help_text="MCOS BusinessLine (MCS/MPT/MFT/MLTS). Geçiş dönemi için null.",
    )
    description = models.TextField("Açıklama", blank=True)
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Supplier(TimeStamped):
    """Tedarikçi."""

    code = models.CharField("Kod", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=200)
    contact = models.CharField("İletişim", max_length=200, blank=True)
    tax_no = models.CharField("Vergi No", max_length=30, blank=True)
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Tedarikçi"
        verbose_name_plural = "Tedarikçiler"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Customer(TimeStamped):
    """Müşteri."""

    code = models.CharField("Kod", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=200)
    contact = models.CharField("İletişim", max_length=200, blank=True)
    tax_no = models.CharField("Vergi No", max_length=30, blank=True)
    is_active = models.BooleanField("Aktif", default=True)

    # Fatura ozel ayarlari
    default_discount_pct = models.DecimalField(
        "Varsayılan iskonto (%)", max_digits=5, decimal_places=2,
        default=0,
        help_text="Bu müşteriye faturada otomatik uygulanacak iskonto (0-100).",
    )
    address = models.TextField("Adres", blank=True)
    email = models.EmailField("E-posta", blank=True)

    class Meta:
        verbose_name = "Müşteri"
        verbose_name_plural = "Müşteriler"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class CompanyProfile(TimeStamped):
    """Şirket profili (SINGLETON) — MAPA'nın kendi kimliği + logo + banka.

    Sistemde en fazla bir tane olur. Fatura PDF/print başlığında,
    e-posta imzalarında ve resmi belgelerde kullanılır.
    """

    legal_name = models.CharField(
        "Yasal ünvan", max_length=200,
        default="SARL MAPA ALGÉRIE",
    )
    short_name = models.CharField(
        "Kısa ad", max_length=60, default="MAPA",
    )
    tagline = models.CharField(
        "Slogan", max_length=200, blank=True,
        default="Sıvı Beton Katkısı Fabrikası",
    )
    logo = models.ImageField(
        "Logo (PNG/JPG, max 2MB)", upload_to="company/",
        null=True, blank=True,
    )

    # İletişim
    address = models.TextField(
        "Adres", blank=True,
        default="Zone Industrielle Blida, Algérie",
    )
    phone = models.CharField("Telefon", max_length=30, blank=True)
    email = models.EmailField("E-posta", blank=True)
    website = models.URLField("Web sitesi", blank=True)

    # Cezayir vergi kimliği
    tax_no = models.CharField(
        "NIF (Vergi kimlik no)", max_length=30, blank=True,
        help_text="Numéro d'Identification Fiscale",
    )
    tax_activity_no = models.CharField(
        "NIS (İstatistik no)", max_length=30, blank=True,
        help_text="Numéro d'Identification Statistique",
    )
    trade_register_no = models.CharField(
        "RC (Ticaret sicil no)", max_length=40, blank=True,
        help_text="Registre du Commerce",
    )
    article_of_import_no = models.CharField(
        "Article No", max_length=30, blank=True,
    )

    # Banka
    bank_name = models.CharField("Banka", max_length=100, blank=True)
    bank_rib = models.CharField(
        "RIB (Cezayir hesap kimlik)", max_length=40, blank=True,
        help_text="Relevé d'Identité Bancaire",
    )
    bank_iban = models.CharField("IBAN", max_length=40, blank=True)

    # Fatura üstü ek metin
    invoice_header_note = models.TextField(
        "Fatura üst notu", blank=True,
    )
    invoice_footer_note = models.TextField(
        "Fatura alt notu (ödeme koşulları vs.)", blank=True,
        default="Ödeme vadesi 30 gün. Geç ödemelerde faiz uygulanır.",
    )

    class Meta:
        verbose_name = "Şirket Profili"
        verbose_name_plural = "Şirket Profili"

    def __str__(self) -> str:
        return self.legal_name

    def save(self, *args, **kwargs):
        # Singleton — pk=1 olarak zorla
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Silmeyi engelle
        pass

    @classmethod
    def get(cls) -> "CompanyProfile":
        """Tek satırlı company — yoksa varsayılanla oluşturur."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Container(TimeStamped):
    """Fiziksel kap / tank / IBC / reaktör."""

    class ContainerType(models.TextChoices):
        TANK = "TANK", "Tank"
        IBC = "IBC", "IBC"
        REACTOR = "REACTOR", "Reaktör"

    code = models.CharField("Kod", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=120)
    container_type = models.CharField(
        "Tip", max_length=16, choices=ContainerType.choices
    )
    capacity = models.DecimalField("Kapasite", max_digits=12, decimal_places=4)
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT, related_name="containers", verbose_name="Birim"
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Kap"
        verbose_name_plural = "Kaplar"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.get_container_type_display()})"
