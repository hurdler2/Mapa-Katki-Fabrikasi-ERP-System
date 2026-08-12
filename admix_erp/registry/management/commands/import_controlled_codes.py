"""00_MCO_1.xls sheet 6 'dan (R15 = 247 kimlik) ControlledCode kayitlarina import.

XLSX beklenen kolon sirasi (bilinen R15 baseline):
    A Full Code
    B Short/Alias Code
    C Title
    D Type
    E Level
    F Function
    G Source Procedure
    H Owner
    I Applicability
    J Package Wave
    K Status
    L Revision
    M Activation Gate
    N Objective Evidence Rule
    O Kullanim / tetik tipi
    P Birincil dolduran
    Q Review / onay modeli
    R Ornek Record ID
    S Onerilen kayit yolu
    T Retention authority

Format sapmalari icin --dry-run ile once test.

Kullanim:
    python manage.py import_controlled_codes --file /path/to/00_MCO_1.xls
    python manage.py import_controlled_codes --file /path/to/00_MCO_1.xls --dry-run
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from registry.models import ControlledCode


NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


TYPE_MAP = {
    "Form": "FRM", "Register": "REG", "Master": "MST", "Master data": "MST",
    "SOP": "SOP", "WI": "WI", "Checklist": "CHK", "CHK": "CHK",
    "Procedure": "PRO", "Policy": "POL", "Manual": "MAN",
    "Specification": "SPC", "Plan": "PLN", "Schedule": "SCH",
    "Log": "LOG", "Report": "RPT", "CDD": "CDD", "NAV": "NAV",
    "SET": "SET",
}

FUNCTION_MAP = {
    "COR": "COR", "OPS": "OPS", "QMS": "QMS", "QA": "QA", "QCL": "QCL",
    "QC": "QCL", "RDT": "RDT", "R&D": "RDT", "PRD": "PRD",
    "SCM": "SCM", "WHL": "WHL", "MNT": "MNT", "HSE": "HSE",
    "COM": "COM", "ADM": "ADM", "IMS": "IMS", "IT": "IT",
    "HR": "HR", "BCM": "BCM", "SUP": "SUP",
    "WHS": "WHS", "ENV": "ENV", "MET": "MET", "DPO": "DPO",
    "LEG": "LEG", "FIN": "FIN",
    "SAL": "SAL", "CPL": "CPL", "ORG": "ORG", "CUS": "CUS",
    "RDI": "RDI", "RCV": "RCV", "TRA": "TRA", "SST": "SST",
    "MFG": "MFG", "LAB": "LAB", "MKT": "MKT", "COMMS": "COMMS",
}

STATUS_MAP = {
    "R0": "DR", "R1": "IS", "Architecture Review": "AR",
    "Controlled Issue": "IS", "Activated": "AC", "Retired": "RT",
    "Draft": "DR",
}

TRIGGER_MAP = {
    "Olay, değişiklik, işlem veya karar tetiklemeli": "EVENT",
    "Rutin / işlem veya vardiya bazlı": "ROUTINE",
    "Register / master (periyodik review)": "REGISTER",
}


def _extract_sheet_text(xlsx_path: Path, sheet_name: str = "05_TUM_FORM_ENVANTERI"):
    """Sheet'ten satır × sütun matrisini string olarak döner."""
    with zipfile.ZipFile(xlsx_path) as z:
        # workbook.xml'den sheet index bul
        wb = z.read("xl/workbook.xml").decode("utf-8")
        root = ET.fromstring(wb)
        sheets = root.find("x:sheets", NS)
        sheet_id = None
        for i, s in enumerate(sheets.findall("x:sheet", NS), start=1):
            if s.get("name") == sheet_name:
                sheet_id = i
                break
        if sheet_id is None:
            raise ValueError(f"Sheet not found: {sheet_name}")

        content = z.read(f"xl/worksheets/sheet{sheet_id}.xml").decode("utf-8")

    root = ET.fromstring(content)
    rows = []
    for row_el in root.iter(f"{{{NS['x']}}}row"):
        row_data = {}
        for c in row_el.findall(f"{{{NS['x']}}}c"):
            ref = c.get("r", "")  # e.g. "A5"
            col_letter = re.match(r"^([A-Z]+)", ref).group(1)
            v = c.find(f"{{{NS['x']}}}v")
            row_data[col_letter] = v.text if v is not None else ""
        rows.append(row_data)
    return rows


def _col(row: dict, letter: str, default: str = "") -> str:
    v = row.get(letter, default) or default
    return v.strip() if isinstance(v, str) else v


