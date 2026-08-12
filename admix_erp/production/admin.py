from django.contrib import admin, messages
from django.utils.html import format_html

from .models import (
    MaterialConsumption,
    OutputContainer,
    ProductionBatch,
    ProductionOrder,
)
from .services import backward_trace


class MaterialConsumptionInline(admin.TabularInline):
    model = MaterialConsumption
    extra = 0
    fields = (
        "sequence", "raw_material", "lot", "target_weight",
        "actual_weight", "deviation_colored", "source", "dosed_at",
    )
    readonly_fields = ("deviation_colored",)
    ordering = ("sequence",)

    @admin.display(description="Sapma %")
    def deviation_colored(self, obj: MaterialConsumption) -> str:
        dev = obj.deviation_pct
        if dev is None:
            return "-"
        try:
            tol = (
                obj.batch.recipe.lines
                .filter(raw_material=obj.raw_material)
                .values_list("tolerance_pct", flat=True)
                .first()
            )
        except Exception:
            tol = None
        color = "#2e7d32"
        if tol is not None and abs(dev) > tol:
            color = "#c62828"
        return format_html('<span style="color:{};font-weight:600">{}%</span>', color, dev)


class OutputContainerInline(admin.TabularInline):
    model = OutputContainer
    extra = 0
    fields = ("container", "quantity", "filled_at", "shipment_reference")


@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number", "product", "recipe", "target_qty",
        "reactor", "scheduled_date", "status",
    )
    list_filter = ("status", "product")
    search_fields = ("order_number", "product__code")
    date_hierarchy = "scheduled_date"


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = (
        "batch_number", "product_code", "recipe", "reactor",
        "target_qty", "actual_qty", "status", "qc_status", "operator",
    )
    list_filter = ("status", "qc_status", "recipe__product")
    search_fields = ("batch_number", "operator")
    date_hierarchy = "created_at"
    inlines = [MaterialConsumptionInline, OutputContainerInline]
    actions = ["run_backward_trace"]

    @admin.display(description="Ürün")
    def product_code(self, obj: ProductionBatch) -> str:
        return obj.recipe.product.code

    @admin.action(description="İzlenebilirlik (backward trace) çalıştır")
    def run_backward_trace(self, request, queryset):
        for batch in queryset:
            trace = backward_trace(batch)
            lines = [
                f"  {c['raw_material']} · lot={c['lot_number']} · "
                f"tedarikçi={c['supplier']} · gerçek={c['actual_weight']} "
                f"sapma={c['deviation_pct']}"
                for c in trace["consumptions"]
            ]
            body = "\n".join(lines) if lines else "  (tüketim yok)"
            self.message_user(
                request,
                f"Parti {trace['batch_number']} ({trace['product']} v{trace['recipe_version']}):\n{body}",
                level=messages.INFO,
            )


@admin.register(MaterialConsumption)
class MaterialConsumptionAdmin(admin.ModelAdmin):
    list_display = (
        "batch", "sequence", "raw_material", "lot",
        "target_weight", "actual_weight", "source", "dosed_at",
    )
    list_filter = ("source", "raw_material")
    search_fields = ("batch__batch_number", "lot__lot_number")


@admin.register(OutputContainer)
class OutputContainerAdmin(admin.ModelAdmin):
    list_display = ("batch", "container", "quantity", "filled_at", "shipment_reference")
    search_fields = ("batch__batch_number", "container__code", "shipment_reference")
