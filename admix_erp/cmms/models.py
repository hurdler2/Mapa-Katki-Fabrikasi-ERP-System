"""CMMS modelleri: ekipman, yedek parça, bakım planı, iş emri, kalibrasyon.

ISO 9001:2015 §7.1.5.2 — İzleme ve ölçme kaynakları (kalibrasyon zorunluluğu).
ISO 45001 / 14001 — kritik ekipmanların bakımı EHS aksiyonlarını da kapsar.
"""
from __future__ import annotations

import datetime as dt

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from common.models import TimeStamped
from masterdata.models import Container
from qms.models import CAPA, Nonconformance


# ---------------------------------------------------------------------------
# Yedek parça
# ---------------------------------------------------------------------------

class SparePart(TimeStamped):
    """Bakım yedek parça envanteri."""

    code = models.CharField("Kod", max_length=40, unique=True)
    name = models.CharField("Ad", max_length=200)
    description = models.TextField("Açıklama", blank=True)
    unit = models.CharField("Birim", max_length=20, default="adet")
    manufacturer = models.CharField("Üretici", max_length=120, blank=True)
    manufacturer_part_no = models.CharField("Üretici P/N", max_length=80, blank=True)
    current_stock = models.DecimalField(
        "Mevcut stok", max_digits=12, decimal_places=3, default=0
    )
    min_stock = models.DecimalField(
        "Minimum stok", max_digits=12, decimal_places=3, default=0
    )
    reorder_point = models.DecimalField(
        "Yeniden sipariş noktası", max_digits=12, decimal_places=3, default=0
    )
    unit_cost = models.DecimalField(
        "Birim maliyet", max_digits=12, decimal_places=4, default=0
    )
    storage_location = models.CharField("Saklama yeri", max_length=120, blank=True)
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Yedek Parça"
        verbose_name_plural = "Yedek Parçalar"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"

    @property
    def below_min(self) -> bool:
        return self.current_stock < self.min_stock


# ---------------------------------------------------------------------------
# Ekipman
# ---------------------------------------------------------------------------

