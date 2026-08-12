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
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Hammadde"
        verbose_name_plural = "Hammaddeler"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


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

    class Meta:
        verbose_name = "Müşteri"
        verbose_name_plural = "Müşteriler"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


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
