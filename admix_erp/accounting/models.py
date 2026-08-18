"""Cezayir SCF muhasebe modelleri (PCN 2010).

Referanslar:
- Ministerial Order No. 26 of 29 July 2008 (SCF hesap planı ve muhasebe kuralları)
- Executive Decree No. 11-24 of 27 January 2011 (Ulusal Muhasebe Konseyi)
- CTCA (Code des Taxes sur le Chiffre d'Affaires) — TVA %19 varsayılan
- G50 aylık beyan formu

SCF ana hesap sınıfları:
  1 Comptes de capitaux (Sermaye)
  2 Comptes d'immobilisations (Duran varlıklar)
  3 Comptes de stocks et en-cours (Stoklar)
  4 Comptes de tiers (Alacaklar/Borçlar — cari)
  5 Comptes financiers (Finansal — banka/kasa)
  6 Comptes de charges (Giderler)
  7 Comptes de produits (Gelirler)
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from common.models import TimeStamped
from cmms.models import Equipment
from masterdata.models import Customer, Product, Supplier


ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# Hesap planı
# ---------------------------------------------------------------------------

class Account(TimeStamped):
    """SCF hesap planı düğümü. Kod ilk hanesi sınıfı belirler (1-7)."""

    class Class(models.TextChoices):
        CAPITAL = "1", "1 - Sermaye"
        FIXED_ASSETS = "2", "2 - Duran varlıklar"
        INVENTORY = "3", "3 - Stoklar"
        THIRD_PARTIES = "4", "4 - Cariler (alacaklar/borçlar)"
        FINANCIAL = "5", "5 - Finansal"
        EXPENSES = "6", "6 - Giderler"
        REVENUES = "7", "7 - Gelirler"

    class Type(models.TextChoices):
        ASSET = "ASSET", "Aktif (Debit natur)"
        LIABILITY = "LIABILITY", "Pasif (Kredi natur)"
        EQUITY = "EQUITY", "Özkaynak"
        REVENUE = "REVENUE", "Gelir"
        EXPENSE = "EXPENSE", "Gider"

    code = models.CharField("Hesap kodu", max_length=20, unique=True)
    name = models.CharField("Hesap adı", max_length=200)
    account_class = models.CharField(
        "Sınıf", max_length=1, choices=Class.choices,
    )
    account_type = models.CharField(
        "Tip", max_length=12, choices=Type.choices,
    )
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="children", verbose_name="Üst hesap",
    )
    is_leaf = models.BooleanField(
        "Yaprak (post edilebilir)", default=True,
        help_text="False ise sadece toplam görevi görür.",
    )
    is_analytic = models.BooleanField("Analitik", default=False)
    currency = models.CharField("Para birimi", max_length=5, default="DZD")
    is_active = models.BooleanField("Aktif", default=True)
    tva_default = models.ForeignKey(
        "TVARate", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="default_accounts", verbose_name="Varsayılan TVA",
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Hesap"
        verbose_name_plural = "Hesap Planı"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"

    def save(self, *args, **kwargs):
        if self.code:
            self.account_class = self.code[0]
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# TVA (KDV)
# ---------------------------------------------------------------------------

class TVARate(TimeStamped):
    """KDV oranı. Cezayir standart %19."""

    code = models.CharField("Kod", max_length=10, unique=True)
    name = models.CharField("Ad", max_length=60)
    rate_pct = models.DecimalField("Oran (%)", max_digits=5, decimal_places=2)
    collected_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, null=True, blank=True,
        related_name="tva_collected_for",
        verbose_name="Tahsil TVA hesabı (4457)",
    )
    deductible_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, null=True, blank=True,
        related_name="tva_deductible_for",
        verbose_name="İndirim TVA hesabı (44562)",
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "TVA Oranı"
        verbose_name_plural = "TVA Oranları"
        ordering = ["-rate_pct"]

    def __str__(self) -> str:
        return f"{self.name} ({self.rate_pct}%)"


# ---------------------------------------------------------------------------
# Mali yıl + Dönem
# ---------------------------------------------------------------------------

class FiscalYear(TimeStamped):
    """Mali yıl (Cezayir'de takvim yılı: 01/01 - 31/12)."""

    year = models.PositiveIntegerField("Yıl", unique=True)
    start_date = models.DateField("Başlangıç")
    end_date = models.DateField("Bitiş")
    is_closed = models.BooleanField("Kapatıldı", default=False)
    closed_at = models.DateTimeField("Kapanış zamanı", null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="closed_fiscal_years", verbose_name="Kapatan",
    )

    class Meta:
        verbose_name = "Mali Yıl"
        verbose_name_plural = "Mali Yıllar"
        ordering = ["-year"]

    def __str__(self) -> str:
        return f"Mali Yıl {self.year}"


class Period(TimeStamped):
    """Aylık muhasebe dönemi. Cezayir'de TVA aylık — dönem = ay."""

    class Status(models.TextChoices):
        OPEN = "OPEN", "Açık"
        LOCKED = "LOCKED", "Kilitli"
        CLOSED = "CLOSED", "Kapatıldı"

    fiscal_year = models.ForeignKey(
        FiscalYear, on_delete=models.CASCADE,
        related_name="periods", verbose_name="Mali yıl",
    )
    year = models.PositiveIntegerField("Yıl")
    month = models.PositiveSmallIntegerField("Ay")
    status = models.CharField(
        "Durum", max_length=8, choices=Status.choices, default=Status.OPEN
    )
    closed_at = models.DateTimeField("Kapanış zamanı", null=True, blank=True)

    class Meta:
        verbose_name = "Dönem"
        verbose_name_plural = "Dönemler"
        unique_together = (("year", "month"),)
        ordering = ["-year", "-month"]

    def __str__(self) -> str:
        return f"{self.year}-{self.month:02d} ({self.status})"


# ---------------------------------------------------------------------------
# Yevmiye (Journal)
# ---------------------------------------------------------------------------

class JournalCode(TimeStamped):
    """Yevmiye türü — SCF'de farklı defter tutmak için (JV, JA, JB vb.)."""

    class Type(models.TextChoices):
        SALES = "SALES", "Satış yevmiyesi"
        PURCHASE = "PURCHASE", "Satın alma yevmiyesi"
        BANK = "BANK", "Banka"
        CASH = "CASH", "Kasa"
        OPERATIONS = "OPERATIONS", "Muhtelif işlemler"
        OPENING = "OPENING", "Açılış"
        CLOSING = "CLOSING", "Kapanış"
        PAYROLL = "PAYROLL", "Bordro"
        DEPRECIATION = "DEPRECIATION", "Amortisman"

    code = models.CharField("Kod", max_length=10, unique=True,
                             help_text="Örn. JV (satış), JA (satın alma), JB (banka)")
    name = models.CharField("Ad", max_length=100)
    type = models.CharField("Tip", max_length=12, choices=Type.choices)
    default_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="default_journals", verbose_name="Karşı hesap (banka/kasa vb.)",
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Yevmiye Kodu"
        verbose_name_plural = "Yevmiye Kodları"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class JournalEntry(TimeStamped):
    """Yevmiye kaydı başlığı (écriture comptable)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        POSTED = "POSTED", "Kesin"
        CANCELLED = "CANCELLED", "İptal"

    entry_number = models.CharField("Fiş no", max_length=40, unique=True)
    journal_code = models.ForeignKey(
        JournalCode, on_delete=models.PROTECT,
        related_name="entries", verbose_name="Yevmiye",
    )
    period = models.ForeignKey(
        Period, on_delete=models.PROTECT,
        related_name="entries", verbose_name="Dönem",
    )
    entry_date = models.DateField("Tarih")
    description = models.CharField("Açıklama", max_length=255)
    reference = models.CharField(
        "Belge referansı", max_length=80, blank=True,
        help_text="Fatura no / dekont no / irsaliye no",
    )
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    posted_at = models.DateTimeField("Kesinleşme zamanı", null=True, blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="posted_entries", verbose_name="Kesinleştiren",
    )
    reversed_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reversal_of", verbose_name="İptal fişi",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Yevmiye Fişi"
        verbose_name_plural = "Yevmiye Fişleri"
        ordering = ["-entry_date", "-entry_number"]

    def __str__(self) -> str:
        return f"{self.entry_number} · {self.entry_date}"

    @property
    def total_debit(self) -> Decimal:
        return self.lines.aggregate(t=models.Sum("debit"))["t"] or ZERO

    @property
    def total_credit(self) -> Decimal:
        return self.lines.aggregate(t=models.Sum("credit"))["t"] or ZERO

    @property
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit


class JournalLine(TimeStamped):
    """Yevmiye satırı — bir hesabın borç veya alacak hareketi."""

    entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE,
        related_name="lines", verbose_name="Fiş",
    )
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT,
        related_name="journal_lines", verbose_name="Hesap",
    )
    debit = models.DecimalField(
        "Borç", max_digits=14, decimal_places=2, default=ZERO
    )
    credit = models.DecimalField(
        "Alacak", max_digits=14, decimal_places=2, default=ZERO
    )
    description = models.CharField("Açıklama", max_length=255, blank=True)

    # Analitik referanslar
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ledger_lines", verbose_name="Müşteri",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ledger_lines", verbose_name="Tedarikçi",
    )

    class Meta:
        verbose_name = "Yevmiye Satırı"
        verbose_name_plural = "Yevmiye Satırları"
        indexes = [
            models.Index(fields=["account", "entry"]),
        ]

    def __str__(self) -> str:
        d = f"D {self.debit}" if self.debit else ""
        c = f"K {self.credit}" if self.credit else ""
        return f"{self.account.code} {d}{c}"


# ---------------------------------------------------------------------------
# Fatura (AR/AP)
# ---------------------------------------------------------------------------

class Invoice(TimeStamped):
    """Fatura başlığı — satış (AR) veya satın alma (AP)."""

    class Type(models.TextChoices):
        SALES = "SALES", "Satış (AR)"
        PURCHASE = "PURCHASE", "Satın alma (AP)"
        CREDIT_NOTE_SALES = "CN_SALES", "Alacak dekontu - satış (avoir)"
        CREDIT_NOTE_PURCHASE = "CN_PURCHASE", "Alacak dekontu - satın alma"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        POSTED = "POSTED", "Muhasebeleşti"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Kısmi ödendi"
        PAID = "PAID", "Ödendi"
        CANCELLED = "CANCELLED", "İptal"

    invoice_number = models.CharField("Fatura no", max_length=40, unique=True)
    type = models.CharField("Tip", max_length=12, choices=Type.choices)
    date = models.DateField("Fatura tarihi")
    due_date = models.DateField("Vade tarihi", null=True, blank=True)
    period = models.ForeignKey(
        Period, on_delete=models.PROTECT,
        related_name="invoices", verbose_name="Dönem",
    )
    currency = models.CharField("Para birimi", max_length=5, default="DZD")

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, null=True, blank=True,
        related_name="invoices", verbose_name="Müşteri",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, null=True, blank=True,
        related_name="invoices", verbose_name="Tedarikçi",
    )

    # Kaynak belge bağlantıları
    shipment_reference = models.CharField(
        "Sevkiyat referansı", max_length=80, blank=True,
    )
    receipt_reference = models.CharField(
        "Mal kabul referansı", max_length=80, blank=True,
    )

    total_ht = models.DecimalField(
        "Toplam HT (KDVsiz)", max_digits=14, decimal_places=2, default=ZERO
    )
    total_tva = models.DecimalField(
        "Toplam TVA", max_digits=14, decimal_places=2, default=ZERO
    )
    total_ttc = models.DecimalField(
        "Toplam TTC (KDV dahil)", max_digits=14, decimal_places=2, default=ZERO
    )
    amount_paid = models.DecimalField(
        "Ödenen", max_digits=14, decimal_places=2, default=ZERO
    )
    status = models.CharField(
        "Durum", max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    journal_entry = models.OneToOneField(
        JournalEntry, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="source_invoice", verbose_name="Yevmiye fişi",
    )
    # Fatura eki — orijinal fatura PDF / taranmış görsel / e-fatura dosyası
    attachment = models.FileField(
        "Fatura eki (PDF/JPG/PNG)",
        upload_to="invoices/%Y/%m/", null=True, blank=True,
        help_text="Orijinal fatura belgesi (PDF veya tarama). Maks 10 MB.",
    )
    attachment_note = models.CharField(
        "Ek açıklaması", max_length=200, blank=True,
        help_text="Örn. 'Tedarikçi orijinali', 'DGI tebliğ dosyası'",
    )
    notes = models.TextField("Notlar", blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Fatura"
        verbose_name_plural = "Faturalar"
        ordering = ["-date", "-invoice_number"]

    def __str__(self) -> str:
        return f"{self.invoice_number} · {self.get_type_display()}"

    @property
    def amount_due(self) -> Decimal:
        return (self.total_ttc or ZERO) - (self.amount_paid or ZERO)

    @property
    def has_attachment(self) -> bool:
        return bool(self.attachment)


class InvoiceLine(TimeStamped):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE,
        related_name="lines", verbose_name="Fatura",
    )
    sequence = models.PositiveIntegerField("Sıra", default=1)
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invoice_lines", verbose_name="Ürün",
    )
    description = models.CharField("Açıklama", max_length=255)
    quantity = models.DecimalField(
        "Miktar", max_digits=12, decimal_places=4, default=Decimal("1")
    )
    unit_price = models.DecimalField(
        "Birim fiyat (HT)", max_digits=12, decimal_places=4
    )
    tva_rate = models.ForeignKey(
        TVARate, on_delete=models.PROTECT,
        related_name="invoice_lines", verbose_name="TVA oranı",
    )
    ht_amount = models.DecimalField(
        "HT tutar", max_digits=14, decimal_places=2, default=ZERO
    )
    tva_amount = models.DecimalField(
        "TVA tutar", max_digits=14, decimal_places=2, default=ZERO
    )
    ttc_amount = models.DecimalField(
        "TTC tutar", max_digits=14, decimal_places=2, default=ZERO
    )
    revenue_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, null=True, blank=True,
        related_name="revenue_invoice_lines",
        verbose_name="Gelir/gider hesabı (6 veya 7)",
    )

    class Meta:
        verbose_name = "Fatura Satırı"
        verbose_name_plural = "Fatura Satırları"
        ordering = ["invoice", "sequence"]

    def __str__(self) -> str:
        return f"{self.invoice.invoice_number} · #{self.sequence} {self.description[:40]}"

    def recompute(self) -> None:
        self.ht_amount = (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        self.tva_amount = (self.ht_amount * self.tva_rate.rate_pct / Decimal("100")).quantize(
            Decimal("0.01"))
        self.ttc_amount = self.ht_amount + self.tva_amount


# ---------------------------------------------------------------------------
# Ödeme
# ---------------------------------------------------------------------------

class Payment(TimeStamped):
    """Fatura tahsilat/tediye ödemesi.

    Cezayir'de çek (chèque) B2B tediye/tahsilatta yaygın; post-dated çek
    de sık kullanılır. `method=CHECK` seçildiğinde ek alanlar (banka,
    çek no, keşide/vade, durum, görsel) doldurulur.
    """

    class Direction(models.TextChoices):
        INCOMING = "INCOMING", "Tahsilat (müşteriden)"
        OUTGOING = "OUTGOING", "Tediye (tedarikçiye)"

    class Method(models.TextChoices):
        BANK_TRANSFER = "BANK_TRANSFER", "Havale / EFT (Virement)"
        CHECK = "CHECK", "Çek (Chèque)"
        CASH = "CASH", "Nakit (Espèces)"
        LC = "LC", "Akreditif (Crédoc)"
        CARD = "CARD", "Kart (Carte CIB)"

    class AlgerianBank(models.TextChoices):
        """Cezayir bankaları — çek/havalede en yaygın olanlar."""
        BEA = "BEA", "BEA (Banque Extérieure d'Algérie)"
        BNA = "BNA", "BNA (Banque Nationale d'Algérie)"
        CPA = "CPA", "CPA (Crédit Populaire d'Algérie)"
        BADR = "BADR", "BADR (Banque de l'Agriculture)"
        BDL = "BDL", "BDL (Banque de Développement Local)"
        CNEP = "CNEP", "CNEP-Banque"
        AGB = "AGB", "AGB (Gulf Bank Algeria)"
        SGA = "SGA", "SGA (Société Générale Algérie)"
        BNP = "BNP", "BNP Paribas El Djazaïr"
        FRB = "FRB", "Fransabank El Djazaïr"
        TRUST = "TRUST", "Trust Bank Algeria"
        HOUSING = "HOUSING", "Housing Bank"
        OTHER = "OTHER", "Diğer / Other"

    class CheckStatus(models.TextChoices):
        """Çek durumu — çek yaşam döngüsü (Cezayir bankacılık pratiği)."""
        ISSUED = "ISSUED", "Kesildi (Émis)"
        DEPOSITED = "DEPOSITED", "Bankaya yatırıldı (Déposé)"
        CLEARED = "CLEARED", "Tahsil edildi (Encaissé)"
        BOUNCED = "BOUNCED", "Karşılıksız (Impayé)"
        CANCELLED = "CANCELLED", "İptal (Annulé)"

    payment_number = models.CharField("Ödeme no", max_length=40, unique=True)
    date = models.DateField("Tarih")
    direction = models.CharField("Yön", max_length=10, choices=Direction.choices)
    method = models.CharField("Yöntem", max_length=15, choices=Method.choices)
    amount = models.DecimalField("Tutar", max_digits=14, decimal_places=2)
    currency = models.CharField("Para birimi", max_length=5, default="DZD")
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="payments", verbose_name="Müşteri",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="payments", verbose_name="Tedarikçi",
    )
    bank_account = models.ForeignKey(
        Account, on_delete=models.PROTECT,
        related_name="payments", verbose_name="Banka/Kasa hesabı",
    )
    reference = models.CharField("Referans (dekont no)", max_length=80, blank=True)
    invoices = models.ManyToManyField(
        Invoice, blank=True, related_name="payments",
        verbose_name="Kapatılan faturalar",
    )
    journal_entry = models.OneToOneField(
        JournalEntry, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="source_payment", verbose_name="Yevmiye fişi",
    )

    # ---- Cezayir çeki için özel alanlar (method=CHECK iken) ----
    check_number = models.CharField(
        "Çek no", max_length=40, blank=True,
        help_text="Çek üzerindeki sıra numarası",
    )
    check_bank = models.CharField(
        "Çek bankası", max_length=12, blank=True,
        choices=AlgerianBank.choices,
    )
    check_bank_branch = models.CharField(
        "Şube", max_length=100, blank=True,
    )
    check_issue_date = models.DateField(
        "Keşide tarihi", null=True, blank=True,
    )
    check_due_date = models.DateField(
        "Vade tarihi", null=True, blank=True,
        help_text="Post-dated (ileri tarihli) çek için doldurulur.",
    )
    check_status = models.CharField(
        "Çek durumu", max_length=12, blank=True,
        choices=CheckStatus.choices,
    )
    check_drawer_name = models.CharField(
        "Çeki keşide eden", max_length=200, blank=True,
        help_text="Çek üzerindeki keşideci adı (kişi veya şirket).",
    )
    check_image = models.FileField(
        "Çek görseli (fotoğraf/tarama)",
        upload_to="checks/%Y/%m/", null=True, blank=True,
    )
    check_bounce_reason = models.CharField(
        "Karşılıksız gerekçesi", max_length=200, blank=True,
        help_text="check_status = BOUNCED olduğunda banka gerekçesi.",
    )

    # Genel ek (havale dekontu, LC belgesi vs.)
    attachment = models.FileField(
        "Ödeme belgesi (PDF/JPG)",
        upload_to="payments/%Y/%m/", null=True, blank=True,
        help_text="Havale dekontu, LC belgesi veya diğer ödeme evrakı.",
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Ödeme"
        verbose_name_plural = "Ödemeler"
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["method", "check_status"]),
            models.Index(fields=["check_due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.payment_number} · {self.amount} {self.currency}"

    @property
    def is_check(self) -> bool:
        return self.method == self.Method.CHECK

    @property
    def is_post_dated_check(self) -> bool:
        """İleri tarihli çek mi? (keşide sonrası vadeli)"""
        if not self.is_check or not self.check_due_date or not self.check_issue_date:
            return False
        return self.check_due_date > self.check_issue_date

    def clean(self):
        """method=CHECK ise çek alanları zorunlu; değilse doldurulmaz."""
        from django.core.exceptions import ValidationError
        if self.method == self.Method.CHECK:
            required = {
                "check_number": self.check_number,
                "check_bank": self.check_bank,
                "check_issue_date": self.check_issue_date,
            }
            missing = [k for k, v in required.items() if not v]
            if missing:
                raise ValidationError({
                    m: "Çek ile ödemede zorunlu alan." for m in missing
                })


# ---------------------------------------------------------------------------
# TVA / G50 beyan
# ---------------------------------------------------------------------------

class TVADeclaration(TimeStamped):
    """Aylık G50 TVA beyan tablosu (Cezayir)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        SUBMITTED = "SUBMITTED", "Teslim edildi"
        AMENDED = "AMENDED", "Düzeltildi"

    period = models.OneToOneField(
        Period, on_delete=models.CASCADE,
        related_name="tva_declaration", verbose_name="Dönem",
    )
    collected_tva = models.DecimalField(
        "Tahsil edilen TVA", max_digits=14, decimal_places=2, default=ZERO
    )
    deductible_tva = models.DecimalField(
        "İndirilecek TVA", max_digits=14, decimal_places=2, default=ZERO
    )
    net_tva = models.DecimalField(
        "Net TVA (öd./iade)", max_digits=14, decimal_places=2, default=ZERO
    )
    credit_carried_forward = models.DecimalField(
        "Devir alacak", max_digits=14, decimal_places=2, default=ZERO
    )
    submitted_at = models.DateField("Teslim tarihi", null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="submitted_tva_declarations", verbose_name="Teslim eden",
    )
    reference_number = models.CharField(
        "G50 Referans No", max_length=40, blank=True,
    )
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "TVA Beyanı (G50)"
        verbose_name_plural = "TVA Beyanları (G50)"
        ordering = ["-period"]

    def __str__(self) -> str:
        return f"G50 {self.period} · Net {self.net_tva}"


# ---------------------------------------------------------------------------
# Sabit kıymet + amortisman
# ---------------------------------------------------------------------------

class FixedAsset(TimeStamped):
    """Sabit kıymet — SCF sınıf 2 (immobilisations)."""

    class Category(models.TextChoices):
        LAND = "LAND", "Arsa (211)"
        BUILDING = "BUILDING", "Bina (213)"
        MACHINERY = "MACHINERY", "Makine (2154)"
        VEHICLES = "VEHICLES", "Taşıtlar (2182)"
        FURNITURE = "FURNITURE", "Mobilya (2184)"
        IT = "IT", "Bilgi işlem (2183)"
        LAB_EQUIPMENT = "LAB_EQUIPMENT", "Laboratuvar (2157)"
        OTHER = "OTHER", "Diğer"

    class Method(models.TextChoices):
        LINEAR = "LINEAR", "Doğrusal (linéaire)"
        DECLINING = "DECLINING", "Azalan bakiye (dégressif)"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Aktif"
        FULLY_DEPRECIATED = "FULLY_DEPRECIATED", "Tam amorti"
        DISPOSED = "DISPOSED", "Elden çıkarıldı"

    asset_number = models.CharField("Sabit kıymet no", max_length=40, unique=True)
    name = models.CharField("Ad", max_length=200)
    category = models.CharField("Kategori", max_length=20, choices=Category.choices)
    purchase_date = models.DateField("Alım tarihi")
    put_in_service = models.DateField("Hizmete girme tarihi", null=True, blank=True)
    purchase_cost = models.DecimalField(
        "Alım maliyeti", max_digits=14, decimal_places=2
    )
    salvage_value = models.DecimalField(
        "Hurda değer", max_digits=14, decimal_places=2, default=ZERO
    )
    useful_life_months = models.PositiveIntegerField(
        "Faydalı ömür (ay)",
        help_text="Doğrusal: aylık amortisman = (maliyet - hurda) / ay",
    )
    method = models.CharField(
        "Yöntem", max_length=10, choices=Method.choices, default=Method.LINEAR
    )
    declining_rate = models.DecimalField(
        "Azalan bakiye oranı (%)", max_digits=5, decimal_places=2, null=True, blank=True
    )

    equipment = models.OneToOneField(
        Equipment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fixed_asset", verbose_name="CMMS ekipmanı",
    )

    # Hesap eşleştirmeleri (SCF)
    account_asset = models.ForeignKey(
        Account, on_delete=models.PROTECT,
        related_name="fixed_assets", verbose_name="Aktif hesap (2xxx)",
    )
    account_accumulated_depreciation = models.ForeignKey(
        Account, on_delete=models.PROTECT,
        related_name="accumulated_depreciation_assets",
        verbose_name="Birikmiş amortisman hesabı (28xxx)",
    )
    account_expense = models.ForeignKey(
        Account, on_delete=models.PROTECT,
        related_name="depreciation_expense_assets",
        verbose_name="Amortisman gideri hesabı (681)",
    )

    status = models.CharField(
        "Durum", max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    disposal_date = models.DateField("Elden çıkarma tarihi", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Sabit Kıymet"
        verbose_name_plural = "Sabit Kıymetler"
        ordering = ["asset_number"]

    def __str__(self) -> str:
        return f"{self.asset_number} · {self.name}"

    @property
    def depreciable_base(self) -> Decimal:
        return (self.purchase_cost or ZERO) - (self.salvage_value or ZERO)

    @property
    def monthly_depreciation_linear(self) -> Decimal:
        if self.useful_life_months <= 0:
            return ZERO
        return (self.depreciable_base / Decimal(self.useful_life_months)).quantize(
            Decimal("0.01"))

    @property
    def accumulated_depreciation(self) -> Decimal:
        return self.depreciation_entries.aggregate(
            t=models.Sum("amount"))["t"] or ZERO

    @property
    def net_book_value(self) -> Decimal:
        return self.purchase_cost - self.accumulated_depreciation


class DepreciationEntry(TimeStamped):
    """Aylık amortisman kaydı — sabit kıymet başına."""

    fixed_asset = models.ForeignKey(
        FixedAsset, on_delete=models.CASCADE,
        related_name="depreciation_entries", verbose_name="Sabit kıymet",
    )
    period = models.ForeignKey(
        Period, on_delete=models.PROTECT,
        related_name="depreciations", verbose_name="Dönem",
    )
    amount = models.DecimalField("Amortisman tutarı", max_digits=14, decimal_places=2)
    cumulative_amount = models.DecimalField(
        "Kümülatif", max_digits=14, decimal_places=2, default=ZERO
    )
    journal_entry = models.OneToOneField(
        JournalEntry, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="source_depreciation", verbose_name="Yevmiye fişi",
    )

    class Meta:
        verbose_name = "Amortisman Kaydı"
        verbose_name_plural = "Amortisman Kayıtları"
        unique_together = (("fixed_asset", "period"),)
        ordering = ["fixed_asset", "period"]

    def __str__(self) -> str:
        return f"{self.fixed_asset.asset_number} · {self.period} · {self.amount}"
