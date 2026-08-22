"""Satış modelleri: müşteri siparişi, satırı, sevkiyat, sevkiyat satırı."""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStamped
from masterdata.models import Customer, Product, UnitOfMeasure
from production.models import OutputContainer


class SalesOrder(TimeStamped):
    """Müşteri siparişi."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        CONFIRMED = "CONFIRMED", "Onaylandı"
        PARTIAL = "PARTIAL", "Kısmi sevk"
        SHIPPED = "SHIPPED", "Sevk edildi"
        CANCELLED = "CANCELLED", "İptal"

    order_number = models.CharField("Sipariş No", max_length=40, unique=True)
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="sales_orders",
        verbose_name="İş Kolu",
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name="sales_orders", verbose_name="Müşteri",
    )
    order_date = models.DateField("Sipariş tarihi")
    delivery_date = models.DateField("Sevk tarihi", null=True, blank=True)
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Müşteri Siparişi"
        verbose_name_plural = "Müşteri Siparişleri"
        ordering = ["-order_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.order_number} · {self.customer.code}"

    def refresh_status(self) -> None:
        lines = list(self.lines.all())
        if not lines:
            return
        total_ordered = sum(l.quantity for l in lines)
        total_shipped = sum(l.shipped_qty for l in lines)
        if total_shipped <= 0:
            new_status = SalesOrder.Status.CONFIRMED
        elif total_shipped >= total_ordered:
            new_status = SalesOrder.Status.SHIPPED
        else:
            new_status = SalesOrder.Status.PARTIAL
        if new_status != self.status and self.status not in {
            SalesOrder.Status.DRAFT, SalesOrder.Status.CANCELLED
        }:
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])


class SalesOrderLine(TimeStamped):
    """Müşteri siparişi satırı."""

    so = models.ForeignKey(
        SalesOrder, on_delete=models.CASCADE,
        related_name="lines", verbose_name="Sipariş",
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name="so_lines", verbose_name="Ürün",
    )
    quantity = models.DecimalField("Miktar", max_digits=12, decimal_places=4)
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT,
        related_name="so_lines", verbose_name="Birim",
    )
    unit_price = models.DecimalField(
        "Birim fiyat", max_digits=12, decimal_places=4, default=Decimal("0")
    )
    shipped_qty = models.DecimalField(
        "Sevk edilen miktar", max_digits=12, decimal_places=4, default=Decimal("0")
    )

    class Meta:
        verbose_name = "SO Satırı"
        verbose_name_plural = "SO Satırları"
        unique_together = (("so", "product"),)

    def __str__(self) -> str:
        return f"{self.so.order_number} · {self.product.code} × {self.quantity}"

    @property
    def outstanding_qty(self) -> Decimal:
        return self.quantity - self.shipped_qty


class Shipment(TimeStamped):
    """Sevkiyat / BL Client (Bordereau de Livraison — İrsaliye).

    Cezayir uyumu: bir müşteri sevkiyatı **fatura kesilmeden** önce
    bir BL (irsaliye) belgesiyle çıkar; fatura sonradan bir veya
    birden fazla BL'yi kapsayacak şekilde kesilir.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        DELIVERED = "DELIVERED", "Teslim edildi"
        INVOICED = "INVOICED", "Faturalandı"
        CANCELLED = "CANCELLED", "İptal"

    shipment_number = models.CharField("BL / Sevk No", max_length=40, unique=True)
    so = models.ForeignKey(
        SalesOrder, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="shipments", verbose_name="Sipariş",
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name="shipments", verbose_name="Müşteri",
    )
    shipped_date = models.DateField("Sevk tarihi")
    carrier = models.CharField("Taşıyıcı", max_length=120, blank=True)
    vehicle_plate = models.CharField("Araç plaka", max_length=30, blank=True)
    driver_name = models.CharField("Şoför", max_length=120, blank=True)
    delivery_address = models.TextField("Teslim adresi", blank=True)
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.DRAFT,
    )
    invoice = models.ForeignKey(
        "accounting.Invoice", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="delivery_notes",
        verbose_name="Bağlı Fatura",
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "BL Client (İrsaliye)"
        verbose_name_plural = "BL Clients (İrsaliyeler)"
        ordering = ["-shipped_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.shipment_number} · {self.customer.code}"

    @property
    def total_amount(self) -> Decimal:
        """BL üzerindeki toplam tutar (satır fiyatı × miktar)."""
        total = Decimal("0")
        for line in self.lines.select_related("so_line"):
            price = line.so_line.unit_price if line.so_line else Decimal("0")
            total += (line.quantity * price)
        return total.quantize(Decimal("0.01"))


class ShipmentLine(TimeStamped):
    """Sevkiyat satırı — bir OutputContainer (IBC) müşteriye eşleşir."""

    shipment = models.ForeignKey(
        Shipment, on_delete=models.CASCADE,
        related_name="lines", verbose_name="Sevkiyat",
    )
    so_line = models.ForeignKey(
        SalesOrderLine, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="shipment_lines", verbose_name="SO Satırı",
    )
    output_container = models.OneToOneField(
        OutputContainer, on_delete=models.PROTECT,
        related_name="shipment_line", verbose_name="Mamul IBC",
    )
    quantity = models.DecimalField("Miktar", max_digits=12, decimal_places=4)

    class Meta:
        verbose_name = "Sevkiyat Satırı"
        verbose_name_plural = "Sevkiyat Satırları"

    def __str__(self) -> str:
        return f"{self.shipment.shipment_number} · IBC {self.output_container.container.code}"


# ---------------------------------------------------------------------------
# Sprint 10 — Ticari destek + Kalite döngüsü modelleri
# ---------------------------------------------------------------------------

class TrialBatch(TimeStamped):
    """Deneme partisi — müşteri sahasında ücretsiz numune ile yapılan test.

    Sika/BASF modeli: müşteri sipariş vermeden önce küçük bir parti gönderilir,
    saha ekibi katkıyı kendi çimentosu/agregasıyla test eder, sonuçlar buraya
    kaydedilir. Başarılı olursa fatura+SO açılır.
    """

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planlandı"
        SHIPPED = "SHIPPED", "Numune gönderildi"
        IN_TRIAL = "IN_TRIAL", "Saha testinde"
        SUCCESS = "SUCCESS", "Başarılı (sipariş uygun)"
        FAILED = "FAILED", "Başarısız"
        CANCELLED = "CANCELLED", "İptal"

    trial_number = models.CharField("Trial No", max_length=40, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name="trial_batches", verbose_name="Müşteri",
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name="trial_batches", verbose_name="Ürün adayı",
    )
    trial_date = models.DateField("Deneme tarihi")
    sample_quantity = models.DecimalField(
        "Numune miktarı", max_digits=10, decimal_places=2,
        help_text="Ör. 25 kg — küçük deneme paketi.",
    )
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT,
        related_name="trial_units",
    )
    site_address = models.CharField(
        "Saha adresi", max_length=300, blank=True,
        help_text="Deneme yapılacak inşaat/santral konumu.",
    )
    # Müşteri çimento/agrega bilgisi
    customer_cement_brand = models.CharField(
        "Müşteri çimento markası", max_length=120, blank=True,
    )
    customer_cement_class = models.CharField(
        "Çimento sınıfı", max_length=40, blank=True,
        help_text="Ör. CEM I 42.5 R, CEM II B-M 32.5 N",
    )
    aggregate_max_size = models.CharField(
        "Agrega max boyutu", max_length=20, blank=True,
    )
    target_slump = models.CharField(
        "Hedef slump", max_length=40, blank=True,
        help_text="Ör. S3 (100-150 mm), S4 (160-210 mm)",
    )
    target_wc_ratio = models.DecimalField(
        "Hedef w/c oranı", max_digits=5, decimal_places=3, null=True, blank=True,
    )
    dosage_pct = models.DecimalField(
        "Doz (%)", max_digits=5, decimal_places=3, null=True, blank=True,
        help_text="Çimento ağırlığına göre önerilen doz.",
    )
    # Sonuçlar (saha tarafından geri gelir)
    initial_slump = models.CharField(
        "İlk slump (mm)", max_length=20, blank=True,
    )
    slump_30min = models.CharField("30 dk slump (mm)", max_length=20, blank=True)
    slump_60min = models.CharField("60 dk slump (mm)", max_length=20, blank=True)
    slump_90min = models.CharField("90 dk slump (mm)", max_length=20, blank=True)
    site_temperature = models.CharField(
        "Saha sıcaklığı (°C)", max_length=20, blank=True,
    )
    trial_notes = models.TextField(
        "Saha ekibi notları", blank=True,
        help_text="Müşteri geri bildirimi + saha ekibi gözlemleri.",
    )
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.PLANNED,
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="trials_performed", verbose_name="Sorumlu",
    )

    class Meta:
        verbose_name = "Trial Batch"
        verbose_name_plural = "Trial Batches"
        ordering = ["-trial_date"]

    def __str__(self) -> str:
        return f"{self.trial_number} · {self.customer.code} · {self.product.code}"


