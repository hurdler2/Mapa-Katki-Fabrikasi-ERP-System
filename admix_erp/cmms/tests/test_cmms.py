"""CMMS testleri: WO yaşam döngüsü, parça sarfı, PM üretici, kalibrasyon FAIL→NCR."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

from cmms.models import (
    CalibrationRecord,
    CalibrationSchedule,
    Equipment,
    MaintenancePlan,
    SparePart,
    WorkOrder,
)
from cmms.services import (
    assign_work_order,
    calculate_mtbf_mttr,
    complete_work_order,
    consume_part,
    create_work_order,
    find_overdue_calibrations,
    generate_pm_work_orders,
    record_calibration,
    start_work_order,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def planner(db):
    return User.objects.create_user("planner", password="pw")


@pytest.fixture
def technician(db):
    return User.objects.create_user("tech", password="pw")


@pytest.fixture
def cmms_seeded(db):
    call_command("seed_equipment")
    return True


@pytest.fixture
def reactor_eq(db):
    return Equipment.objects.create(
        equipment_number="EQ-TEST-R", name="Test reaktör",
        category=Equipment.Category.REACTOR,
        criticality=Equipment.Criticality.A_CRITICAL,
    )


@pytest.fixture
def balance_eq(db):
    return Equipment.objects.create(
        equipment_number="EQ-TEST-BAL", name="Test terazi",
        category=Equipment.Category.BALANCE,
        is_measuring_device=True,
    )


# --- Seed --------------------------------------------------------------------

def test_seed_creates_reference_equipment(cmms_seeded):
    assert Equipment.objects.filter(equipment_number="EQ-REACT-1").exists()
    assert MaintenancePlan.objects.filter(plan_code="PM-BAL-01-W").exists()
    assert CalibrationSchedule.objects.filter(
        equipment__equipment_number="EQ-BAL-01").exists()


# --- WO yaşam döngüsü --------------------------------------------------------

def test_corrective_wo_puts_equipment_under_maintenance(reactor_eq, planner):
    wo = create_work_order(
        work_order_number="WO-001", type=WorkOrder.Type.CORRECTIVE,
        equipment=reactor_eq, title="Karıştırıcı arızası",
        failure_description="Motor titriyor", requested_by=planner,
    )
    reactor_eq.refresh_from_db()
    assert reactor_eq.status == Equipment.Status.UNDER_MAINTENANCE
    assert wo.status == WorkOrder.Status.OPEN


def test_wo_full_lifecycle(reactor_eq, planner, technician):
    wo = create_work_order(
        work_order_number="WO-002", type=WorkOrder.Type.CORRECTIVE,
        equipment=reactor_eq, title="X", requested_by=planner,
    )
    # Atanmadan başlatılamaz
    with pytest.raises(ValidationError):
        start_work_order(wo)
    assign_work_order(wo, technician=technician)
    start_work_order(wo)
    wo.refresh_from_db()
    assert wo.status == WorkOrder.Status.IN_PROGRESS
    assert wo.actual_start is not None

    complete_work_order(
        wo, completion_notes="Değiştirildi",
        downtime_hours=2.5, labor_hours=1.5, labor_cost=Decimal("300"),
    )
    wo.refresh_from_db()
    assert wo.status == WorkOrder.Status.COMPLETED
    assert wo.actual_end is not None
    reactor_eq.refresh_from_db()
    assert reactor_eq.status == Equipment.Status.OPERATIONAL


def test_consume_part_reduces_stock_and_adds_cost(reactor_eq, planner, technician):
    part = SparePart.objects.create(
        code="SP-BEARING-1", name="Yatak", current_stock=Decimal("5"),
        unit_cost=Decimal("120"),
    )
    wo = create_work_order(
        work_order_number="WO-003", type=WorkOrder.Type.CORRECTIVE,
        equipment=reactor_eq, title="Yatak değişimi", requested_by=planner,
        assigned_to=technician,
    )
    start_work_order(wo)
    consume_part(wo, spare_part=part, quantity=Decimal("2"))
    part.refresh_from_db()
    wo.refresh_from_db()
    assert part.current_stock == Decimal("3")
    assert wo.parts_cost == Decimal("240")


def test_consume_part_insufficient_stock(reactor_eq, planner, technician):
    part = SparePart.objects.create(code="SP-LOW", name="X",
                                     current_stock=Decimal("1"), unit_cost=Decimal("10"))
    wo = create_work_order(
        work_order_number="WO-004", type=WorkOrder.Type.CORRECTIVE,
        equipment=reactor_eq, title="X", requested_by=planner, assigned_to=technician,
    )
    start_work_order(wo)
    with pytest.raises(ValidationError):
        consume_part(wo, spare_part=part, quantity=Decimal("5"))


# --- PM üretici --------------------------------------------------------------

def test_pm_generator_creates_wo_for_due_plans(reactor_eq, planner):
    plan = MaintenancePlan.objects.create(
        equipment=reactor_eq, plan_code="PM-TEST-D",
        name="Günlük kontrol", frequency=MaintenancePlan.Frequency.DAILY,
        task_checklist="Test",
        last_generated_on=dt.date.today() - dt.timedelta(days=2),
    )
    created = generate_pm_work_orders(requested_by=planner)
    assert len(created) == 1
    plan.refresh_from_db()
    assert plan.last_generated_on == dt.date.today()

    # Aynı gün ikinci çağrı mükerrer üretmez
    again = generate_pm_work_orders(requested_by=planner)
    assert len(again) == 0


def test_pm_skips_not_due(reactor_eq, planner):
    MaintenancePlan.objects.create(
        equipment=reactor_eq, plan_code="PM-YEAR",
        name="Yıllık", frequency=MaintenancePlan.Frequency.ANNUAL,
        task_checklist="Test",
        last_generated_on=dt.date.today() - dt.timedelta(days=10),
    )
    created = generate_pm_work_orders(requested_by=planner)
    assert len(created) == 0


# --- Kalibrasyon -------------------------------------------------------------

def test_calibration_pass_updates_next_due(balance_eq, planner):
    sched = CalibrationSchedule.objects.create(
        equipment=balance_eq, parameter="Ağırlık", tolerance="±0.5%",
        interval_days=365, responsible=planner,
    )
    record_calibration(
        sched, performed_at=dt.date(2026, 8, 10),
        performed_by="Kalibrasyon Lab.", result=CalibrationRecord.Result.PASS,
        as_found={"0kg": 0.002, "50kg": 50.01},
        as_left={"0kg": 0.000, "50kg": 50.00},
        certificate_number="CAL-2026-001",
    )
    sched.refresh_from_db()
    assert sched.last_calibrated_on == dt.date(2026, 8, 10)
    assert sched.next_due_date == dt.date(2027, 8, 10)


def test_calibration_fail_opens_ncr_and_sets_equipment_oos(balance_eq, planner):
    sched = CalibrationSchedule.objects.create(
        equipment=balance_eq, parameter="Ağırlık", tolerance="±0.5%",
        interval_days=365, responsible=planner,
    )
    rec = record_calibration(
        sched, performed_at=dt.date.today(),
        performed_by="Lab X", result=CalibrationRecord.Result.FAIL,
        as_found={"50kg": 55.0},
        performed_by_user=planner,
    )
    assert rec.ncr is not None
    assert rec.ncr.source == "MAINTENANCE"
    balance_eq.refresh_from_db()
    assert balance_eq.status == Equipment.Status.OUT_OF_SERVICE


def test_find_overdue_calibrations(balance_eq, planner):
    CalibrationSchedule.objects.create(
        equipment=balance_eq, parameter="Ağırlık",
        tolerance="±0.5%", interval_days=365,
        responsible=planner,
        last_calibrated_on=dt.date.today() - dt.timedelta(days=400),
        next_due_date=dt.date.today() - dt.timedelta(days=35),
    )
    overdue = find_overdue_calibrations()
    assert len(overdue) == 1


# --- MTBF / MTTR -------------------------------------------------------------

def test_mtbf_mttr_calculation(reactor_eq, planner, technician):
    reactor_eq.install_date = dt.date.today() - dt.timedelta(days=30)
    reactor_eq.save()

    # 2 arıza, toplam 10 saat duruş
    for i, hours in enumerate([4, 6]):
        wo = create_work_order(
            work_order_number=f"WO-M-{i}",
            type=WorkOrder.Type.CORRECTIVE,
            equipment=reactor_eq, title="Arıza",
            requested_by=planner, assigned_to=technician,
        )
        start_work_order(wo)
        complete_work_order(wo, downtime_hours=hours, labor_hours=hours)

    metrics = calculate_mtbf_mttr(reactor_eq)
    assert metrics["failures"] == 2
    assert metrics["downtime_hours"] == Decimal("10")
    assert metrics["mttr_hours"] == 5.0  # 10 / 2
    assert metrics["mtbf_hours"] is not None
    assert metrics["availability_pct"] is not None and metrics["availability_pct"] > 90