class Equipment(TimeStamped):
    """Ekipman envanteri — reaktör, terazi, pompa, vana, tank vb. Hiyerarşik."""

    class Category(models.TextChoices):
        REACTOR = "REACTOR", "Reaktör"
        BALANCE = "BALANCE", "Terazi / Yük hücresi"
        PUMP = "PUMP", "Pompa"
        VALVE = "VALVE", "Vana"
        TANK = "TANK", "Tank"
        SENSOR = "SENSOR", "Sensör"
        MIXER = "MIXER", "Karıştırıcı"
        CONVEYOR = "CONVEYOR", "Konveyör"
        PIPELINE = "PIPELINE", "Boru hattı"
        FILTER = "FILTER", "Filtre"
        HEAT_EXCHANGER = "HEAT_EXCHANGER", "Isı değiştirici"
        COMPRESSOR = "COMPRESSOR", "Kompresör"
        MOTOR = "MOTOR", "Motor"
        PLC_HMI = "PLC_HMI", "PLC / HMI"
        LAB_INSTRUMENT = "LAB_INSTRUMENT", "Laboratuvar cihazı"
        UTILITY = "UTILITY", "Yardımcı işletme"
        OTHER = "OTHER", "Diğer"

    class Criticality(models.TextChoices):
        A_CRITICAL = "A", "A - Kritik (üretim/güvenlik durur)"
        B_IMPORTANT = "B", "B - Önemli (kısmi etki)"
        C_STANDARD = "C", "C - Standart"

    class Status(models.TextChoices):
        OPERATIONAL = "OPERATIONAL", "Çalışıyor"
        UNDER_MAINTENANCE = "UNDER_MAINTENANCE", "Bakımda"
        OUT_OF_SERVICE = "OUT_OF_SERVICE", "Servis dışı"
        DECOMMISSIONED = "DECOMMISSIONED", "Hurdaya ayrıldı"
        STANDBY = "STANDBY", "Yedek / bekleme"

    equipment_number = models.CharField("Ekipman No", max_length=40, unique=True)
    name = models.CharField("Ad", max_length=200)
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="equipment",
        verbose_name="İş Kolu",
    )
    category = models.CharField("Kategori", max_length=20, choices=Category.choices)
    criticality = models.CharField(
        "Kritiklik (ABC)", max_length=1, choices=Criticality.choices,
        default=Criticality.C_STANDARD,
    )
    status = models.CharField(
        "Durum", max_length=20, choices=Status.choices, default=Status.OPERATIONAL
    )
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children", verbose_name="Üst ekipman",
    )
    container = models.ForeignKey(
        Container, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="equipment", verbose_name="Bağlı kap",
        help_text="Reaktör/tank ekipmanı Container'a bağlanabilir.",
    )
    location = models.CharField("Yer / bölge", max_length=200, blank=True)

    manufacturer = models.CharField("Üretici", max_length=120, blank=True)
    model = models.CharField("Model", max_length=120, blank=True)
    serial_no = models.CharField("Seri no", max_length=80, blank=True)
    install_date = models.DateField("Kurulum tarihi", null=True, blank=True)
    commissioning_date = models.DateField("Devreye alma tarihi", null=True, blank=True)
    warranty_end = models.DateField("Garanti sonu", null=True, blank=True)

    manual_reference = models.CharField(
        "Kullanım kılavuzu ref.", max_length=200, blank=True,
        help_text="SOP no / dosya URL",
    )
    is_measuring_device = models.BooleanField(
        "Ölçüm cihazı mı?", default=False,
        help_text="ISO 9001 §7.1.5.2 kapsamındaysa kalibrasyon zorunlu.",
    )
    spare_parts = models.ManyToManyField(
        SparePart, blank=True, through="EquipmentSparePart",
        related_name="equipment", verbose_name="Yedek parçalar",
    )
    responsible_department = models.CharField(
        "Sorumlu departman", max_length=60, blank=True
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Ekipman"
        verbose_name_plural = "Ekipmanlar"
        ordering = ["equipment_number"]

    def __str__(self) -> str:
        return f"{self.equipment_number} · {self.name}"


class EquipmentSparePart(TimeStamped):
    """Ekipman × yedek parça (BOM). Bir ekipmanın gerektirdiği parça listesi."""

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name="part_lines"
    )
    spare_part = models.ForeignKey(SparePart, on_delete=models.PROTECT)
    quantity = models.DecimalField("Adet", max_digits=8, decimal_places=2, default=1)
    position = models.CharField(
        "Pozisyon / konum", max_length=100, blank=True,
        help_text="Ekipman üzerindeki yeri (örn. Sol pompa contası)",
    )

    class Meta:
        verbose_name = "Ekipman Yedek Parçası"
        verbose_name_plural = "Ekipman Yedek Parçaları"
        unique_together = (("equipment", "spare_part", "position"),)

    def __str__(self) -> str:
        return f"{self.equipment.equipment_number} → {self.spare_part.code} × {self.quantity}"


# ---------------------------------------------------------------------------
# Önleyici bakım planı (PM)
# ---------------------------------------------------------------------------

