from django.contrib import admin
from django.http import HttpResponse

from common.pdf import render_shipment_pdf

from .models import SalesOrder, SalesOrderLine, Shipment, ShipmentLine


class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 1
    fields = ("product", "quantity", "unit", "unit_price", "shipped_qty")
    readonly_fields = ("shipped_qty",)
    autocomplete_fields = ("product",)


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "order_date", "delivery_date", "status")
    list_filter = ("status", "customer")
    search_fields = ("order_number", "customer__code", "customer__name")
    date_hierarchy = "order_date"
    inlines = [SalesOrderLineInline]


class ShipmentLineInline(admin.TabularInline):
    model = ShipmentLine
    extra = 0
    fields = ("so_line", "output_container", "quantity")
    autocomplete_fields = ("so_line", "output_container")


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("shipment_number", "customer", "so", "shipped_date", "carrier", "vehicle_plate")
    list_filter = ("customer",)
    search_fields = ("shipment_number", "so__order_number", "vehicle_plate")
    date_hierarchy = "shipped_date"
    inlines = [ShipmentLineInline]
    actions = ["download_pdf"]

    @admin.action(description="İrsaliye PDF indir (ilk seçili)")
    def download_pdf(self, request, queryset):
        sh = queryset.first()
        if not sh:
            return
        pdf = render_shipment_pdf(sh)
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{sh.shipment_number}.pdf"'
        return resp


@admin.register(SalesOrderLine)
class SalesOrderLineAdmin(admin.ModelAdmin):
    list_display = ("so", "product", "quantity", "shipped_qty", "unit_price")
    search_fields = ("so__order_number",)


@admin.register(ShipmentLine)
class ShipmentLineAdmin(admin.ModelAdmin):
    list_display = ("shipment", "output_container", "quantity")
    search_fields = ("shipment__shipment_number",)
