"""MCOS kontrollu kod cekirdek baseline seed'i.

MAPA IMS Master Project'ten dogrudan gorulmus bilinen kimlikler:
- L1 CDD + IMS Manual + Policy + NAV
- L2 IMS core prosedurler (DOC, RSK, MOC, NCR, AUD, MR)
- L2 SCM, QA, HSE, HR prosedurleri
- L3/L4 MCS uretim + IT + QC form aileleri (kritik olanlar)

Bu tam 247 degil; 00_MCO_1.xls'ten gorunur olan ~50 core kimlik.
Tam envanter icin: python manage.py import_controlled_codes --file <path>

Kullanim:
    python manage.py seed_mcos_codes
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from registry.models import ControlledCode


# ---------------------------------------------------------------------------
# Cekirdek baseline (MCOS Package-001 + gorunur kimlikler)
# ---------------------------------------------------------------------------

# Format: (full_code, short, title, type, level, function, status, owner_role,
#          source_procedure, package_wave, trigger_type)
CORE_CODES = [
    # ==== L1 Corporate ====
    ("MAPA-CDD-001", "CDD-001", "Company Design Document", "CDD", "L1", "COR",
     "IS", "General Manager", "", "Package-001", "EVENT"),
    ("MAPA-CDD-002", "CDD-002", "Organization Design Document", "CDD", "L1", "COR",
     "IS", "General Manager", "", "Package-001", "EVENT"),
    ("MAPA-IMS-MAN-001", "IMS-MAN-001", "IMS Manual", "MAN", "L1", "IMS",
     "AR", "QA/IMS Manager", "", "Package-002", "EVENT"),
    ("MAPA-IMS-POL-001", "IMS-POL-001", "IMS Policy", "POL", "L1", "IMS",
     "AR", "General Manager", "", "Package-002", "EVENT"),
    # ==== L1 Navigation (Package-001 READ FIRST) ====
    ("MAPA-IMS-NAV-001", "NAV-001", "IMS Navigation Map", "NAV", "L1", "IMS",
     "IS", "QA/IMS Manager", "", "Package-001 READ FIRST", "EVENT"),
    ("MAPA-IMS-NAV-002", "NAV-002", "Decision Navigation Map", "NAV", "L1", "IMS",
     "IS", "QA/IMS Manager", "", "Package-001 READ FIRST", "EVENT"),
    ("MAPA-IMS-NAV-003", "NAV-003", "Investigation Navigation Map", "NAV", "L1", "IMS",
     "IS", "QA/IMS Manager", "", "Package-001 READ FIRST", "EVENT"),
    ("MAPA-IMS-NAV-SET-001", "NAV-SET-001",
     "GATE-001 READ FIRST Control Workbook", "SET", "L1", "IMS",
     "IS", "QA/IMS Manager", "", "Package-001 READ FIRST", "EVENT"),

    # ==== L2 IMS Core Procedures ====
    ("MAPA-IMS-PRO-DOC-001", "IMS-PRO-DOC", "Document Control Procedure",
     "PRO", "L2", "IMS", "AR", "QA/IMS Manager", "MAPA-IMS-MAN-001",
     "Package-002", "ROUTINE"),
    ("MAPA-IMS-PRO-RSK-001", "IMS-PRO-RSK", "Risk Management Procedure",
     "PRO", "L2", "IMS", "AR", "QA/IMS Manager", "MAPA-IMS-MAN-001",
     "Package-002", "ROUTINE"),
    ("MAPA-IMS-PRO-MOC-001", "IMS-PRO-MOC", "Management of Change Procedure",
     "PRO", "L2", "IMS", "AR", "QA/IMS Manager", "MAPA-IMS-MAN-001",
     "Package-002", "EVENT"),
    ("MAPA-IMS-PRO-NCR-001", "IMS-PRO-NCR", "Nonconformity & CAPA Procedure",
     "PRO", "L2", "IMS", "AR", "QA/IMS Manager", "MAPA-IMS-MAN-001",
     "Package-002", "EVENT"),
    ("MAPA-IMS-PRO-AUD-001", "IMS-PRO-AUD", "Internal Audit Procedure",
     "PRO", "L2", "IMS", "AR", "QA/IMS Manager", "MAPA-IMS-MAN-001",
     "Package-002", "ROUTINE"),
    ("MAPA-IMS-PRO-MR-001", "IMS-PRO-MR", "Management Review Procedure",
     "PRO", "L2", "IMS", "AR", "General Manager", "MAPA-IMS-MAN-001",
     "Package-002", "ROUTINE"),

    # ==== L2 SCM / QA / HSE / HR ====
    ("MAPA-SCM-PRO-SUP-001", "SCM-PRO-SUP",
     "Supplier and External Provider Management",
     "PRO", "L2", "SCM", "AR", "SCM Manager", "MAPA-IMS-MAN-001",
     "Package-002", "ROUTINE"),
    ("MAPA-QA-PRO-REL-001", "QA-PRO-REL", "Product Review and Release",
     "PRO", "L2", "QA", "AR", "QA/QC Manager", "MAPA-IMS-MAN-001",
     "Package-002", "EVENT"),
    ("MAPA-HSE-PRO-EMR-001", "HSE-PRO-EMR", "Emergency Preparedness and Response",
     "PRO", "L2", "HSE", "AR", "HSE Manager", "MAPA-IMS-MAN-001",
     "Package-002", "EVENT"),
    ("MAPA-HR-PRO-CMP-001", "HR-PRO-CMP", "Competence and Authorization",
     "PRO", "L2", "HR", "AR", "HR Manager", "MAPA-IMS-MAN-001",
     "Package-002", "ROUTINE"),

    # ==== L4 MCS/PRD Kritik Formlar (Package 004) ====
    ("MAPA-PRD-FRM-BMR-001", "PRD-FRM-BMR", "Batch Manufacturing Record",
     "FRM", "L4", "PRD", "IS", "Production Supervisor", "MAPA-QA-PRO-REL-001",
     "Package-004 MCS pilot", "ROUTINE"),
    ("MAPA-PRD-FRM-CLR-001", "PRD-FRM-CLR", "Line Clearance & Cleaning",
     "FRM", "L4", "PRD", "IS", "Production + QA/QC", "MAPA-QA-PRO-REL-001",
     "Package-004 MCS pilot", "ROUTINE"),
    ("MAPA-PRD-FRM-IPC-001", "PRD-FRM-IPC", "In-Process Control",
     "FRM", "L4", "PRD", "IS", "Production + QA/QC", "MAPA-QA-PRO-REL-001",
     "Package-004 MCS pilot", "ROUTINE"),

    # ==== L4 Warehouse / Receipt ====
    ("MAPA-WHL-FRM-001", "WHS-FRM-001", "Goods Receipt & Lot Registration",
     "FRM", "L4", "WHL", "IS", "Warehouse Supervisor", "MAPA-SCM-PRO-SUP-001",
     "Package-004", "ROUTINE"),
    ("MAPA-WHL-FRM-003", "WHS-FRM-003", "Storage Condition & Preservation",
     "FRM", "L4", "WHL", "AR", "Warehouse Supervisor", "MAPA-SCM-PRO-SUP-001",
     "Package-004", "ROUTINE"),
    ("MAPA-WHL-FRM-004", "WHS-FRM-004", "Material Issue / Return",
     "FRM", "L4", "WHL", "IS", "Warehouse Supervisor", "MAPA-QA-PRO-REL-001",
     "Package-004", "ROUTINE"),
    ("MAPA-WHL-FRM-005", "WHS-FRM-005", "Dispatch Record",
     "FRM", "L4", "WHL", "IS", "Logistics + QA", "MAPA-QA-PRO-REL-001",
     "Package-004", "ROUTINE"),

    # ==== L4 QC / QA ====
    ("MAPA-QC-FRM-SMP-001", "SMP-001", "Sampling Record",
     "FRM", "L4", "QCL", "IS", "Sampler / Analyst", "MAPA-QA-PRO-REL-001",
     "Package-004", "EVENT"),
    ("MAPA-QC-FRM-TST-001", "TST-001", "Test / Analysis Record",
     "FRM", "L4", "QCL", "IS", "Analyst", "MAPA-QA-PRO-REL-001",
     "Package-004", "EVENT"),
    ("MAPA-QC-FRM-OOS-001", "OOS-001", "Out-of-Specification Investigation",
     "FRM", "L4", "QCL", "IS", "QC Reviewer + QA", "MAPA-IMS-PRO-NCR-001",
     "Package-004", "EVENT"),
    ("MAPA-QA-FRM-BDR-001", "BDR-001", "Batch Disposition Review",
     "FRM", "L4", "QA", "IS", "QA Reviewer + Yetkili Release", "MAPA-QA-PRO-REL-001",
     "Package-004", "EVENT"),
    ("MAPA-QA-FRM-REL-001", "REL-001", "Batch/Product Release Decision",
     "FRM", "L4", "QA", "IS", "Yetkili Release Rolu", "MAPA-QA-PRO-REL-001",
     "Package-004", "EVENT"),
    ("MAPA-QA-FRM-REL-002", "REL-002", "Lot Status Decision",
     "FRM", "L4", "QA", "IS", "QA", "MAPA-QA-PRO-REL-001",
     "Package-004", "EVENT"),
    ("MAPA-QA-FRM-REL-005", "REL-005", "Incoming Material Release",
     "FRM", "L4", "QA", "IS", "QA (Incoming)", "MAPA-SCM-PRO-SUP-001",
     "Package-004", "EVENT"),
    ("MAPA-QA-FRM-REL-006", "REL-006", "Dispatch Release Decision",
     "FRM", "L4", "QA", "IS", "QA + Logistics", "MAPA-QA-PRO-REL-001",
     "Package-004", "EVENT"),

    # ==== L4 IMS NCR / CAPA / MOC ====
    ("MAPA-IMS-FRM-NCR-001", "IMS-FRM-NCR", "Nonconformity Report (NCR)",
     "FRM", "L4", "IMS", "IS", "QA/IMS + Owner", "MAPA-IMS-PRO-NCR-001",
     "Package-002", "EVENT"),
    ("MAPA-IMS-FRM-CAPA-001", "IMS-FRM-CAPA", "CAPA & Effectiveness Record",
     "FRM", "L4", "IMS", "IS", "CAPA Owner + QA/IMS", "MAPA-IMS-PRO-NCR-001",
     "Package-002", "EVENT"),
    ("MAPA-IMS-FRM-MOC-001", "IMS-FRM-MOC-001", "Change Notice & Screening",
     "FRM", "L4", "IMS", "IS", "Change Owner + QA/IMS", "MAPA-IMS-PRO-MOC-001",
     "Package-002", "EVENT"),
    ("MAPA-IMS-FRM-MOC-002", "IMS-FRM-MOC-002", "Integrated Impact Analysis",
     "FRM", "L4", "IMS", "IS", "Cross-functional Reviewers", "MAPA-IMS-PRO-MOC-001",
     "Package-002", "EVENT"),

    # ==== L4 IT / OT (GATE-001 kaynak) ====
    ("MAPA-IT-REG-004", "IT-REG-004",
     "Security Event, Incident & Data Breach Register",
     "REG", "L4", "IT", "IS", "IT Incident Lead + QA/IMS", "MAPA-IMS-PRO-NCR-001",
     "Package-002", "REGISTER"),
    ("MAPA-IT-FRM-005", "IT-FRM-005", "Incident Detection & Containment",
     "FRM", "L4", "IT", "IS", "IT Incident Lead", "MAPA-IMS-PRO-NCR-001",
     "Package-002", "EVENT"),
    ("MAPA-IT-FRM-006", "IT-FRM-006", "Return-to-Service Reconciliation",
     "FRM", "L4", "IT", "IS", "IT + Owner + QA/IMS", "MAPA-IMS-PRO-NCR-001",
     "Package-002", "EVENT"),
    ("MAPA-IT-CHK-004", "IT-CHK-004", "Containment Verification Checklist",
     "CHK", "L4", "IT", "IS", "IT Incident Lead + QA", "MAPA-IMS-PRO-NCR-001",
     "Package-002", "EVENT"),

    # ==== L4 IMS Registers ====
    ("MAPA-IMS-REG-NCR-001", "IMS-REG-NCR",
     "Integrated Event / CAPA Master Register",
     "REG", "L4", "IMS", "IS", "QA/IMS Manager", "MAPA-IMS-PRO-NCR-001",
     "Package-002", "REGISTER"),

    # ==== L5 Master Data ====
    ("MAPA-IMS-MST-REC-001", "IMS-MST-REC", "Record Retention Master",
     "MST", "L5", "IMS", "AR", "QA/IMS + Document Control", "MAPA-IMS-PRO-DOC-001",
     "Package-002", "REGISTER"),
    ("MAPA-IMS-FRM-MST-001", "IMS-FRM-MST", "Controlled Form/Record Inventory",
     "MST", "L5", "IMS", "IS", "Document Control", "MAPA-IMS-PRO-DOC-001",
     "Package-001", "REGISTER"),
]


DEFAULT_ACTIVATION_GATE = (
    "Approve template + train users + create one accepted live record"
)
DEFAULT_EVIDENCE_RULE = (
    "Blank template is not evidence; completed, approved and retrievable "
    "record with evidence link is required."
)


class Command(BaseCommand):
    help = "MCOS kontrollu kod cekirdek baseline (~45 kimlik) seed'i."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        created = updated = 0
        for row in CORE_CODES:
            (full_code, short, title, ctype, level, func, status,
             owner_role, source_pro, wave, trigger) = row

            defaults = {
                "short_alias": short,
                "title": title,
                "type": ctype,
                "level": level,
                "function": func,
                "status": status,
                "owner_role": owner_role,
                "source_procedure": source_pro,
                "package_wave": wave,
                "trigger_type": trigger,
                "activation_gate": DEFAULT_ACTIVATION_GATE,
                "objective_evidence_rule": DEFAULT_EVIDENCE_RULE,
                "review_approval_model": (
                    f"{owner_role} hazirlar; bagimsiz reviewer/QA-HSE-IT ve "
                    "yetkili karar rolu onaylar."
                ),
                "archive_path_pattern": (
                    f"/MCOS/IMS/RECORDS/{func}/<YYYY>/{full_code}/<Record-ID>/"
                ),
                "retention_authority": (
                    "MAPA-IMS-MST-REC-001; approved legal/contract retention"
                ),
                "is_active": True,
            }
            obj, was_created = ControlledCode.objects.update_or_create(
                full_code=full_code, defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"MCOS core codes seeded: {created} new, {updated} updated, "
            f"{ControlledCode.objects.count()} total."
        ))
