"""Sprint 11: SensorAlert -> WorkOrder koprusu testleri."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from cmms.models import Equipment, SensorAlert, WorkOrder
from cmms.services import create_work_order_from_alert


pytestmark = pytest.mark.django_db


@pytest.fixture
def equipment():
    return Equipment.objects.create(
        equipment_number="R-101", name="Reactor R-101",
        category=Equipment.Category.REACTOR,
        criticality=Equipment.Criticality.A_CRITICAL,
    )


def _alert(equipment, severity=SensorAlert.Severity.CRITICAL, number="ALT-1"):
    return SensorAlert.objects.create(
        alert_number=number,
        equipment=equipment,
        sensor_tag="R101.TEMP.OUT",
        parameter="Temperature",
        measured_value=Decimal("92.5"),
        threshold_high=Decimal("85.0"),
        unit="°C",
        detected_at=timezone.now(),
        severity=severity,
    )


def test_critical_alert_opens_urgent_wo(equipment):
    alert = _alert(equipment)
    wo = create_work_order_from_alert(alert)
    assert wo.priority == WorkOrder.Priority.URGENT
    assert wo.type == WorkOrder.Type.CORRECTIVE
    alert.refresh_from_db()
    assert alert.status == SensorAlert.Status.WO_CREATED
    assert alert.auto_work_order_id == wo.pk


def test_warning_alert_opens_medium_wo(equipment):
    alert = _alert(equipment, severity=SensorAlert.Severity.WARNING, number="ALT-2")
    wo = create_work_order_from_alert(alert)
    assert wo.priority == WorkOrder.Priority.MEDIUM


def test_info_alert_opens_low_wo(equipment):
    alert = _alert(equipment, severity=SensorAlert.Severity.INFO, number="ALT-3")
    wo = create_work_order_from_alert(alert)
    assert wo.priority == WorkOrder.Priority.LOW


def test_repeated_call_returns_same_wo(equipment):
    alert = _alert(equipment, number="ALT-4")
    wo1 = create_work_order_from_alert(alert)
    wo2 = create_work_order_from_alert(alert)
    assert wo1.pk == wo2.pk