class MaintenancePlan(TimeStamped):
    """Bir ekipman için düzenli önleyici bakım (PM) planı."""

    class Frequency(models.TextChoices):
        DAILY = "DAILY", "Günlük"
        WEEKLY = "WEEKLY", "Haftalık"
        MONTHLY = "MONTHLY", "Aylık"
        QUARTERLY = "QUARTERLY", "Üç aylık"
        SEMI_ANNUAL = "SEMI_ANNUAL", "Altı aylık"
        ANNUAL = "ANNUAL", "Yıllık"
        CUSTOM = "CUSTOM", "Özel (gün)"

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE,
        related_name="maintenance_plans", verbose_name="Ekipman",
    )
    plan_code = models.CharField("Plan kodu", max_length=40, unique=True)
    name = models.CharField("Ad", max_length=200)
    description = models.TextField("Açıklama", blank=True)
    frequency = models.CharField(
        "Frekans", max_length=12, choices=Frequency.choices, default=Frequency.MONTHLY
    )
    interval_days = models.PositiveIntegerField(
        "Aralık (gün)", null=True, blank=True,
        help_text="Frekans CUSTOM ise dolu, aksi halde otomatik hesaplanır.",
    )
    task_checklist = models.TextField(
        "Görev kontrol listesi",
        help_text="Her satır bir kontrol adımı.",
    )
    estimated_hours = models.DecimalField(
        "Tahmini süre (saat)", max_digits=6, decimal_places=2, default=1
    )
    responsible_group = models.CharField("Sorumlu grup", max_length=60, blank=True)
    last_generated_on = models.DateField(
        "Son üretilen WO tarihi", null=True, blank=True,
        help_text="`generate_pm_work_orders` bunu günceller.",
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Bakım Planı (PM)"
        verbose_name_plural = "Bakım Planları"
        ordering = ["equipment", "plan_code"]

    def __str__(self) -> str:
        return f"{self.plan_code} · {self.name}"

    @property
    def days_between_wo(self) -> int:
        mapping = {
            MaintenancePlan.Frequency.DAILY: 1,
            MaintenancePlan.Frequency.WEEKLY: 7,
            MaintenancePlan.Frequency.MONTHLY: 30,
            MaintenancePlan.Frequency.QUARTERLY: 90,
            MaintenancePlan.Frequency.SEMI_ANNUAL: 180,
            MaintenancePlan.Frequency.ANNUAL: 365,
        }
        if self.frequency == MaintenancePlan.Frequency.CUSTOM:
            return self.interval_days or 0
        return mapping.get(self.frequency, 30)

    @property
    def next_due_date(self) -> dt.date:
        base = self.last_generated_on or self.created_at.date()
        return base + dt.timedelta(days=self.days_between_wo)


# ---------------------------------------------------------------------------
# İş Emri (Work Order)
# ---------------------------------------------------------------------------

class WorkOrder(TimeStamped):
    """Bakım iş emri — PM, arıza (CM), kalibrasyon, muayene, acil."""

    class Type(models.TextChoices):
        PREVENTIVE = "PREVENTIVE", "Önleyici (PM)"
        CORRECTIVE = "CORRECTIVE", "Düzeltici (CM / arıza)"
        PREDICTIVE = "PREDICTIVE", "Kestirimci (PdM)"
        EMERGENCY = "EMERGENCY", "Acil"
        CALIBRATION = "CALIBRATION", "Kalibrasyon"
        INSPECTION = "INSPECTION", "Muayene"
        MODIFICATION = "MODIFICATION", "Modifikasyon"

    class Priority(models.TextChoices):
        LOW = "LOW", "Düşük"
        MEDIUM = "MEDIUM", "Orta"
        HIGH = "HIGH", "Yüksek"
        URGENT = "URGENT", "Acil"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Açık"
        ASSIGNED = "ASSIGNED", "Atandı"
        IN_PROGRESS = "IN_PROGRESS", "Devam ediyor"
        ON_HOLD = "ON_HOLD", "Beklemede"
        COMPLETED = "COMPLETED", "Tamamlandı"
        CANCELLED = "CANCELLED", "İptal"

    work_order_number = models.CharField("İş emri no", max_length=40, unique=True)
    type = models.CharField("Tip", max_length=14, choices=Type.choices)
    priority = models.CharField(
        "Öncelik", max_length=8, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        "Durum", max_length=14, choices=Status.choices, default=Status.OPEN
    )
    equipment = models.ForeignKey(
        Equipment, on_delete=models.PROTECT,
        related_name="work_orders", verbose_name="Ekipman",
    )
    plan = models.ForeignKey(
        MaintenancePlan, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="work_orders", verbose_name="PM planı",
    )

    title = models.CharField("Başlık", max_length=200)
    description = models.TextField("Açıklama", blank=True)
    failure_description = models.TextField(
        "Arıza tanımı", blank=True,
        help_text="Corrective tipinde arızayı tarif eder.",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="requested_wos", verbose_name="Talep eden",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_wos", verbose_name="Atanan teknisyen",
    )

    scheduled_start = models.DateTimeField("Planlı başlangıç", null=True, blank=True)
    scheduled_end = models.DateTimeField("Planlı bitiş", null=True, blank=True)
    actual_start = models.DateTimeField("Gerçek başlangıç", null=True, blank=True)
    actual_end = models.DateTimeField("Gerçek bitiş", null=True, blank=True)

    downtime_hours = models.DecimalField(
        "Duruş süresi (saat)", max_digits=8, decimal_places=2, default=0,
        help_text="Ekipman üretim dışı kaldığı süre — MTTR hesabında kullanılır.",
    )
    labor_hours = models.DecimalField(
        "İşçilik (saat)", max_digits=8, decimal_places=2, default=0
    )
    labor_cost = models.DecimalField(
        "İşçilik maliyeti", max_digits=12, decimal_places=2, default=0
    )
    parts_cost = models.DecimalField(
        "Parça maliyeti", max_digits=12, decimal_places=2, default=0
    )

    completion_notes = models.TextField("Tamamlama notları", blank=True)
    ncr = models.ForeignKey(
        Nonconformance, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="work_orders", verbose_name="Bağlı NCR",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "İş Emri"
        verbose_name_plural = "İş Emirleri"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.work_order_number} · {self.equipment.equipment_number}"

    @property
    def total_cost(self):
        return (self.labor_cost or 0) + (self.parts_cost or 0)


class SparePartConsumption(TimeStamped):
    """İş emrinde harcanan yedek parça."""

    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE,
        related_name="parts_used", verbose_name="İş emri",
    )
    spare_part = models.ForeignKey(
        SparePart, on_delete=models.PROTECT,
        related_name="consumptions", verbose_name="Yedek parça",
    )
    quantity = models.DecimalField("Miktar", max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField(
        "Birim maliyet", max_digits=12, decimal_places=4, default=0
    )
    consumed_at = models.DateTimeField("Harcama zamanı", auto_now_add=True)

    class Meta:
        verbose_name = "Parça Sarfı"
        verbose_name_plural = "Parça Sarfları"

    def __str__(self) -> str:
        return f"{self.work_order.work_order_number} · {self.spare_part.code} × {self.quantity}"

    @property
    def line_cost(self):
        return self.quantity * self.unit_cost


# ---------------------------------------------------------------------------
# Kalibrasyon (ISO 9001 §7.1.5.2)
# ---------------------------------------------------------------------------

class CalibrationSchedule(TimeStamped):
    """Bir ölçüm cihazı için kalibrasyon planı."""

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE,
        related_name="calibration_schedules", verbose_name="Ekipman",
        limit_choices_to={"is_measuring_device": True},
    )
    parameter = models.CharField(
        "Parametre", max_length=120,
        help_text="Örn. Ağırlık (0-100 kg), pH (0-14), Sıcaklık (0-200°C)",
    )
    reference_standard = models.CharField(
        "Referans standart", max_length=200, blank=True,
        help_text="EN ISO 376 (kuvvet), EN ISO 4787 (hacim), OIML R76 (terazi)...",
    )
    method = models.CharField("Metot", max_length=200, blank=True)
    tolerance = models.CharField(
        "Tolerans", max_length=80,
        help_text="Örn. ±0.5%, ±0.01 pH, ±0.5°C",
    )
    interval_days = models.PositiveIntegerField(
        "Aralık (gün)", default=365,
        help_text="Kalibrasyon periyodu.",
    )
    external_lab_required = models.BooleanField(
        "Harici akredite lab. gerekli", default=False,
        help_text="ALGERAC / EA akrediteli lab. zorunlu",
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="calibration_schedules", verbose_name="Sorumlu",
    )
    last_calibrated_on = models.DateField("Son kalibrasyon", null=True, blank=True)
    next_due_date = models.DateField(
        "Sonraki kalibrasyon", null=True, blank=True,
        help_text="Otomatik hesaplanır; last + interval",
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Kalibrasyon Planı"
        verbose_name_plural = "Kalibrasyon Planları"
        unique_together = (("equipment", "parameter"),)
        ordering = ["next_due_date", "equipment"]

    def __str__(self) -> str:
        return f"CAL {self.equipment.equipment_number} · {self.parameter}"

    def recompute_next(self) -> None:
        if self.last_calibrated_on:
            self.next_due_date = self.last_calibrated_on + dt.timedelta(days=self.interval_days)


class CalibrationRecord(TimeStamped):
    """Kalibrasyon icra kaydı — as-found / as-left ölçümleri + sertifika."""

    class Result(models.TextChoices):
        PASS = "PASS", "Geçti"
        FAIL = "FAIL", "Başarısız"
        CONDITIONAL = "CONDITIONAL", "Şartlı geçti (ayar yapıldı)"
        SUSPECT = "SUSPECT", "Şüpheli (tekrarlanmalı)"

    schedule = models.ForeignKey(
        CalibrationSchedule, on_delete=models.PROTECT,
        related_name="records", verbose_name="Kalibrasyon planı",
    )
    performed_at = models.DateField("İcra tarihi")
    performed_by = models.CharField(
        "İcra eden (kişi/kuruluş)", max_length=200,
        help_text="Kendi personel veya akredite lab. adı",
    )
    performed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="performed_calibrations", verbose_name="İcra eden (sistem kullanıcı)",
    )
    is_external = models.BooleanField("Harici lab. tarafından", default=False)
    certificate_number = models.CharField("Sertifika No", max_length=80, blank=True)
    certificate_file = models.FileField(
        "Sertifika PDF", upload_to="calibration/%Y/", null=True, blank=True
    )

    # As-found: kalibrasyon öncesi ölçüm; As-left: sonrası
    as_found = models.JSONField("As-Found ölçümler", default=dict, blank=True)
    as_left = models.JSONField("As-Left ölçümler", default=dict, blank=True)
    uncertainty = models.CharField(
        "Belirsizlik (U)", max_length=60, blank=True,
        help_text="Örn. ±0.02 pH (k=2)",
    )

    result = models.CharField("Sonuç", max_length=12, choices=Result.choices)
    notes = models.TextField("Notlar", blank=True)
    ncr = models.ForeignKey(
        Nonconformance, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="calibration_records", verbose_name="FAIL için açılan NCR",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Kalibrasyon Kaydı"
        verbose_name_plural = "Kalibrasyon Kayıtları"
        ordering = ["-performed_at"]

    def __str__(self) -> str:
        return f"{self.schedule} @ {self.performed_at} → {self.result}"


# ---------------------------------------------------------------------------
# Sprint 11 — SCADA sensor alert → CMMS auto work order köprüsü
# ---------------------------------------------------------------------------

class SensorAlert(TimeStamped):
    """SCADA sensöründen gelen anomali/eşik ihlali uyarısı.

    Kritik uyarılar otomatik olarak CMMS'te WorkOrder açar (BR bağı).
    Örn: reaktör sıcaklık > 85°C → HIGH priority CORRECTIVE work order.
    """

    class Severity(models.TextChoices):
        INFO = "INFO", "Bilgi"
        WARNING = "WARNING", "Uyarı"
        CRITICAL = "CRITICAL", "Kritik"

    class Status(models.TextChoices):
        NEW = "NEW", "Yeni"
        ACK = "ACK", "Onaylandı (kabul)"
        WO_CREATED = "WO_CREATED", "İş emri açıldı"
        RESOLVED = "RESOLVED", "Çözüldü"
        IGNORED = "IGNORED", "Görmezden gelindi"

    alert_number = models.CharField("Alert No", max_length=40, unique=True)
    equipment = models.ForeignKey(
        Equipment, on_delete=models.PROTECT,
        related_name="sensor_alerts", verbose_name="Ekipman",
    )
    sensor_tag = models.CharField(
        "Sensor tag", max_length=80,
        help_text="SCADA sensör etiketi (Ör. R101.TEMP.OUT).",
    )
    parameter = models.CharField(
        "Ölçüm parametresi", max_length=60,
        help_text="Ör. Temperature, Pressure, RPM, Flow rate.",
    )
    measured_value = models.DecimalField(
        "Ölçüm değeri", max_digits=12, decimal_places=4,
    )
    threshold_low = models.DecimalField(
        "Alt eşik", max_digits=12, decimal_places=4, null=True, blank=True,
    )
    threshold_high = models.DecimalField(
        "Üst eşik", max_digits=12, decimal_places=4, null=True, blank=True,
    )
    unit = models.CharField("Birim", max_length=20, blank=True)
    detected_at = models.DateTimeField("Tespit zamanı")
    severity = models.CharField(
        "Şiddet", max_length=8, choices=Severity.choices,
        default=Severity.WARNING,
    )
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.NEW,
    )
    auto_work_order = models.ForeignKey(
        WorkOrder, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="triggered_by_alert",
        verbose_name="Otomatik açılan iş emri",
    )
    resolved_at = models.DateTimeField("Çözüm zamanı", null=True, blank=True)
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Sensor Alert"
        verbose_name_plural = "Sensor Alerts"
        ordering = ["-detected_at"]

    def __str__(self) -> str:
        return f"{self.alert_number} · {self.sensor_tag}={self.measured_value} · {self.severity}"
