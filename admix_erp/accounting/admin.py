from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from common.pdf import render_invoice_pdf

from .models import (
    Account,
    AdvanceAllocation,
    CustomerAdvance,
    DepreciationEntry,
    ExpenseInvoice,
    FiscalYear,
    FixedAsset,
    Invoice,
    InvoiceLine,
    JournalCode,
    JournalEntry,
    JournalLine,
    Payment,
    Period,
    TVADeclaration,
    TVARate,
)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "account_class", "account_type",
                    "is_leaf", "currency", "is_active")
    list_filter = ("account_class", "account_type", "is_leaf", "is_active")
    search_fields = ("code", "name")
    autocomplete_fields = ("parent",)


@admin.register(TVARate)
class TVARateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "rate_pct", "collected_account",
                    "deductible_account", "is_active")
    search_fields = ("code", "name")


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ("year", "start_date", "end_date", "is_closed", "closed_at")
    list_filter = ("is_closed",)


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "fiscal_year", "status", "closed_at")
    list_filter = ("status", "fiscal_year")


@admin.register(JournalCode)
class JournalCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "type", "default_account", "is_active")
    list_filter = ("type", "is_active")
    search_fields = ("code", "name")


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0
    fields = ("account", "debit", "credit", "description", "customer", "supplier")
    autocomplete_fields = ("account", "customer", "supplier")


@admin.register(JournalEntry)
class JournalEntryAdmin(SimpleHistoryAdmin):
    list_display = ("entry_number", "entry_date", "journal_code", "period",
                    "description", "status_c", "total_debit", "total_credit",
                    "balanced_c")
    list_filter = ("status", "journal_code", "period")
    search_fields = ("entry_number", "description", "reference")
    date_hierarchy = "entry_date"
    inlines = [JournalLineInline]

    @admin.display(description="Durum")
    def status_c(self, obj):
        c = {"DRAFT": "#6b7280", "POSTED": "#2e7d32",
             "CANCELLED": "#c62828"}.get(obj.status, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_status_display())

    @admin.display(description="Denge")
    def balanced_c(self, obj):
        ok = obj.is_balanced
        return format_html(
            '<span style="color:{}">{}</span>',
            "#2e7d32" if ok else "#c62828", "✓" if ok else "≠",
        )


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1
    fields = ("sequence", "product", "description", "quantity", "unit_price",
              "tva_rate", "ht_amount", "tva_amount", "ttc_amount")
    readonly_fields = ("ht_amount", "tva_amount", "ttc_amount")
    autocomplete_fields = ("product", "revenue_account")


@admin.register(Invoice)
class InvoiceAdmin(SimpleHistoryAdmin):
    list_display = ("invoice_number", "type", "date", "due_date",
                    "counterparty", "total_ht", "total_tva", "total_ttc",
                    "amount_paid", "status_c")
    list_filter = ("type", "status", "period")
    search_fields = ("invoice_number", "customer__code", "supplier__code",
                     "shipment_reference", "receipt_reference")
    date_hierarchy = "date"
    inlines = [InvoiceLineInline]
    autocomplete_fields = ("customer", "supplier")
    readonly_fields = ("total_ht", "total_tva", "total_ttc", "amount_paid",
                       "journal_entry")
    actions = ["download_pdf"]

    @admin.action(description="Fatura PDF indir (ilk seçili)")
    def download_pdf(self, request, queryset):
        inv = queryset.first()
        if not inv:
            return
        pdf = render_invoice_pdf(inv)
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{inv.invoice_number}.pdf"'
        return resp

    @admin.display(description="Cari")
    def counterparty(self, obj):
        return obj.customer or obj.supplier

    @admin.display(description="Durum")
    def status_c(self, obj):
        c = {"DRAFT": "#6b7280", "POSTED": "#0369a1",
             "PARTIALLY_PAID": "#ed6c02", "PAID": "#2e7d32",
             "CANCELLED": "#c62828"}.get(obj.status, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_status_display())


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_number", "date", "direction", "method",
                    "amount", "counterparty", "bank_account", "reference")
    list_filter = ("direction", "method")
    search_fields = ("payment_number", "reference",
                     "customer__code", "supplier__code")
    filter_horizontal = ("invoices",)
    date_hierarchy = "date"

    @admin.display(description="Cari")
    def counterparty(self, obj):
        return obj.customer or obj.supplier


@admin.register(TVADeclaration)
class TVADeclarationAdmin(admin.ModelAdmin):
    list_display = ("period", "collected_tva", "deductible_tva",
                    "net_tva", "status", "submitted_at", "reference_number")
    list_filter = ("status", "period__year")