def _guess_type(raw: str) -> str | None:
    raw = (raw or "").strip()
    for key, code in TYPE_MAP.items():
        if raw.lower().startswith(key.lower()):
            return code
    return None


def _guess_function(raw: str) -> str | None:
    raw = (raw or "").strip().upper()
    return FUNCTION_MAP.get(raw)


def _guess_status(raw: str) -> str:
    for key, code in STATUS_MAP.items():
        if key.lower() in (raw or "").lower():
            return code
    return "DR"


def _guess_trigger(raw: str) -> str:
    for key, code in TRIGGER_MAP.items():
        if key in (raw or ""):
            return code
    return "OTHER"


class Command(BaseCommand):
    help = "00_MCO_1.xls sheet 6'dan ControlledCode kayitlarina toplu import."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--file", required=True, help="00_MCO_1.xls (veya .xlsx) yolu")
        parser.add_argument("--sheet", default="05_TUM_FORM_ENVANTERI",
                            help="Import edilecek sheet adi")
        parser.add_argument("--dry-run", action="store_true",
                            help="Kayit yapma, sadece raporla")

    @transaction.atomic
    def handle(self, *args, file: str, sheet: str,
               dry_run: bool = False, **_) -> None:
        path = Path(file)
        if not path.exists():
            raise CommandError(f"Dosya yok: {file}")

        try:
            rows = _extract_sheet_text(path, sheet_name=sheet)
        except Exception as e:
            raise CommandError(f"Sheet okunamadi: {e}") from e

        # Baslik satiri: full code = 'Full Code' iceren ilk satir
        header_idx = None
        for i, r in enumerate(rows):
            if any((v or "").strip() == "Full Code" for v in r.values()):
                header_idx = i
                break

        if header_idx is None:
            raise CommandError("Header (Full Code) satiri bulunamadi.")

        data_rows = rows[header_idx + 1:]
        created = updated = skipped = errors = 0
        code_pattern = re.compile(r"^MAPA(-[A-Z][A-Z0-9]{1,5}){1,3}-\d{3}$")

        for r in data_rows:
            full_code = _col(r, "A")
            if not full_code or not full_code.startswith("MAPA-"):
                skipped += 1
                continue
            if not code_pattern.match(full_code):
                self.stdout.write(
                    self.style.WARNING(f"  Format uymuyor, atlandi: {full_code}"))
                skipped += 1
                continue

            short_alias = _col(r, "B")
            title = _col(r, "C")
            raw_type = _col(r, "D")
            raw_level = _col(r, "E")
            raw_func = _col(r, "F")
            source_pro = _col(r, "G")
            owner_role = _col(r, "H")
            applicability = _col(r, "I")
            package_wave = _col(r, "J")
            raw_status = _col(r, "K")
            revision = _col(r, "L") or "R0"
            activation_gate = _col(r, "M")
            evidence_rule = _col(r, "N")
            raw_trigger = _col(r, "O")
            preparer = _col(r, "P")
            review_model = _col(r, "Q")
            example_id = _col(r, "R")
            archive_path = _col(r, "S")
            retention = _col(r, "T")

            ctype = _guess_type(raw_type)
            func = _guess_function(raw_func)
            level = raw_level.upper() if raw_level in ("L1", "L2", "L3", "L4", "L5") else None
            if not ctype or not func or not level:
                self.stdout.write(self.style.WARNING(
                    f"  Sinif eslesmedi, atlandi: {full_code} (type={raw_type}, func={raw_func}, level={raw_level})"
                ))
                skipped += 1
                continue

            defaults = {
                "short_alias": short_alias,
                "title": title,
                "type": ctype,
                "level": level,
                "function": func,
                "source_procedure": source_pro,
                "owner_role": owner_role,
                "package_wave": package_wave,
                "status": _guess_status(raw_status),
                "revision": revision,
                "activation_gate": activation_gate,
                "objective_evidence_rule": evidence_rule,
                "trigger_type": _guess_trigger(raw_trigger),
                "primary_preparer_role": preparer,
                "review_approval_model": review_model,
                "example_record_id_pattern": example_id,
                "archive_path_pattern": archive_path,
                "retention_authority": retention,
                "notes": applicability,
                "is_active": True,
            }

            if dry_run:
                created += 1
                continue

            try:
                obj, was_created = ControlledCode.objects.update_or_create(
                    full_code=full_code, defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"  ERROR {full_code}: {e}"))
                errors += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"DRY-RUN: {created} yeni + {updated} guncelleme + "
                f"{skipped} atlandi + {errors} hata."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Import tamam: {created} yeni + {updated} guncelleme + "
                f"{skipped} atlandi + {errors} hata. "
                f"Toplam: {ControlledCode.objects.count()} kod."
            ))
