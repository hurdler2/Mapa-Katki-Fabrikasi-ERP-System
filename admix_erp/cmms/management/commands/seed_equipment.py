"""Referans hat için temel ekipmanları + kalibrasyon planlarını yükler."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from cmms.models import CalibrationSchedule, Equipment, MaintenancePlan
from masterdata.models import Container


EQUIPMENT_DEFS = [
    # (code, name, category, criticality, is_measuring, model, container_code)
    ("EQ-REACT-1", "Reaktör 1 (karıştırmalı)", Equipment.Category.REACTOR, "A", False, "R-2000", "REACTOR-1"),
    ("EQ-BAL-01", "Yük hücreli terazi 1", Equipment.Category.BALANCE, "A", True, "Mettler PBK987", None),
    ("EQ-BAL-02", "Reaktör kütle terazisi", Equipment.Category.BALANCE, "A", True, "Mettler PBK987", None),
    ("EQ-PUMP-01", "SP dozaj pompası", Equipment.Category.PUMP, "B", False, "Grundfos DDA", None),
    ("EQ-PUMP-02", "G dozaj pompası", Equipment.Category.PUMP, "B", False, "Grundfos DDA", None),
    ("EQ-VALVE-W1", "Su solenoid vanası", Equipment.Category.VALVE, "B", False, "Danfoss EV220", None),
    ("EQ-TANK-W1", "Su tankı", Equipment.Category.TANK, "C", False, "10 m³", "TANK-W1"),
    ("EQ-PH-01", "Reaktör pH-metre", Equipment.Category.SENSOR, "A", True, "Endress+Hauser CPS11", None),
    ("EQ-VISC-01", "Laboratuvar viskozimetresi", Equipment.Category.LAB_INSTRUMENT, "B", True, "Brookfield DV2T", None),
    ("EQ-PLC-01", "Ana PLC + HMI", Equipment.Category.PLC_HMI, "A", False, "Siemens S7-1500", None),
]

PM_PLANS = [
    # (equipment_code, plan_code, name, frequency, checklist)
    ("EQ-REACT-1", "PM-REACT-M", "Reaktör aylık bakım",
        MaintenancePlan.Frequency.MONTHLY,
        "1. Görsel kontrol\n2. Karıştırıcı yataklarının yağlanması\n"
        "3. Sızdırmazlık kontrolü\n4. İç yüzey aşınma kontrolü"),
    ("EQ-BAL-01", "PM-BAL-01-W", "Terazi haftalık kontrol",
        MaintenancePlan.Frequency.WEEKLY,
        "1. Test ağırlığıyla kontrol (0, 10, 50 kg)\n"
        "2. Sıfır ayarı\n3. Yük hücresi kablo kontrolü"),
    ("EQ-PUMP-01", "PM-PUMP-01-Q", "SP pompa üç aylık",
        MaintenancePlan.Frequency.QUARTERLY,
        "1. Diyafram durumu\n2. Ventil sızdırmazlığı\n3. Debi testi"),
    ("EQ-PLC-01", "PM-PLC-A", "PLC yıllık yedekleme + inceleme",
        MaintenancePlan.Frequency.ANNUAL,
        "1. Firmware yedeği\n2. Program yedeği\n3. UPS testi"),
]

CALIB_PLANS = [
    # (equipment_code, parameter, standard, tolerance, interval_days, external_lab)
    ("EQ-BAL-01", "Ağırlık (0-100 kg)", "OIML R76",
        "±0.5% okuma", 365, True),
    ("EQ-BAL-02", "Ağırlık (0-2000 kg)", "OIML R76",
        "±0.5% okuma", 365, True),
    ("EQ-PH-01", "pH (0-14)", "EN ISO 10523",
        "±0.05 pH", 90, False),
    ("EQ-VISC-01", "Viskozite (10-1000 mPa·s)", "ISO 3219",
        "±1%", 365, True),
]


class Command(BaseCommand):
    help = "Referans hat için ekipman + PM + kalibrasyon planları seed."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        containers = {c.code: c for c in Container.objects.all()}
        eqmap: dict[str, Equipment] = {}

        for code, name, cat, crit, meas, model, cont in EQUIPMENT_DEFS:
            eq, _ = Equipment.objects.update_or_create(
                equipment_number=code,
                defaults={
                    "name": name, "category": cat, "criticality": crit,
                    "is_measuring_device": meas, "model": model,
                    "manufacturer": model.split()[0] if model else "",
                    "container": containers.get(cont) if cont else None,
                    "status": Equipment.Status.OPERATIONAL,
                },
            )
            eqmap[code] = eq

        for eq_code, plan_code, name, freq, checklist in PM_PLANS:
            eq = eqmap.get(eq_code)
            if not eq:
                continue
            MaintenancePlan.objects.update_or_create(
                plan_code=plan_code,
                defaults={
                    "equipment": eq, "name": name, "frequency": freq,
                    "task_checklist": checklist, "is_active": True,
                    "estimated_hours": 2,
                },
            )

        for eq_code, param, std, tol, days, ext in CALIB_PLANS:
            eq = eqmap.get(eq_code)
            if not eq:
                continue
            CalibrationSchedule.objects.update_or_create(
                equipment=eq, parameter=param,
                defaults={
                    "reference_standard": std, "tolerance": tol,
                    "interval_days": days, "external_lab_required": ext,
                    "is_active": True,
                },
            )

        self.stdout.write(self.style.SUCCESS(
            f"CMMS seed: {Equipment.objects.count()} equipment, "
            f"{MaintenancePlan.objects.count()} PM plans, "
            f"{CalibrationSchedule.objects.count()} calibration schedules."
        ))
