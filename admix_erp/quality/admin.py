from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .models import CertificateOfAnalysis, QCParameter, QCSpec, QCTestResult
from .services import (
    coa_payload,
    generate_coa,
    quarantine_lot,
    reject_batch,
    reject_lot,
    release_batch,
    release_lot,
)


@admin.register(QCParameter)
class QCParameterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "unit", "method", "is_active")
    list_filter = ("method", "is_active")
    search_fields = ("code", "name")


@admin.register(QCSpec)
class QCSpecAdmin(admin.ModelAdmin):
    list_display = ("parameter", "product", "raw_material", "min_value", "max_value", "target_value", "is_mandatory")
    list_filter = ("parameter", "is_mandatory")
    autocomplete_fields = ("parameter", "product", "raw_material")


@admin.register(QCTestResult)
class QCTestResultAdmin(admin.ModelAdmin):
    list_display = ("parameter", "value", "verdict_colored", "target_display", "tested_at", "tester")
    list_filter = ("verdict", "parameter")
    search_fields = ("lot__lot_number", "batch__batch_number", "tester")
    autocomplete_fields = ("parameter", "lot", "batch")
    date_hierarchy = "tested_at"

    @admin.display(description="Sonuç")
    def verdict_colored(self, obj: QCTestResult) -> str:
        colors = {
            QCTestResult.Verdict.PASS: "#2e7d32",
            QCTestResult.Verdict.FAIL: "#c62828",
            QCTestResult.Verdict.NA: "#a0a0a0",
        }
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            colors.get(obj.verdict, "#000"), obj.get_verdict_display(),
        )

    @admin.display(description="Hedef")
    def target_display(self, obj: QCTestResult) -> str:
        return obj.lot.lot_number if obj.lot else (obj.batch.batch_number if obj.batch else "-")


@admin.register(CertificateOfAnalysis)
class CertificateOfAnalysisAdmin(admin.ModelAdmin):
    list_display = ("coa_number", "batch", "status", "issued_at", "issued_by")
    list_filter = ("status",)
    search_fields = ("coa_number", "batch__batch_number")
    actions = ["issue_coa", "print_payload"]

    @admin.action(description="COA yayımla (ISSUED)")
    def issue_coa(self, request, queryset):
        for coa in queryset:
            try:
                generate_coa(coa.batch, coa_number=coa.coa_number, issued_by=str(request.user))
                self.message_user(request, f"{coa.coa_number} yayımlandı.", messages.SUCCESS)
            except ValidationError as e:
                self.message_user(request, f"{coa.coa_number}: {e.messages[0]}", messages.ERROR)

    @admin.action(description="COA içeriğini göster")
    def print_payload(self, request, queryset):
        for coa in queryset:
            data = coa_payload(coa)
            lines = [
                f"COA {data['coa_number']} · Parti {data['batch_number']} · "
                f"{data['product']} v{data['recipe_version']}"
            ]
            for r in data["results"]:
                lines.append(
                    f"  {r['parameter']}={r['value']} {r['unit']} → {r['verdict']} ({r['method']})"
                )
            self.message_user(request, "\n".join(lines), messages.INFO)


# ProductionBatch admin'e QC action ve inline eklemesi
from django.contrib.admin.sites import site as admin_site

from production.models import ProductionBatch
from inventory.models import RawMaterialLot


class QCTestBatchInline(admin.TabularInline):
    model = QCTestResult
    fk_name = "batch"
    extra = 0
    fields = ("parameter", "value", "verdict", "tester", "tested_at")
    readonly_fields = ("tested_at",)
    autocomplete_fields = ("parameter",)


class QCTestLotInline(admin.TabularInline):
    model = QCTestResult
    fk_name = "lot"
    extra = 0
    fields = ("parameter", "value", "verdict", "tester", "tested_at")
    readonly_fields = ("tested_at",)
    autocomplete_fields = ("parameter",)


