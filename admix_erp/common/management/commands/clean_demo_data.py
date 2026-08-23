"""Demo/örnek verileri temizler — çalışan denemesi için hazır sistem bırakır.

İki mod:
  --soft (varsayılan): Sadece işlem verilerini siler (fatura, batch, ödeme, BL, vs.)
                      Master data korunur (ürün, hammadde, reçete, spec, kullanıcı).
  --hard: Yumuşak temizlik + müşteri/tedarikçi/ürün/hammadde/reçete gibi
          demo master data da silinir.

Her iki modda da KORUNAN veriler:
  - Kullanıcılar, gruplar, permission'lar (Django auth)
  - SCADA bridge kullanıcısı ve token
  - Mali yıl, dönem, TVA oranları, hesap planı (SCF PCN 2010)
  - Şirket profili (CompanyProfile)
  - Business Line, Controlled Code (MCOS altyapı)
  - Depo bölgesi (StorageZone), tehlike uyumsuzlukları

Kullanım:
    python manage.py clean_demo_data --dry-run       # Öngörü — hiçbir şey silinmez
    python manage.py clean_demo_data --soft --confirm # Yumuşak temizlik
    python manage.py clean_demo_data --hard --confirm # Sıkı temizlik

--confirm olmadan çalışmaz (kaza koruması).
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction


# ---------------------------------------------------------------------------
# TABLO SİLME SIRALARI (FK bağımlılıklarına göre)
# ---------------------------------------------------------------------------

# İşlem verileri (soft + hard'da silinir)
TRANSACTIONAL_MODELS = [
    # Muhasebe — bağımlılık: JournalLine < JournalEntry, Payment < Invoice
    ("accounting", "AdvanceAllocation"),
    ("accounting", "CustomerAdvance"),
    ("accounting", "Payment"),
    ("accounting", "JournalLine"),
    ("accounting", "JournalEntry"),
    ("accounting", "InvoiceLine"),
    ("accounting", "ExpenseInvoice"),
    ("accounting", "Invoice"),
    ("accounting", "DepreciationEntry"),
    ("accounting", "FixedAsset"),
    ("accounting", "TVADeclaration"),

    # Satış — Delivery/BL bağımlılıkları
    ("sales", "PerformanceWarranty"),
    ("sales", "ApplicatorTraining"),
    ("sales", "MixDesignConsultation"),
    ("sales", "TrialBatch"),
    ("sales", "DeliveryTrip"),
    ("sales", "ShipmentLine"),
    ("sales", "Shipment"),
    ("sales", "SalesOrderLine"),
    ("sales", "SalesOrder"),

    # Kalite (test sonuçları, COA, saha testleri)
    ("quality", "CustomerSiteTest"),
    ("quality", "QCTestResult"),
    ("quality", "CertificateOfAnalysis"),

    # QMS (NCR, CAPA, sapma)
    ("qms", "CorrectiveActionPreventiveAction"),
    ("qms", "Deviation"),
    ("qms", "Nonconformance"),

    # Chemicals (opsiyonel — retention numunesi işlem)
    ("chemicals", "RetentionSample"),

    # Üretim (batch, tüketim, IBC, kampanya, order)
    ("production", "OutputContainer"),
    ("production", "MaterialConsumption"),
    ("production", "ProductionBatch"),
    ("production", "ProductionCampaign"),
    ("production", "ProductionOrder"),

    # Satın alma (PO, GR)
    ("purchasing", "GoodsReceiptLine"),
    ("purchasing", "GoodsReceipt"),
    ("purchasing", "PurchaseOrderLine"),
    ("purchasing", "PurchaseOrder"),

    # Stok (hareketler, ajustement, lotlar)
    ("inventory", "StockAdjustmentLine"),
    ("inventory", "StockAdjustment"),
    ("inventory", "StockMovement"),
    ("inventory", "RawMaterialLot"),  # lot'lar da işlem verisi — yeni mal kabul yapılacak

    # CMMS (iş emirleri, sensor alertler)
    ("cmms", "SparePartConsumption"),
    ("cmms", "CalibrationRecord"),
    ("cmms", "WorkOrder"),
    ("cmms", "SensorAlert"),

    # MCOS records (Case/RecordInstance/Evidence/Decision/Signature)
    ("records", "Signature"),
    ("records", "Decision"),
    ("records", "Evidence"),
    ("records", "RecordInstance"),
    ("records", "Case"),

    # Master Register
    ("master_register", "SecurityEventRegister"),
    ("master_register", "IntegratedMasterRegister"),

    # Kural ihlalleri
    ("rules", "Violation"),

    # Notifications
    ("notifications", "Notification"),

    # SCADA (recipe download, batch download)
    ("scada", "RecipeDownload"),
]

# Sıkı temizlikte silinecek demo master data (müşteri/tedarikçi/ürün)
DEMO_MASTER_MODELS = [
    ("masterdata", "Customer"),
    ("masterdata", "Supplier"),
    # NOT: Product, RawMaterial, Recipe, QCSpec, SamplingPlan KORUNUR
]

# Her iki modda da KORUNAN modeller (referans/altyapı)
PROTECTED_MODELS = {
    "auth.User", "auth.Group", "auth.Permission",
    "authtoken.Token",
    "masterdata.Product", "masterdata.RawMaterial",
    "masterdata.Container", "masterdata.UnitOfMeasure",
    "masterdata.CompanyProfile",
    "formulation.Recipe", "formulation.RecipeLine",
    "quality.QCParameter", "quality.QCSpec", "quality.SamplingPlan",
    "accounting.FiscalYear", "accounting.Period",
    "accounting.TVARate", "accounting.Account", "accounting.JournalCode",
    "chemicals.ChemicalProfile", "chemicals.Pictogram",
    "chemicals.HazardStatement", "chemicals.PrecautionaryStatement",
    "chemicals.NotifiedBody", "chemicals.FPCTestPlan",
    "chemicals.CertificateOfConformity", "chemicals.SafetyDataSheet",
    "chemicals.DeclarationOfPerformance", "chemicals.FPCAudit",
    "chemicals.StorageZone", "chemicals.StorageIncompatibility",
    "businessline.BusinessLine",
    "registry.ControlledCode",
    "cmms.Equipment", "cmms.SparePart", "cmms.MaintenancePlan",
    "cmms.CalibrationSchedule",
}


class Command(BaseCommand):
    help = "Demo verileri temizle (soft/hard mod)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--soft", action="store_true",
            help="Yumuşak temizlik — sadece işlem verileri (varsayılan)",
        )
        parser.add_argument(
            "--hard", action="store_true",
            help="Sıkı temizlik — işlem + demo müşteri/tedarikçi",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Öngörü — hiçbir şey silinmez, sadece raporlanır",
        )
        parser.add_argument(
            "--confirm", action="store_true",
            help="Kaza koruması — bu flag olmadan çalışmaz",
        )

    def handle(self, *args, **options):
        soft = options["soft"]
        hard = options["hard"]
        dry = options["dry_run"]
        confirm = options["confirm"]

        # Mode seçimi
        if not soft and not hard:
            soft = True  # varsayılan

        if soft and hard:
            self.stderr.write(self.style.ERROR(
                "HATA: --soft ve --hard aynı anda kullanılamaz."
            ))
            return

        # Confirm kontrolü
        if not dry and not confirm:
            self.stderr.write(self.style.ERROR(
                "HATA: --confirm olmadan çalışmaz. Kaza koruması."
            ))
            self.stdout.write("Önce --dry-run ile deneyin.")
            self.stdout.write("Emin olduktan sonra --confirm ekleyin.")
            return

        # Model listesini oluştur
        models_to_delete = list(TRANSACTIONAL_MODELS)
        if hard:
            models_to_delete.extend(DEMO_MASTER_MODELS)

        # Başlık
        mode_name = "SIKI TEMIZLIK (--hard)" if hard else "YUMUSAK TEMIZLIK (--soft)"
        if dry:
            mode_name = f"[DRY-RUN] {mode_name}"

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("=" * 70))
        self.stdout.write(self.style.WARNING(f"  {mode_name}"))
        self.stdout.write(self.style.WARNING("=" * 70))
        self.stdout.write("")

        total_deleted = 0
        try:
            with transaction.atomic():
                for app_label, model_name in models_to_delete:
                    try:
                        from django.apps import apps
                        Model = apps.get_model(app_label, model_name)
                    except LookupError:
                        self.stdout.write(f"  !  {app_label}.{model_name} bulunamadi (atlaniyor)")
                        continue

                    count = Model.objects.count()
                    if count == 0:
                        continue

                    if dry:
                        self.stdout.write(
                            f"  [DRY] {app_label}.{model_name}: {count} kayit silinecek"
                        )
                    else:
                        Model.objects.all().delete()
                        self.stdout.write(self.style.SUCCESS(
                            f"  OK {app_label}.{model_name}: {count} kayit silindi"
                        ))
                    total_deleted += count

                if dry:
                    # Transaction'ı geri al
                    raise KeyboardInterrupt("dry-run rollback")

        except KeyboardInterrupt:
            # dry-run için beklenen — bir şey yapma
            pass

        # Özet
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        if dry:
            self.stdout.write(self.style.SUCCESS(
                f"  DRY-RUN TAMAM · Silinecek toplam: {total_deleted} kayit"
            ))
            self.stdout.write("")
            self.stdout.write("  Gercek silme icin: --confirm flag'i ekleyin")
        else:
            self.stdout.write(self.style.SUCCESS(
                f"  TEMIZLIK TAMAM · Silinen toplam: {total_deleted} kayit"
            ))
            self.stdout.write("")
            self.stdout.write("  KORUNANLAR (dokunulmadi):")
            for m in sorted(PROTECTED_MODELS):
                self.stdout.write(f"    - {m}")
        self.stdout.write(self.style.SUCCESS("=" * 70))