class MixDesignConsultation(TimeStamped):
    """Müşteri özel formül/karışım tasarımı — teknik destek CRM'i.

    Sika/BASF: müşteri özel projesi için katkı doz ayarı, sıcak/soğuk iklim
    formülü, ekstra dayanım için karışım optimizasyonu.
    """

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Talep alındı"
        IN_STUDY = "IN_STUDY", "Çalışılıyor"
        DELIVERED = "DELIVERED", "Rapor teslim edildi"
        IMPLEMENTED = "IMPLEMENTED", "Sahada uygulandı"

    consultation_number = models.CharField("Consultation No", max_length=40, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name="mix_design_consultations",
    )
    request_date = models.DateField("Talep tarihi")
    project_name = models.CharField(
        "Proje adı", max_length=200,
        help_text="Ör. Otoyol köprüsü Sétif, Baraj enjeksiyonu Béjaïa",
    )
    concrete_class_target = models.CharField(
        "Beton sınıfı hedefi", max_length=40,
        help_text="Ör. C30/37, C40/50, C50/60",
    )
    special_requirements = models.TextField(
        "Özel gereksinimler",
        help_text="Sıcak iklim, deniz suyu maruziyeti, erken dayanım, vs.",
    )
    proposed_products = models.CharField(
        "Önerilen ürün(ler)", max_length=300, blank=True,
    )
    proposed_dosage = models.CharField(
        "Önerilen doz", max_length=200, blank=True,
    )
    consultant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="mix_design_consultations",
        verbose_name="Teknik danışman",
    )
    report = models.FileField(
        "Öneri raporu (PDF)", upload_to="mix_designs/%Y/",
        null=True, blank=True,
    )
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.REQUESTED,
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Mix Design Consultation"
        verbose_name_plural = "Mix Design Consultations"
        ordering = ["-request_date"]

    def __str__(self) -> str:
        return f"{self.consultation_number} · {self.customer.code} · {self.project_name}"