def _augment_batch_admin() -> None:
    """ProductionBatchAdmin'e QC test inline'ı ve serbest bırak/reddet aksiyonları ekle."""
    from production.admin import ProductionBatchAdmin

    if QCTestBatchInline not in ProductionBatchAdmin.inlines:
        ProductionBatchAdmin.inlines = list(ProductionBatchAdmin.inlines) + [QCTestBatchInline]

    @admin.action(description="QC RELEASE (parti serbest bırak)")
    def action_release(modeladmin, request, queryset):
        for b in queryset:
            try:
                release_batch(b)
                modeladmin.message_user(request, f"{b.batch_number} RELEASED.", messages.SUCCESS)
            except ValidationError as e:
                modeladmin.message_user(request, f"{b.batch_number}: {e.messages[0]}", messages.ERROR)

    @admin.action(description="QC REJECT (parti reddet)")
    def action_reject(modeladmin, request, queryset):
        for b in queryset:
            reject_batch(b, reason="Admin aksiyonu ile reddedildi.")
            modeladmin.message_user(request, f"{b.batch_number} REJECTED.", messages.WARNING)

    @admin.action(description="COA üret + yayımla")
    def action_coa(modeladmin, request, queryset):
        for b in queryset:
            try:
                coa = generate_coa(b, issued_by=str(request.user))
                modeladmin.message_user(request, f"{b.batch_number} → {coa.coa_number}", messages.SUCCESS)
            except ValidationError as e:
                modeladmin.message_user(request, f"{b.batch_number}: {e.messages[0]}", messages.ERROR)

    existing_actions = list(getattr(ProductionBatchAdmin, "actions", []) or [])
    for a in (action_release, action_reject, action_coa):
        if a not in existing_actions:
            existing_actions.append(a)
    ProductionBatchAdmin.actions = existing_actions

    # Yeniden kaydet
    try:
        admin_site.unregister(ProductionBatch)
    except admin.sites.NotRegistered:
        pass
    admin_site.register(ProductionBatch, ProductionBatchAdmin)


def _augment_lot_admin() -> None:
    from inventory.admin import RawMaterialLotAdmin

    if QCTestLotInline not in getattr(RawMaterialLotAdmin, "inlines", []):
        RawMaterialLotAdmin.inlines = list(getattr(RawMaterialLotAdmin, "inlines", [])) + [QCTestLotInline]

    @admin.action(description="Lot serbest bırak (RELEASED)")
    def action_release_lot(modeladmin, request, queryset):
        for lot in queryset:
            try:
                release_lot(lot)
                modeladmin.message_user(request, f"{lot.lot_number} RELEASED.", messages.SUCCESS)
            except ValidationError as e:
                modeladmin.message_user(request, f"{lot.lot_number}: {e.messages[0]}", messages.ERROR)

    @admin.action(description="Lot karantinaya al")
    def action_quarantine_lot(modeladmin, request, queryset):
        for lot in queryset:
            quarantine_lot(lot)
            modeladmin.message_user(request, f"{lot.lot_number} QUARANTINE.", messages.WARNING)

    @admin.action(description="Lot reddet")
    def action_reject_lot(modeladmin, request, queryset):
        for lot in queryset:
            reject_lot(lot)
            modeladmin.message_user(request, f"{lot.lot_number} REJECTED.", messages.ERROR)

    existing_actions = list(getattr(RawMaterialLotAdmin, "actions", []) or [])
    for a in (action_release_lot, action_quarantine_lot, action_reject_lot):
        if a not in existing_actions:
            existing_actions.append(a)
    RawMaterialLotAdmin.actions = existing_actions

    try:
        admin_site.unregister(RawMaterialLot)
    except admin.sites.NotRegistered:
        pass
    admin_site.register(RawMaterialLot, RawMaterialLotAdmin)


_augment_batch_admin()
_augment_lot_admin()
