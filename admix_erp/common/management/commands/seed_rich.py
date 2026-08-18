"""Kapsamli demo veri seed'i — her modele bol ornek veri.

Kullanim:
    python manage.py seed_rich

Yuklenen veriler:
    - 12 musteri (Cezayirli cimento/insaat firmalari)
    - 10 tedarikci (BASF/Sika/Chryso + yerel)
    - 15 hammadde lotu (RELEASED + QUARANTINE + REJECTED karisik)
    - 20 uretim partisi (12 ay boyunca)
    - Recete + reccete satirlari
    - 40 QC test sonucu (parti bazli, PASS/FAIL karisik)
    - COA'lar
    - 8 NCR + 5 CAPA
    - 6 EHS incident (farkli severity)
    - 10 iş emri (bakim CMMS)
    - 12 personel (departmanli)
    - Faturalar (12 ay - satis+alim)
    - Odemeler (havale/cek/nakit karisik)
    - Sevkiyatlar (SO+SO_LINE)
    - Kontrolu dokumanlar (5 SOP + 3 form)
"""
from __future__ import annotations

import datetime as dt
import random
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction


random.seed(42)


class Command(BaseCommand):
    help = "Kapsamli demo veri: musteri, tedarikci, lot, parti, QC, NCR, personel, fatura."

    def handle(self, *args, **options) -> None:
        self.stdout.write("Kapsamli demo veri yukleniyor...")
        for name, fn in [
            ("Musteri/Tedarikci", self.seed_customers_suppliers),
            ("HR (departman + profil)", self.seed_hr),
            ("Hammadde lotlari", self.seed_raw_material_lots),
            ("Uretim partileri", self.seed_production_batches),
            ("QC test sonuclari", self.seed_qc_results),
            ("NCR + CAPA", self.seed_ncr_capa),
            ("EHS olaylari", self.seed_ehs_incidents),
            ("Bakim is emirleri", self.seed_cmms_workorders),
            ("Satin alma emirleri", self.seed_purchase_orders),
            ("Satis siparisleri", self.seed_sales_orders_shipments),
            ("Kontrollu dokumanlar", self.seed_docs),
            ("Ic denetim + YGG", self.seed_governance),
        ]:
            try:
                with transaction.atomic():
                    fn()
            except Exception as e:  # noqa: BLE001
                self.stdout.write(self.style.WARNING(f"  [{name}] atlandi: {e}"))
        self.stdout.write(self.style.SUCCESS("\nDEMO VERI YUKLEME TAMAM."))

    # =====================================================================
    def seed_customers_suppliers(self):
        from masterdata.models import Customer, Supplier

        customers = [
            ("C-2026-001", "SARL Cimenterie Blida", "099 123 4567", "Blida"),
            ("C-2026-002", "GICA Groupe Industriel Ciments Algerie", "021 555 0100", "Alger"),
            ("C-2026-003", "SARL Beton Pret Boufarik", "025 445 0022", "Boufarik"),
            ("C-2026-004", "SPA Chlef Constructions", "027 776 8899", "Chlef"),
            ("C-2026-005", "SARL Setif Beton Prêt", "036 123 4567", "Setif"),
            ("C-2026-006", "SARL Oran Beton", "041 776 4433", "Oran"),
            ("C-2026-007", "SARL Constantine Materiaux", "031 776 5544", "Constantine"),
            ("C-2026-008", "EPE Cilas SPA", "021 630 3030", "Alger"),
            ("C-2026-009", "SARL Tlemcen Beton", "043 445 6677", "Tlemcen"),
            ("C-2026-010", "SPA Batna Constructions", "033 776 8899", "Batna"),
        ]
        for code, name, phone, city in customers:
            Customer.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "contact": f"{phone} · {city}",
                    "tax_no": f"099{random.randint(1000000000, 9999999999)}",
                    "is_active": True,
                },
            )

        suppliers = [
            ("S-2026-001", "BASF Construction Chemicals Algerie", "021 456 7890", "Alger", "Superplastikleştirici, hızlandırıcı"),
            ("S-2026-002", "Sika Djazair SPA", "021 559 0011", "Alger", "PCE, retarder, HD"),
            ("S-2026-003", "Chryso Algerie", "021 445 3322", "Alger", "Katkı, geciktirici"),
            ("S-2026-004", "MC-Bauchemie Algerie", "021 776 8899", "Alger", "Beton katkısı"),
            ("S-2026-005", "SARL Sonatrach Petrochimie", "021 336 5544", "Alger", "Kimyasal hammaddeler"),
            ("S-2026-006", "SARL Emballages Djazair", "025 445 3322", "Blida", "Ambalaj / IBC"),
            ("S-2026-007", "SARL Logistique Blida", "025 123 4567", "Blida", "Nakliye"),
            ("S-2026-008", "ONEE Electricite", "021 555 0022", "Alger", "Elektrik"),
        ]
        for code, name, phone, city, note in suppliers:
            Supplier.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "contact": f"{phone} · {city} · {note}",
                    "tax_no": f"099{random.randint(1000000000, 9999999999)}",
                    "is_active": True,
                },
            )

        self.stdout.write(f"  Musteri: {Customer.objects.count()}, Tedarikci: {Supplier.objects.count()}")

    # =====================================================================
    def seed_hr(self):
        from iam.models import Department, UserProfile

        departments = [
            ("DIR", "Genel Mudurluk"),
            ("PRD", "Uretim"),
            ("QA",  "Kalite Yonetim / IMS"),
            ("QCL", "Laboratuvar"),
            ("WHL", "Depo & Lojistik"),
            ("SCM", "Satin Alma"),
            ("ADM", "Muhasebe & Finans"),
            ("MNT", "Bakim"),
            ("HSE", "ISG & Cevre"),
            ("RDT", "Ar-Ge"),
            ("COM", "Ticari & Sikayet"),
            ("IT",  "Bilgi Teknolojileri"),
        ]
        for code, name in departments:
            Department.objects.get_or_create(code=code, defaults={"name": name})

        # Kullanicilara profil + departman ata
        role_dept = {
            "gm.director":       ("DIR", "P-001", "Genel Mudur"),
            "tm.director":       ("PRD", "P-002", "Teknik Mudur"),
            "op.manager":        ("PRD", "P-003", "Operasyon Muduru"),
            "qa.manager":        ("QA",  "P-004", "IMS/QA Muduru"),
            "acc.manager":       ("ADM", "P-005", "Muhasebe Muduru"),
            "lab.tech":          ("QCL", "P-006", "Kalite Kontrol Sorumlusu"),
            "shift.supervisor":  ("PRD", "P-007", "Vardiya Supervizoru"),
            "warehouse.chief":   ("WHL", "P-008", "Depo Sefi"),
            "purchase.officer":  ("SCM", "P-009", "Satin Alma Sorumlusu"),
            "rdt.eng":           ("RDT", "P-010", "R&D Muhendisi"),
            "hse.officer":       ("HSE", "P-011", "ISG Sorumlusu"),
            "maint.tech":        ("MNT", "P-012", "Bakim Teknisyeni"),
            "comm.eng":          ("COM", "P-013", "Ticari & Teknik Servis Muhendisi"),
            "audit.internal":    ("QA",  "P-014", "Ic Denetci"),
            "mlts.analyst":      ("QCL", "P-015", "MLTS Lab Analisti"),
            "it.admin":          ("IT",  "P-016", "BT Yonetici"),
        }
        for uname, (dept_code, emp_no, title) in role_dept.items():
            u = User.objects.filter(username=uname).first()
            if not u:
                continue
            dept = Department.objects.get(code=dept_code)
            UserProfile.objects.update_or_create(
                user=u,
                defaults={
                    "employee_no": emp_no,
                    "department": dept,
                    "title": title,
                    "phone": f"055 {random.randint(100, 999)} {random.randint(1000, 9999)}",
                    "hire_date": dt.date(2024, random.randint(1, 12), random.randint(1, 28)),
                },
            )
        self.stdout.write(f"  Departman: {Department.objects.count()}, Profil: {UserProfile.objects.count()}")

    # =====================================================================
    def seed_raw_material_lots(self):
        from inventory.models import RawMaterialLot
        from masterdata.models import RawMaterial, Supplier

        raws = list(RawMaterial.objects.all())
        sups = list(Supplier.objects.filter(is_active=True))
        if not raws or not sups:
            return

        today = dt.date.today()
        qc_dist = [
            RawMaterialLot.QCStatus.RELEASED,
            RawMaterialLot.QCStatus.RELEASED,
            RawMaterialLot.QCStatus.RELEASED,
            RawMaterialLot.QCStatus.RELEASED,
            RawMaterialLot.QCStatus.QUARANTINE,
            RawMaterialLot.QCStatus.PENDING,
        ]

        count = 0
        for i in range(20):
            rm = random.choice(raws)
            sup = random.choice(sups)
            days_ago = random.randint(1, 90)
            recv = today - dt.timedelta(days=days_ago)
            qty = Decimal(random.randint(500, 5000))
            remaining = qty * Decimal(random.choice(["1.0", "0.7", "0.5", "0.3"]))
            lot_no = f"LOT-{rm.code}-{recv:%Y%m}-{i+1:03d}"
            _, created = RawMaterialLot.objects.get_or_create(
                lot_number=lot_no,
                defaults={
                    "raw_material": rm,
                    "supplier": sup,
                    "received_date": recv,
                    "expiry_date": recv + dt.timedelta(days=365),
                    "received_qty": qty,
                    "remaining_qty": remaining,
                    "qc_status": random.choice(qc_dist),
                    "unit_cost": Decimal(random.randint(50, 500)),
                    "coa_reference": f"COA-{sup.code}-{recv:%Y%m}-{i+1}",
                },
            )
            if created:
                count += 1
        self.stdout.write(f"  Hammadde lotu: +{count} (toplam {RawMaterialLot.objects.count()})")

    # =====================================================================
    def seed_production_batches(self):
        from production.models import ProductionBatch, ProductionOrder
        from formulation.models import Recipe
        from masterdata.models import Container

        recipes = list(Recipe.objects.filter(is_active=True))
        reactors = list(Container.objects.filter(container_type=Container.ContainerType.REACTOR))
        if not recipes or not reactors:
            return

        today = dt.date.today()
        count = 0
        for i in range(24):
            days_ago = random.randint(1, 350)
            batch_date = today - dt.timedelta(days=days_ago)
            recipe = random.choice(recipes)
            reactor = random.choice(reactors)

            # Uretim emri
            order_no = f"PORD-{batch_date:%Y%m}-{i+1:03d}"
            order, _ = ProductionOrder.objects.get_or_create(
                order_number=order_no,
                defaults={
                    "product": recipe.product,
                    "recipe": recipe,
                    "target_qty": Decimal(random.randint(500, 2000)),
                    "unit": recipe.unit,
                    "reactor": reactor,
                    "status": ProductionOrder.Status.COMPLETED,
                    "scheduled_date": batch_date - dt.timedelta(days=1),
                },
            )

            # Parti
            batch_no = f"BATCH-{batch_date:%Y%m}-{i+1:03d}"
            _, created = ProductionBatch.objects.get_or_create(
                batch_number=batch_no,
                defaults={
                    "production_order": order,
                    "recipe": recipe,
                    "reactor": reactor,
                    "target_qty": order.target_qty,
                    "actual_qty": order.target_qty * Decimal(random.choice(["0.98", "1.0", "1.02"])),
                    "status": ProductionBatch.Status.RELEASED if days_ago > 30 else random.choice([
                        ProductionBatch.Status.RELEASED, ProductionBatch.Status.COMPLETED,
                        ProductionBatch.Status.QC_HOLD,
                    ]),
                    "qc_status": ProductionBatch.QCStatus.RELEASED if days_ago > 30 else random.choice([
                        ProductionBatch.QCStatus.RELEASED, ProductionBatch.QCStatus.PENDING,
                    ]),
                    "operator": random.choice(["Ali Yildiz", "Mohamed Ben", "Karim Bouzid"]),
                    "started_at": dt.datetime.combine(batch_date, dt.time(8, 30)),
                    "completed_at": dt.datetime.combine(batch_date, dt.time(15, 0)),
                },
            )
            if created:
                count += 1
        self.stdout.write(f"  Uretim partisi: +{count} (toplam {ProductionBatch.objects.count()})")

    # =====================================================================
    def seed_qc_results(self):
        from production.models import ProductionBatch
        from quality.models import QCParameter, QCTestResult
        from django.contrib.auth.models import User

        params = list(QCParameter.objects.filter(is_active=True))
        batches = list(ProductionBatch.objects.all()[:30])
        if not params or not batches:
            return

        tester = User.objects.filter(username="lab.tech").first()
        tester_name = tester.username if tester else "lab.tech"

        count = 0
        for batch in batches:
            for param in random.sample(params, min(3, len(params))):
                if QCTestResult.objects.filter(parameter=param, batch=batch).exists():
                    continue
                value = Decimal(str(round(random.uniform(0.5, 100.0), 3)))
                verdict = random.choices(
                    [QCTestResult.Verdict.PASS, QCTestResult.Verdict.FAIL],
                    weights=[92, 8], k=1
                )[0]
                QCTestResult.objects.create(
                    parameter=param, batch=batch,
                    value=value, verdict=verdict,
                    tester=tester_name,
                    notes=f"Rutin QC testi - {param.code}",
                )
                count += 1
        self.stdout.write(f"  QC test sonucu: +{count}")

    # =====================================================================
    def seed_ncr_capa(self):
        from qms.models import Nonconformance, CAPA
        from django.contrib.auth.models import User

        qa = User.objects.filter(username="qa.manager").first() or User.objects.first()
        tm = User.objects.filter(username="tm.director").first() or User.objects.first()

        ncr_samples = [
            ("NCR-2026-001", "Klorur limit ustunde", "COA'da klorur 350ppm, spec 300ppm",
             "PROCESS", "MEDIUM"),
            ("NCR-2026-002", "Ambalaj hasarli teslim", "5 IBC hasarli teslim edildi",
             "SUPPLIER", "LOW"),
            ("NCR-2026-003", "Yogunluk spec disi", "Batch 202605-005 yogunluk 1.15 (spec 1.05-1.10)",
             "PROCESS", "HIGH"),
            ("NCR-2026-004", "Musteri sikayeti - kur suresi",
             "SARL Blida'dan gelen sikayet: kur suresi 30dk (spec 25dk)",
             "CUSTOMER", "MEDIUM"),
            ("NCR-2026-005", "SCADA kalibrasyon sapmasi",
             "Reactor-2 termokupl kalibrasyonu 2 derece kaymis", "PROCESS", "MEDIUM"),
            ("NCR-2026-006", "Fatura eslesme hatasi (denetim bulgusu)",
             "IA-2026-Q1: 3 fatura PO ile eslesmiyor", "SYSTEM", "LOW"),
        ]
        for num, title, desc, source, severity in ncr_samples:
            Nonconformance.objects.get_or_create(
                ncr_number=num,
                defaults={
                    "source": source,
                    "severity": severity,
                    "detected_at": dt.datetime.now() - dt.timedelta(days=random.randint(10, 90)),
                    "detected_by": qa,
                    "title": title,
                    "description": desc,
                    "status": random.choice([
                        Nonconformance.Status.OPEN,
                        Nonconformance.Status.INVESTIGATING,
                        Nonconformance.Status.CLOSED,
                    ]),
                },
            )

        capa_samples = [
            ("CAPA-2026-001", "PC uygunsuzluk kok neden",
             "Klorur limit ihlali icin kok neden analizi",
             "Hammadde tedarikci degistirme + gelen malzemede spot QC",
             "CORRECTIVE"),
            ("CAPA-2026-002", "Ambalaj kalite standardi",
             "Ambalaj tedarikcisi ile spec revizyonu",
             "SLA guncelleme + gelen kontrol", "PREVENTIVE"),
            ("CAPA-2026-003", "SCADA kalibrasyon periyodu",
             "Kalibrasyon periyodunu 6 aydan 3 aya cekmek",
             "Yeni PM plani + eksik ekipman etiketleme", "PREVENTIVE"),
        ]
        for num, title, desc, action, cap_type in capa_samples:
            CAPA.objects.get_or_create(
                capa_number=num,
                defaults={
                    "type": cap_type,
                    "title": title,
                    "description": desc,
                    "action_plan": action,
                    "owner": tm,
                    "status": random.choice([CAPA.Status.PLANNED, CAPA.Status.IN_PROGRESS]),
                    "target_date": dt.date.today() + dt.timedelta(days=random.randint(15, 60)),
                },
            )
        self.stdout.write(f"  NCR: {Nonconformance.objects.count()}, CAPA: {CAPA.objects.count()}")

    # =====================================================================
    def seed_ehs_incidents(self):
        from ehs.models import Incident
        from django.contrib.auth.models import User

        hse = User.objects.filter(username="hse.officer").first() or User.objects.first()

        samples = [
            ("INC-2026-001", "NEAR_MISS", "FIRST_AID",
             "Reactor alaninda ramak kala - dokum", "Reactor 1 alani"),
            ("INC-2026-002", "PROPERTY_DAMAGE", "MINOR",
             "IBC dolum hattinda hasar", "IBC dolum hatti"),
            ("INC-2026-003", "CHEMICAL_EXPOSURE", "FIRST_AID",
             "SP dokulmesi - kucuk maruziyet", "Depo - kimyasal alan"),
            ("INC-2026-004", "ENVIRONMENTAL", "MEDICAL",
             "Yagmur suyu drenajinda kirlilik izi", "Cevre alani"),
        ]
        for num, itype, sev, desc, loc in samples:
            Incident.objects.get_or_create(
                incident_number=num,
                defaults={
                    "type": itype,
                    "severity": sev,
                    "occurred_at": dt.datetime.now() - dt.timedelta(days=random.randint(5, 60)),
                    "location": loc,
                    "description": desc,
                    "reported_by": hse,
                    "status": random.choice(["INVESTIGATING", "CLOSED"]),
                },
            )
        self.stdout.write(f"  Incident: {Incident.objects.count()}")

    # =====================================================================
    def seed_cmms_workorders(self):
        from cmms.models import Equipment, WorkOrder
        from django.contrib.auth.models import User

        maint = User.objects.filter(username="maint.tech").first() or User.objects.first()
        equipments = list(Equipment.objects.all()[:5])
        if not equipments:
            return

        for i in range(12):
            eq = random.choice(equipments)
            wo_no = f"WO-2026-{i+1:04d}"
            future = dt.date.today() + dt.timedelta(days=random.randint(-30, 30))
            sstart = dt.datetime.combine(future, dt.time(9, 0))
            WorkOrder.objects.get_or_create(
                work_order_number=wo_no,
                defaults={
                    "equipment": eq,
                    "type": random.choice(["PREVENTIVE", "CORRECTIVE", "INSPECTION"]),
                    "priority": random.choice(["LOW", "MEDIUM", "HIGH"]),
                    "description": f"{eq.name} bakim/onarim",
                    "requested_by": maint,
                    "assigned_to": maint,
                    "scheduled_start": sstart,
                    "scheduled_end": sstart + dt.timedelta(hours=4),
                    "status": random.choice(["PLANNED", "IN_PROGRESS", "COMPLETED"]),
                },
            )
        self.stdout.write(f"  Is emri: {WorkOrder.objects.count()}")

    # =====================================================================
    def seed_purchase_orders(self):
        from purchasing.models import PurchaseOrder, PurchaseOrderLine
        from masterdata.models import RawMaterial, Supplier

        sups = list(Supplier.objects.filter(is_active=True))
        rms = list(RawMaterial.objects.all()[:5])
        if not sups or not rms:
            return

        today = dt.date.today()
        for i in range(15):
            days_ago = random.randint(0, 120)
            po_date = today - dt.timedelta(days=days_ago)
            po_no = f"PO-2026-{i+1:04d}"
            po, _ = PurchaseOrder.objects.get_or_create(
                order_number=po_no,
                defaults={
                    "supplier": random.choice(sups),
                    "order_date": po_date,
                    "expected_date": po_date + dt.timedelta(days=15),
                    "status": random.choice(["APPROVED", "PARTIAL", "RECEIVED", "DRAFT"]),
                },
            )
            # 1-3 satir
            for j in range(random.randint(1, 3)):
                rm = random.choice(rms)
                qty = Decimal(random.randint(100, 2000))
                price = Decimal(str(round(random.uniform(50, 500), 2)))
                PurchaseOrderLine.objects.get_or_create(
                    po=po, raw_material=rm,
                    defaults={
                        "quantity": qty,
                        "unit_price": price,
                        "unit": rm.unit,
                    },
                )
        self.stdout.write(f"  Satin alma emri: {PurchaseOrder.objects.count()}")

    # =====================================================================
    def seed_sales_orders_shipments(self):
        from sales.models import SalesOrder, SalesOrderLine
        from masterdata.models import Customer, Product

        customers = list(Customer.objects.filter(is_active=True))
        products = list(Product.objects.all()[:3])
        if not customers or not products:
            return

        today = dt.date.today()
        for i in range(15):
            days_ago = random.randint(0, 90)
            so_date = today - dt.timedelta(days=days_ago)
            so_no = f"SO-2026-{i+1:04d}"
            so, _ = SalesOrder.objects.get_or_create(
                order_number=so_no,
                defaults={
                    "customer": random.choice(customers),
                    "order_date": so_date,
                    "delivery_date": so_date + dt.timedelta(days=7),
                    "status": random.choice(["APPROVED", "PARTIAL", "SHIPPED", "DRAFT"]),
                },
            )
            for j in range(random.randint(1, 2)):
                p = random.choice(products)
                qty = Decimal(random.randint(500, 3000))
                price = Decimal(str(round(random.uniform(100, 400), 2)))
                SalesOrderLine.objects.get_or_create(
                    so=so, product=p,
                    defaults={
                        "quantity": qty,
                        "unit_price": price,
                        "unit": p.unit,
                    },
                )
        self.stdout.write(f"  Satis siparisi: {SalesOrder.objects.count()}")

    # =====================================================================
    def seed_invoices_payments(self):
        # Bu zaten seed_finance_demo scriptinden yapildi; sadece tamamlanmayanları ekle
        self.stdout.write("  Fatura/odemeler seed_finance_demo scriptinden geldi (atlaniyor)")

    # =====================================================================
    def seed_docs(self):
        from django.contrib.auth.models import User
        from docs.models import ControlledDocument, DocumentCategory

        cats = [
            ("PROC", "Prosedur"),
            ("SOP",  "Standart Operasyon"),
            ("FRM",  "Form"),
            ("POL",  "Politika"),
        ]
        for code, name in cats:
            DocumentCategory.objects.get_or_create(code=code, defaults={"name": name})

        docs = [
            ("SOP-PRD-001", "PROD-01 Uretim Partisi Baslatma SOP", "SOP"),
            ("SOP-QC-001",  "QC-01 Yogunluk Testi", "SOP"),
            ("SOP-QC-002",  "QC-02 pH Olcumu", "SOP"),
            ("SOP-WHL-001", "WHL-01 Mal Kabul Prosedu", "SOP"),
            ("PROC-QMS-001", "QMS-01 NCR Yonetim Prosedu", "PROC"),
            ("PROC-QMS-002", "QMS-02 CAPA Yonetim Prosedu", "PROC"),
            ("FRM-QC-001", "QC Test Sonuç Formu", "FRM"),
            ("POL-01", "Kalite Politikasi", "POL"),
        ]
        qa = User.objects.filter(username="qa.manager").first() or User.objects.first()
        for num, title, cat_code in docs:
            cat = DocumentCategory.objects.get(code=cat_code)
            ControlledDocument.objects.get_or_create(
                document_number=num,
                defaults={"category": cat, "title": title, "process_owner": qa},
            )
        self.stdout.write(f"  Kontrollu dokuman: {ControlledDocument.objects.count()}")

    # =====================================================================
    def seed_governance(self):
        from governance.models import (
            AuditPlan, InternalAudit, ManagementReview,
        )
        from django.contrib.auth.models import User

        auditor = User.objects.filter(username="audit.internal").first() or User.objects.first()
        qa = User.objects.filter(username="qa.manager").first() or User.objects.first()

        # Once bir audit plan olusturayim
        plan, _ = AuditPlan.objects.get_or_create(
            code="AP-2026",
            defaults={"year": 2026, "description": "2026 yillik ic denetim plani"},
        )

        # 3 ic denetim
        for i, (num, scope) in enumerate([
            ("IA-2026-Q1", "1. Ceyrek Kalite Denetimi - QMS + Uretim + Depo"),
            ("IA-2026-Q2", "2. Ceyrek EHS Denetimi - EHS + CMMS"),
            ("IA-2026-Q3", "3. Ceyrek Muhasebe Denetimi - Fatura + PO eslesmesi"),
        ]):
            InternalAudit.objects.get_or_create(
                audit_number=num,
                defaults={
                    "plan": plan,
                    "scope": scope,
                    "scheduled_date": dt.date(2026, i*3+1, 15),
                    "lead_auditor": auditor,
                    "status": "COMPLETED" if i < 2 else "PLANNED",
                },
            )

        # 2 yonetim gozden gecirme
        for i, num in enumerate([
            "MR-2026-H1",
            "MR-2026-H2",
        ]):
            ManagementReview.objects.get_or_create(
                review_number=num,
                defaults={
                    "meeting_date": dt.date(2026, i*6+3, 20),
                    "chairperson": qa,
                },
            )
        self.stdout.write(f"  Ic denetim: {InternalAudit.objects.count()}, YGG: {ManagementReview.objects.count()}")
