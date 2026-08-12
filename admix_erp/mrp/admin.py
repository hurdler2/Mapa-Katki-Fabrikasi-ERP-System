from django.contrib import admin
from django.utils.html import format_html

from .models import DemandForecast, MaterialRequirement, MRPRun, PurchaseRequisition


@admin.register(DemandForecast)
class DemandForecastAdmin(admin.ModelAdmin):
    list_display = ("product", "period_start", "period_end", "quantity", "confidence")
    list_filter = ("product",)
    date_hierarchy = "period_start"


class MaterialRequirementInline(admin.TabularInline):
    model = MaterialRequirement
    extra = 0
    fields = ("raw_material", "gross_requirement", "on_hand", "on_order",
              "net_requirement", "suggested_order_qty", "status")
    readonly_fields = fields
    can_delete = False


@admin.register(MRPRun)
class MRPRunAdmin(admin.ModelAdmin):
    list_display = ("run_number", "horizon_date", "executed_at", "executed_by")
    date_hierarchy = "executed_at"
    inlines = [MaterialRequirementInline]


@admin.register(MaterialRequirement)
class MaterialRequirementAdmin(admin.ModelAdmin):
    list_display = ("run", "raw_material", "gross_requirement", "on_hand",
                    "on_order", "net_requirement", "status_c")
    list_filter = ("status", "run")
    search_fields = ("raw_material__code",)

    @admin.display(description="Durum")
    def status_c(self, obj):
        c = {"OK": "#2e7d32", "REORDER": "#ed6c02",
             "SHORTAGE": "#c62828"}.get(obj.status, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_status_display())


@admin.register(PurchaseRequisition)
class PurchaseRequisitionAdmin(admin.ModelAdmin):
    list_display = ("requisition_number", "raw_material", "quantity",
                    "needed_by", "status", "requested_by", "approved_at")
    list_filter = ("status",)
    search_fields = ("requisition_number", "raw_material__code")
    date_hierarchy = "created_at"
