from django.contrib import admin

from .models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 1
    fields = ("raw_material", "quantity", "unit", "unit_price", "received_qty")
    readonly_fields = ("received_qty",)
    autocomplete_fields = ("raw_material",)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "supplier", "order_date", "expected_date", "status")
    list_filter = ("status", "supplier")
    search_fields = ("order_number", "supplier__code", "supplier__name")
    date_hierarchy = "order_date"
    inlines = [PurchaseOrderLineInline]


class GoodsReceiptLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 0
    fields = ("po_line", "raw_material", "lot", "quantity")
    readonly_fields = ("lot",)
    autocomplete_fields = ("raw_material", "po_line")


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "supplier", "po", "received_date", "receiver")
    list_filter = ("supplier",)
    search_fields = ("receipt_number", "po__order_number")
    date_hierarchy = "received_date"
    inlines = [GoodsReceiptLineInline]


@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(admin.ModelAdmin):
    list_display = ("po", "raw_material", "quantity", "received_qty", "unit_price")
    list_filter = ("raw_material",)
    search_fields = ("po__order_number",)