class ApplicatorTraining(TimeStamped):
    """Uygulayıcı eğitim izleri — müşterinin saha ekibine ürün kullanımı eğitimi.

    Sika/Chryso: dozaj + karıştırma prosedürü + güvenlik eğitimi verilir,
    katılımcı listesi ve sertifika kaydı tutulur.
    """

    training_number = models.CharField("Training No", max_length=40, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name="applicator_trainings",
    )
    training_date = models.DateField("Eğitim tarihi")
    location = models.CharField("Yer", max_length=200)
    topics = models.TextField(
        "Konu başlıkları",
        help_text="Örn. dozaj kalibrasyonu, slump yönetimi, güvenlik prosedürleri.",
    )
    products_covered = models.CharField(
        "İşlenen ürünler", max_length=300, blank=True,
    )
    participant_count = models.PositiveIntegerField("Katılımcı sayısı", default=0)
    participant_list = models.TextField(
        "Katılımcı listesi", blank=True,
        help_text="Her satır bir kişi (ad soyad · görev)",
    )
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="trainings_delivered",
        verbose_name="Eğitmen",
    )
    duration_hours = models.DecimalField(
        "Süre (saat)", max_digits=4, decimal_places=1, default=0,
    )
    certificate_issued = models.BooleanField(
        "Katılım belgesi verildi", default=False,
    )
    certificate_file = models.FileField(
        "Toplu katılım belgesi (PDF)", upload_to="trainings/%Y/",
        null=True, blank=True,
    )
    feedback_score = models.DecimalField(
        "Geri bildirim puanı (1-5)", max_digits=3, decimal_places=1,
        null=True, blank=True,
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Applicator Training"
        verbose_name_plural = "Applicator Trainings"
        ordering = ["-training_date"]

    def __str__(self) -> str:
        return f"{self.training_number} · {self.customer.code} · {self.training_date}"


class PerformanceWarranty(TimeStamped):
    """Ürün performans garantisi — ürün+müşteri+proje bazında yazılı garanti.

    Sika: 60+ ülkede sistem garantisi (10-25 yıl). Belge ürünün beklenen
    dayanıklılığını, koşullarını ve garantiyi kapsar.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Aktif"
        EXPIRED = "EXPIRED", "Süresi doldu"
        CLAIMED = "CLAIMED", "Talep açıldı"
        VOIDED = "VOIDED", "Geçersiz kılındı"

    warranty_number = models.CharField("Warranty No", max_length=40, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name="warranties",
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name="warranties",
    )
    project_name = models.CharField("Proje adı", max_length=200)
    project_location = models.CharField("Proje konumu", max_length=200, blank=True)
    quantity_supplied = models.DecimalField(
        "Teslim edilen miktar", max_digits=12, decimal_places=2,
    )
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT,
        related_name="warranty_units",
    )
    warranty_start = models.DateField("Garanti başlangıcı")
    warranty_end = models.DateField("Garanti sonu")
    coverage_summary = models.TextField(
        "Kapsam özeti",
        help_text="Örn. 25 yıl dayanıklılık, dosaj koşulları, güvenlik sınırları.",
    )
    exclusions = models.TextField(
        "Hariç durumlar", blank=True,
        help_text="Yanlış uygulama, uygun olmayan koşullar vb.",
    )
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="warranties_signed", verbose_name="İmza sahibi",
    )
    signed_at = models.DateTimeField("İmza zamanı", null=True, blank=True)
    document = models.FileField(
        "Garanti belgesi (PDF)", upload_to="warranties/%Y/",
        null=True, blank=True,
    )
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.ACTIVE,
    )

    class Meta:
        verbose_name = "Performance Warranty"
        verbose_name_plural = "Performance Warranties"
        ordering = ["-warranty_start"]

    def __str__(self) -> str:
        return f"{self.warranty_number} · {self.customer.code} · {self.project_name}"


# ---------------------------------------------------------------------------
# Sprint 11 — Fleet Management (Truck + DeliveryTrip + GPS)
# ---------------------------------------------------------------------------

class Truck(TimeStamped):
    """Filo aracı — kimyasal katkı sevkiyat kamyonu."""

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Müsait"
        LOADING = "LOADING", "Yükleniyor"
        EN_ROUTE = "EN_ROUTE", "Yolda"
        UNLOADING = "UNLOADING", "Boşaltılıyor"
        MAINTENANCE = "MAINTENANCE", "Bakımda"
        OUT_OF_SERVICE = "OUT", "Servis dışı"

    class Type(models.TextChoices):
        TANKER = "TANKER", "Tanker (dökme sıvı)"
        FLATBED = "FLATBED", "Platform (IBC)"
        VAN = "VAN", "Kamyonet (paket)"
        REEFER = "REEFER", "Soğutmalı"

    plate_number = models.CharField("Plaka", max_length=30, unique=True)
    truck_type = models.CharField(
        "Tip", max_length=10, choices=Type.choices,
    )
    capacity_kg = models.DecimalField(
        "Kapasite (kg)", max_digits=10, decimal_places=2,
    )
    make_model = models.CharField("Marka/model", max_length=120, blank=True)
    year = models.PositiveIntegerField("Yıl", null=True, blank=True)
    driver_default = models.CharField(
        "Varsayılan şoför", max_length=200, blank=True,
    )
    driver_phone = models.CharField("Şoför telefonu", max_length=30, blank=True)
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.AVAILABLE,
    )
    gps_device_id = models.CharField(
        "GPS cihaz ID", max_length=80, blank=True,
        help_text="Filo takip cihazı ID — API sorgu anahtarı.",
    )
    last_maintenance = models.DateField("Son bakım", null=True, blank=True)
    next_maintenance = models.DateField("Sonraki bakım", null=True, blank=True)
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Truck (Camion)"
        verbose_name_plural = "Trucks (Camions)"
        ordering = ["plate_number"]

    def __str__(self) -> str:
        return f"{self.plate_number} · {self.get_truck_type_display()}"


class DeliveryTrip(TimeStamped):
    """Sevkiyat seferi — BL Client'a bağlı taşıma turu."""

    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Planlandı"
        LOADED = "LOADED", "Yüklendi"
        DEPARTED = "DEPARTED", "Yola çıktı"
        ARRIVED = "ARRIVED", "Teslim yerine ulaştı"
        DELIVERED = "DELIVERED", "Teslim edildi"
        RETURNED = "RETURNED", "Geri döndü"
        CANCELLED = "CANCELLED", "İptal"

    trip_number = models.CharField("Trip No", max_length=40, unique=True)
    shipment = models.OneToOneField(
        Shipment, on_delete=models.PROTECT,
        related_name="delivery_trip",
        verbose_name="BL Client",
    )
    truck = models.ForeignKey(
        Truck, on_delete=models.PROTECT,
        related_name="trips", verbose_name="Kamyon",
    )
    driver_name = models.CharField("Şoför", max_length=200, blank=True)
    driver_phone = models.CharField("Şoför telefonu", max_length=30, blank=True)
    scheduled_departure = models.DateTimeField("Planlanan çıkış")
    actual_departure = models.DateTimeField("Gerçek çıkış", null=True, blank=True)
    scheduled_arrival = models.DateTimeField("Planlanan varış")
    actual_arrival = models.DateTimeField("Gerçek varış", null=True, blank=True)
    delivery_completed_at = models.DateTimeField(
        "Teslim tamamlandı", null=True, blank=True,
    )
    origin_address = models.CharField(
        "Yükleme yeri", max_length=300,
        default="Fabrika — Zone industrielle Rouiba, Alger",
    )
    destination_address = models.CharField(
        "Teslim yeri", max_length=300,
    )
    distance_km = models.DecimalField(
        "Mesafe (km)", max_digits=6, decimal_places=1, null=True, blank=True,
    )
    fuel_cost = models.DecimalField(
        "Yakıt gideri (DZD)", max_digits=10, decimal_places=2, null=True, blank=True,
    )
    # 90-dk kritik pencere için son GPS
    last_gps_lat = models.DecimalField(
        "Son GPS enlem", max_digits=9, decimal_places=6, null=True, blank=True,
    )
    last_gps_lng = models.DecimalField(
        "Son GPS boylam", max_digits=9, decimal_places=6, null=True, blank=True,
    )
    last_gps_timestamp = models.DateTimeField(
        "Son GPS zamanı", null=True, blank=True,
    )
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.SCHEDULED,
    )
    proof_of_delivery = models.FileField(
        "POD (imzalı belge)", upload_to="pods/%Y/%m/",
        null=True, blank=True,
    )
    signature_name = models.CharField(
        "Teslim alan (ad soyad)", max_length=200, blank=True,
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Delivery Trip"
        verbose_name_plural = "Delivery Trips"
        ordering = ["-scheduled_departure"]

    def __str__(self) -> str:
        return f"{self.trip_number} · {self.truck.plate_number} · {self.get_status_display()}"

    @property
    def is_delayed(self) -> bool:
        """Planlanan varış geçti mi ve teslim edilmedi mi?"""
        from django.utils import timezone
        if self.status in (self.Status.DELIVERED, self.Status.CANCELLED, self.Status.RETURNED):
            return False
        return timezone.now() > self.scheduled_arrival

    @property
    def elapsed_minutes_from_load(self):
        """Yüklemeden bu yana geçen dakika — 90 dk kritik pencere için."""
        from django.utils import timezone
        if not self.actual_departure:
            return None
        end = self.delivery_completed_at or timezone.now()
        delta = end - self.actual_departure
        return int(delta.total_seconds() / 60)