class DepreciationEntryInline(admin.TabularInline):
    model = DepreciationEntry
    extra = 0
    fields = ("period", "amount", "cumulative_amount", "journal_entry")
    readonly_fields = ("cumulative_amount", "journal_entry")


@admin.register(FixedAsset)
class FixedAssetAdmin(SimpleHistoryAdmin):
    list_display = ("asset_number", "name", "category", "purchase_cost",
                    "accumulated_depreciation_c", "net_book_value_c", "status")
    list_filter = ("category", "status", "method")
    search_fields = ("asset_number", "name")
    inlines = [DepreciationEntryInline]

    @admin.display(description="Birikmiş")
    def accumulated_depreciation_c(self, obj):
        return obj.accumulated_depreciation

    @admin.display(description="Net defter değeri")
    def net_book_value_c(self, obj):
        return obj.net_book_value


@admin.register(DepreciationEntry)
class DepreciationEntryAdmin(admin.ModelAdmin):
    list_display = ("fixed_asset", "period", "amount",
                    "cumulative_amount", "journal_entry")
    list_filter = ("period",)
    search_fields = ("fixed_asset__asset_number",)


# -- Sprint 5: Müşteri Avansı (§23) -----------------------------------------

class AdvanceAllocationInline(admin.TabularInline):
    model = AdvanceAllocation
    extra = 0
    fields = ("invoice", "amount", "date")
    autocomplete_fields = ("invoice",)


@admin.register(CustomerAdvance)
class CustomerAdvanceAdmin(SimpleHistoryAdmin):
    list_display = (
        "advance_number", "customer", "date", "amount",
        "allocated_col", "remaining_col", "status", "method",
    )
    list_filter = ("status", "method", "date")
    search_fields = ("advance_number", "customer__code", "customer__name", "reference")
    autocomplete_fields = ("customer",)
    date_hierarchy = "date"
    inlines = [AdvanceAllocationInline]

    @admin.display(description="Tahsis")
    def allocated_col(self, obj):
        return obj.allocated_total

    @admin.display(description="Kalan")
    def remaining_col(self, obj):
        rem = obj.remaining_amount
        color = "#16A34A" if rem > 0 else "#6B7280"
        return format_html('<b style="color:{}">{}</b>', color, rem)


@admin.register(AdvanceAllocation)
class AdvanceAllocationAdmin(admin.ModelAdmin):
    list_display = ("advance", "invoice", "amount", "date")
    list_filter = ("date",)
    autocomplete_fields = ("advance", "invoice")
    date_hierarchy = "date"


# -- Sprint 8: Facture de Dépense -------------------------------------------

@admin.register(ExpenseInvoice)
class ExpenseInvoiceAdmin(SimpleHistoryAdmin):
    list_display = (
        "expense_number", "supplier", "category", "invoice_date",
        "amount_ht", "amount_ttc", "status", "performed_by",
    )
    list_filter = ("category", "status", "invoice_date")
    search_fields = (
        "expense_number", "supplier__code", "supplier__name",
        "supplier_invoice_number", "equipment_reference", "description",
    )
    autocomplete_fields = ("supplier", "tva_rate", "performed_by", "approved_by")
    date_hierarchy = "invoice_date"
    readonly_fields = ("amount_tva", "amount_ttc", "approved_at")
    fieldsets = (
        (None, {"fields": (
            ("expense_number", "status"),
            ("supplier", "category"),
            ("invoice_date", "due_date", "period"),
        )}),
        ("Détails", {"fields": (
            "description",
            ("supplier_invoice_number", "equipment_reference"),
        )}),
        ("Montants", {"fields": (
            ("amount_ht", "tva_rate"),
            ("amount_tva", "amount_ttc"),
            "amount_in_words",
        )}),
        ("Justificatif", {"fields": ("proof_document",)}),
        ("Onay", {"fields": (
            ("performed_by",),
            ("approved_by", "approved_at"),
            "payment_reference",
        )}),
        ("Notlar", {"fields": ("notes",)}),
    )

    def save_model(self, request, obj, form, change):
        # Otomatik hesaplama
        obj.recompute()
        if not obj.performed_by_id:
            obj.performed_by = request.user
        if obj.status == ExpenseInvoice.Status.APPROVED and obj.approved_at is None:
            from django.utils import timezone
            obj.approved_at = timezone.now()
            obj.approved_by = obj.approved_by or request.user
        super().save_model(request, obj, form, change)
