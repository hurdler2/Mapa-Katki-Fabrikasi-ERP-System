"""CMMS servisleri: WO yaşam döngüsü, PM üretici, MTBF/MTTR, kalibrasyon."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from qms.services import open_ncr

from .models import (
    CalibrationRecord,
    CalibrationSchedule,
    Equipment,
    MaintenancePlan,
    SparePart,
    SparePartConsumption,
    WorkOrder,
)


# ---------------------------------------------------------------------------
# İş emri yaşam döngüsü
# ---------------------------------------------------------------------------

@transaction.atomic
def create_work_order(
    *,
    work_order_number: str,
    type: str,
    equipment: Equipment,
    title: str,
    requested_by,
    priority: str = WorkOrder.Priority.MEDIUM,
    description: str = "",
    failure_description: str = "",
    plan: MaintenancePlan | None = None,
    scheduled_start=None,
    scheduled_end=None,
    assigned_to=None,
) -> WorkOrder:
    wo = WorkOrder.objects.create(
        work_order_number=work_order_number,
        type=type,
        priority=priority,
        equipment=equipment,
        plan=plan,
        title=title,
        description=description,
        failure_description=failure_description,
        requested_by=requested_by,
        assigned_to=assigned_to,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        status=(WorkOrder.Status.ASSIGNED if assigned_to else WorkOrder.Status.OPEN),
    )

    # Corrective / Emergency: ekipmanı otomatik bakımda göster
    if type in {WorkOrder.Type.CORRECTIVE, WorkOrder.Type.EMERGENCY}:
        equipment.status = Equipment.Status.UNDER_MAINTENANCE
        equipment.save(update_fields=["status", "updated_at"])

    return wo


@transaction.atomic
def assign_work_order(wo: WorkOrder, *, technician) -> WorkOrder:
    if wo.status not in {WorkOrder.Status.OPEN, WorkOrder.Status.ASSIGNED,
                         WorkOrder.Status.ON_HOLD}:
        raise ValidationError("İş emri atanabilir durumda değil.")
    wo.assigned_to = technician
    wo.status = WorkOrder.Status.ASSIGNED
    wo.save(update_fields=["assigned_to", "status", "updated_at"])
    return wo


@transaction.atomic
def start_work_order(wo: WorkOrder) -> WorkOrder:
    if wo.status not in {WorkOrder.Status.OPEN, WorkOrder.Status.ASSIGNED,
                         WorkOrder.Status.ON_HOLD}:
        raise ValidationError("İş emri başlatılamaz durumda.")
    if wo.assigned_to is None:
        raise ValidationError("İş emri atanmadan başlatılamaz.")
    wo.status = WorkOrder.Status.IN_PROGRESS
    wo.actual_start = timezone.now()
    wo.save(update_fields=["status", "actual_start", "updated_at"])
    return wo


@transaction.atomic
def consume_part(
    wo: WorkOrder, *, spare_part: SparePart, quantity, unit_cost=None
) -> SparePartConsumption:
    if wo.status != WorkOrder.Status.IN_PROGRESS:
        raise ValidationError("Yalnız IN_PROGRESS iş emrine parça harcanabilir.")
    quantity = Decimal(quantity)
    if spare_part.current_stock < quantity:
        raise ValidationError(
            f"Yedek parça stoğu yetersiz: {spare_part.code} istenen={quantity}"
        )
    unit_cost = Decimal(unit_cost) if unit_cost is not None else spare_part.unit_cost
    cons = SparePartConsumption.objects.create(
        work_order=wo, spare_part=spare_part,
        quantity=quantity, unit_cost=unit_cost,
    )
    spare_part.current_stock = spare_part.current_stock - quantity
    spare_part.save(update_fields=["current_stock", "updated_at"])

    wo.parts_cost = (wo.parts_cost or 0) + (quantity * unit_cost)
    wo.save(update_fields=["parts_cost", "updated_at"])
    return cons


@transaction.atomic
def complete_work_order(
    wo: WorkOrder,
    *,
    completion_notes: str = "",
    downtime_hours: float | None = None,
    labor_hours: float | None = None,
    labor_cost: float | None = None,
    restore_equipment: bool = True,
) -> WorkOrder:
    if wo.status != WorkOrder.Status.IN_PROGRESS:
        raise ValidationError("Yalnız IN_PROGRESS iş emri tamamlanabilir.")
    wo.status = WorkOrder.Status.COMPLETED
    wo.actual_end = timezone.now()
    if completion_notes:
        wo.completion_notes = completion_notes
    if downtime_hours is not None:
        wo.downtime_hours = Decimal(str(downtime_hours))
    if labor_hours is not None:
        wo.labor_hours = Decimal(str(labor_hours))
    if labor_cost is not None:
        wo.labor_cost = Decimal(str(labor_cost))
    wo.save(update_fields=[
        "status", "actual_end", "completion_notes",
        "downtime_hours", "labor_hours", "labor_cost", "updated_at",
    ])

    if restore_equipment and wo.equipment.status == Equipment.Status.UNDER_MAINTENANCE:
        wo.equipment.status = Equipment.Status.OPERATIONAL
        wo.equipment.save(update_fields=["status", "updated_at"])
    return wo


# ---------------------------------------------------------------------------
# Önleyici bakım üretici
# ---------------------------------------------------------------------------

@transaction.atomic
def generate_pm_work_orders(
    *,
    as_of: dt.date | None = None,
    requested_by,
) -> list[WorkOrder]:
    """Vadesi gelmiş / geçmiş aktif PM'ler için iş emri üretir.

    Aynı gün için mükerrer WO oluşturmaz.
    """
    as_of = as_of or dt.date.today()
    created: list[WorkOrder] = []
    plans = MaintenancePlan.objects.filter(is_active=True).select_related("equipment")
    for plan in plans:
        if plan.next_due_date > as_of:
            continue
        # Aynı plan için o gün bir WO var mı?
        exists = WorkOrder.objects.filter(
            plan=plan, created_at__date=as_of,
        ).exists()
        if exists:
            continue
        wo_number = f"PM-{plan.plan_code}-{as_of.strftime('%Y%m%d')}"
        wo = create_work_order(
            work_order_number=wo_number,
            type=WorkOrder.Type.PREVENTIVE,
            equipment=plan.equipment,
            plan=plan,
            title=plan.name,
            description=plan.task_checklist,
            requested_by=requested_by,
            priority=WorkOrder.Priority.MEDIUM,
            scheduled_start=timezone.now(),
        )
        plan.last_generated_on = as_of
        plan.save(update_fields=["last_generated_on", "updated_at"])
        created.append(wo)
    return created


# ---------------------------------------------------------------------------
# Bakım metrikleri (MTBF / MTTR)
# ---------------------------------------------------------------------------

def calculate_mtbf_mttr(
    equipment: Equipment,
    *,
    since: dt.date | None = None,
    until: dt.date | None = None,
) -> dict:
    """Belirtilen aralıkta ekipmanın MTBF ve MTTR değerlerini hesaplar.

    MTBF = toplam çalışma süresi / arıza sayısı
    MTTR = toplam onarım süresi / arıza sayısı
    """
    qs = equipment.work_orders.filter(
        type=WorkOrder.Type.CORRECTIVE,
        status=WorkOrder.Status.COMPLETED,
    )
    if since:
        qs = qs.filter(actual_end__date__gte=since)
    if until:
        qs = qs.filter(actual_end__date__lte=until)

    failures = qs.count()
    total_downtime = qs.aggregate(t=Sum("downtime_hours"))["t"] or Decimal("0")

    # Aralık toplam saati (varsayılan 30 gün = 720 saat)
    period_start = since or (equipment.install_date or (dt.date.today() - dt.timedelta(days=30)))
    period_end = until or dt.date.today()
    period_hours = Decimal((period_end - period_start).days * 24)

    if failures == 0:
        return {
            "failures": 0,
            "period_hours": period_hours,
            "downtime_hours": total_downtime,
            "uptime_hours": period_hours - total_downtime,
            "mtbf_hours": None,
            "mttr_hours": None,
            "availability_pct": None if period_hours == 0
                else float((period_hours - total_downtime) / period_hours * 100),
        }

    uptime = period_hours - total_downtime
    return {
        "failures": failures,
        "period_hours": period_hours,
        "downtime_hours": total_downtime,
        "uptime_hours": uptime,
        "mtbf_hours": float(uptime / failures) if failures else None,
        "mttr_hours": float(total_downtime / failures) if failures else None,
        "availability_pct": float(uptime / period_hours * 100) if period_hours > 0 else None,
    }


# ---------------------------------------------------------------------------
# Kalibrasyon
# ---------------------------------------------------------------------------

@transaction.atomic
def record_calibration(
    schedule: CalibrationSchedule,
    *,
    performed_at: dt.date,
    performed_by: str,
    result: str,
    as_found: dict | None = None,
    as_left: dict | None = None,
    certificate_number: str = "",
    is_external: bool = False,
    uncertainty: str = "",
    notes: str = "",
    performed_by_user=None,
) -> CalibrationRecord:
    """Kalibrasyon icra kaydı yaz + planı güncelle.

    FAIL veya SUSPECT sonucunda otomatik NCR açar; ekipmanı UNDER_MAINTENANCE'a çeker.
    """
    record = CalibrationRecord.objects.create(
        schedule=schedule,
        performed_at=performed_at,
        performed_by=performed_by,
        performed_by_user=performed_by_user,
        is_external=is_external,
        certificate_number=certificate_number,
        as_found=as_found or {},
        as_left=as_left or {},
        uncertainty=uncertainty,
        result=result,
        notes=notes,
    )

    schedule.last_calibrated_on = performed_at
    schedule.recompute_next()
    schedule.save(update_fields=["last_calibrated_on", "next_due_date", "updated_at"])

    if result in {CalibrationRecord.Result.FAIL, CalibrationRecord.Result.SUSPECT}:
        from qms.models import Nonconformance
        # Ekipman ölçümlerinin geriye dönük olası etkisi araştırılmalı
        ncr_user = performed_by_user or schedule.responsible
        if ncr_user is not None:
            ncr = open_ncr(
                ncr_number=f"NCR-CAL-{record.pk}",
                source=Nonconformance.Source.MAINTENANCE,
                detected_by=ncr_user,
                title=f"Kalibrasyon {result} - {schedule.equipment.equipment_number}",
                description=(
                    f"Kalibrasyon planı {schedule.parameter} için sonuç: {result}. "
                    f"Geriye dönük ölçüm etkisi değerlendirilmeli."
                ),
                severity="HIGH" if result == CalibrationRecord.Result.FAIL else "MEDIUM",
                target=schedule.equipment,
            )
            record.ncr = ncr
            record.save(update_fields=["ncr", "updated_at"])
        # Ekipmanı servis dışı say
        schedule.equipment.status = Equipment.Status.OUT_OF_SERVICE
        schedule.equipment.save(update_fields=["status", "updated_at"])

    return record


def find_overdue_calibrations(*, as_of: dt.date | None = None) -> list[CalibrationSchedule]:
    """Vadesi geçmiş kalibrasyon planlarını döner."""
    as_of = as_of or dt.date.today()
    return list(CalibrationSchedule.objects.filter(
        is_active=True,
        next_due_date__isnull=False,
        next_due_date__lt=as_of,
    ).select_related("equipment"))


# ---------------------------------------------------------------------------
# Sprint 11 — SCADA sensor alert -> auto WorkOrder koprusu
# ---------------------------------------------------------------------------

from django.utils import timezone as _tz
from .models import SensorAlert


SEVERITY_TO_PRIORITY = {
    SensorAlert.Severity.INFO: WorkOrder.Priority.LOW,
    SensorAlert.Severity.WARNING: WorkOrder.Priority.MEDIUM,
    SensorAlert.Severity.CRITICAL: WorkOrder.Priority.URGENT,
}


def _next_wo_number() -> str:
    stamp = _tz.now().strftime("%Y%m%d%H%M%S")
    return f"WO-AUTO-{stamp}"


from django.db import transaction as _tx


def _system_user():
    from django.contrib.auth import get_user_model
    U = get_user_model()
    u, _ = U.objects.get_or_create(
        username="scada_system",
        defaults={"first_name": "SCADA", "last_name": "System"},
    )
    return u


@_tx.atomic
def create_work_order_from_alert(alert, requested_by=None):
    """Kritik sensor alert icin otomatik WorkOrder ac."""
    if alert.auto_work_order_id is not None:
        return alert.auto_work_order

    priority = SEVERITY_TO_PRIORITY.get(alert.severity, WorkOrder.Priority.MEDIUM)
    title = f"[SCADA] {alert.sensor_tag} = {alert.measured_value} {alert.unit} ({alert.severity})"
    description = (
        f"Otomatik acildi - Sensor alert {alert.alert_number}.\n"
        f"Sensor tag: {alert.sensor_tag}\n"
        f"Parametre: {alert.parameter}\n"
        f"Olcum: {alert.measured_value} {alert.unit}\n"
    )
    if alert.threshold_low is not None or alert.threshold_high is not None:
        description += f"Esikler: [{alert.threshold_low or '-inf'} ... {alert.threshold_high or '+inf'}]\n"
    if alert.notes:
        description += f"\nNot: {alert.notes}"

    wo = WorkOrder.objects.create(
        work_order_number=_next_wo_number(),
        type=WorkOrder.Type.CORRECTIVE,
        priority=priority,
        status=WorkOrder.Status.OPEN,
        equipment=alert.equipment,
        title=title[:200],
        description=description,
        requested_by=(requested_by or _system_user()),
    )
    alert.auto_work_order = wo
    alert.status = SensorAlert.Status.WO_CREATED
    alert.save(update_fields=["auto_work_order", "status", "updated_at"])
    return wo
