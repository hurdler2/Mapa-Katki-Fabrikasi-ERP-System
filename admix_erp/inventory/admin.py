from django.contrib import admin
from django.utils.html import format_html

from .models import RawMaterialLot, StockAdjustment, StockMovement


@admin.register(RawMaterialLot)
class RawMaterialLotAdmin(admin.ModelAdmin):
    list_display = (
        "lot_number", "raw_material", "supplier", "qc_status_colored",
        "received_qty", "remaining_qty", "unit_cost", "expiry_date", "container",
    )
    list_filter = ("qc_status", "raw_material", "supplier")
    search_fields = ("lot_number", "coa_reference")
    date_hierarchy = "received_date"

    @admin.display(description="Kalite")
    def qc_status_colored(self, obj: RawMaterialLot) -> str:
        colors = {
            RawMaterialLot.QCStatus.PENDING: "#a0a0a0",
            RawMaterialLot.QCStatus.RELEASED: "#2e7d32",
            RawMaterialLot.QCStatus.QUARANTINE: "#ed6c02",
            RawMaterialLot.QCStatus.REJECTED: "#c62828",
        }
        color = colors.get(obj.qc_status, "#000")
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            color, obj.get_qc_status_display(),
        )


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "lot", "movement_type", "quantity", "reference")
    list_filter = ("movement_type",)
    search_fields = ("lot__lot_number", "reference")
    date_hierarchy = "timestamp"


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        "adjustment_number", "lot", "adjustment_type",
        "qty_before", "qty_after", "delta_c",
        "performed_by", "performed_at",
    )
    list_filter = ("adjustment_type", "performed_at")
    search_fields = ("adjustment_number", "lot__lot_number", "reason", "document_ref")
    date_hierarchy = "performed_at"
    autocomplete_fields = ("lot", "performed_by")
    readonly_fields = ("delta", "movement")

    @admin.display(description="Delta")
    def delta_c(self, obj):
        color = "#DC2626" if obj.delta < 0 else "#16A34A"
        return format_html('<b style="color:{}">{}</b>', color, obj.delta)
