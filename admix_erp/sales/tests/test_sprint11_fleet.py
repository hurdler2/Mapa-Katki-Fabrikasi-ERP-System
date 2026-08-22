"""Sprint 11: Fleet (Truck + DeliveryTrip) testleri."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone

from masterdata.models import Customer
from sales.models import DeliveryTrip, Shipment, Truck


pytestmark = pytest.mark.django_db


@pytest.fixture
def customer():
    return Customer.objects.create(code="C-FLEET-1", name="Test Fleet Client")


@pytest.fixture
def truck():
    return Truck.objects.create(
        plate_number="01234-11-16",
        truck_type=Truck.Type.TANKER,
        capacity_kg=Decimal("15000.00"),
        make_model="Renault K440",
        year=2023,
        driver_default="Mohamed Belaidi",
        driver_phone="+213555123456",
        gps_device_id="GPS-DEV-A44",
    )


@pytest.fixture
def shipment(customer):
    return Shipment.objects.create(
        shipment_number="BL-TRIP-001",
        customer=customer,
        shipped_date=dt.date.today(),
    )


def test_truck_status_default(truck):
    assert truck.status == Truck.Status.AVAILABLE
    assert truck.capacity_kg == Decimal("15000.00")


def test_delivery_trip_lifecycle(truck, shipment):
    now = timezone.now()
    trip = DeliveryTrip.objects.create(
        trip_number="TRP-2026-001",
        shipment=shipment, truck=truck,
        driver_name="Mohamed Belaidi",
        scheduled_departure=now,
        scheduled_arrival=now + dt.timedelta(hours=2),
        destination_address="Chantier autoroute Setif",
        distance_km=Decimal("310.5"),
    )
    assert trip.status == DeliveryTrip.Status.SCHEDULED
    trip.actual_departure = now + dt.timedelta(minutes=15)
    trip.status = DeliveryTrip.Status.DEPARTED
    trip.save()
    trip.actual_arrival = now + dt.timedelta(hours=2, minutes=10)
    trip.status = DeliveryTrip.Status.DELIVERED
    trip.delivery_completed_at = now + dt.timedelta(hours=2, minutes=20)
    trip.signature_name = "Karim Boudjelal"
    trip.save()
    assert trip.status == DeliveryTrip.Status.DELIVERED


def test_delivery_trip_delay(truck, shipment):
    past = timezone.now() - dt.timedelta(hours=3)
    trip = DeliveryTrip.objects.create(
        trip_number="TRP-2026-002",
        shipment=shipment, truck=truck,
        scheduled_departure=past,
        scheduled_arrival=past + dt.timedelta(hours=1),
        destination_address="Test",
        status=DeliveryTrip.Status.DEPARTED,
    )
    assert trip.is_delayed is True


def test_delivery_gps_update(truck, shipment):
    now = timezone.now()
    trip = DeliveryTrip.objects.create(
        trip_number="TRP-2026-003",
        shipment=shipment, truck=truck,
        scheduled_departure=now,
        scheduled_arrival=now + dt.timedelta(hours=1),
        destination_address="Test",
    )
    trip.last_gps_lat = Decimal("36.752887")
    trip.last_gps_lng = Decimal("3.042048")
    trip.last_gps_timestamp = now
    trip.save()
    assert trip.last_gps_lat == Decimal("36.752887")
