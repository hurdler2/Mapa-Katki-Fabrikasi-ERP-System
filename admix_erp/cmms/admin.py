from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    CalibrationRecord,
    CalibrationSchedule,
    Equipment,
    EquipmentSparePart,
    MaintenancePlan,
    SparePart,
    SparePartConsumption,
    WorkOrder,
)


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "current_stock", "min_stock", "unit_cost",
                    "storage_location", "below_min_c", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "manufacturer_part_no")

    @admin.display(description="Min altı?")
    def below_min_c(self, obj):
        color = "#c62828" if obj.below_min else "#2e7d32"
        text = "EVET" if obj.below_min else "hayır"
        return format_html('<span style="color:{};font-weight:600">{}</span>', color, text)


class EquipmentSparePartInline(admin.TabularInline):
    model = EquipmentSparePart
    extra = 0
    fields = ("spare_part", "quantity", "position")
    autocomplete_fields = ("spare_part",)


@admin.register(Equipment)
class EquipmentAdmin(SimpleHistoryAdmin):
    list_display = ("equipment_number", "name", "category", "criticality_c",
                    "status_c", "location", "is_measuring_device")
    list_filter = ("category", "criticality", "status", "is_measuring_device")
    search_fields = ("equipment_number", "name", "serial_no", "model", "manufacturer")
    autocomplete_fields = ("parent", "container")
    inlines = [EquipmentSparePartInline]
    fieldsets = (
        (None, {"fields": ("equipment_number", "name", "category", "criticality",
                            "status", "is_measuring_device")}),
        ("Konum & hiyerarşi", {"fields": ("parent", "container", "location",
                                            "responsible_department")}),
        ("Üretici & seri", {"fields": ("manufacturer", "model", "serial_no",
                                        "install_date", "commissioning_date", "warranty_end")}),
        ("Doküman", {"fields": ("manual_reference",)}),
    )

    @admin.display(description="Kritiklik")
    def criticality_c(self, obj):
        c = {"A": "#c62828", "B": "#ed6c02", "C": "#6b7280"}.get(obj.criticality, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_criticality_display())

    @admin.display(description="Durum")
    def status_c(self, obj):
        c = {"OPERATIONAL": "#2e7d32", "UNDER_MAINTENANCE": "#ed6c02",
             "OUT_OF_SERVICE": "#c62828", "DECOMMISSIONED": "#374151",
             "STANDBY": "#0369a1"}.get(obj.status, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_status_display())


@admin.register(MaintenancePlan)
class MaintenancePlanAdmin(admin.ModelAdmin):
    list_display = ("plan_code", "name", "equipment", "frequency",
                    "days_between_wo", "last_generated_on", "next_due_date_c", "is_active")
    list_filter = ("frequency", "is_active", "equipment__category")
    search_fields = ("plan_code", "name", "equipment__equipment_number")

    @admin.display(description="Sonraki vade")
    def next_due_date_c(self, obj):
        return obj.next_due_date


class SparePartConsumptionInline(admin.TabularInline):
    model = SparePartConsumption
    extra = 0
    fields = ("spare_part", "quantity", "unit_cost", "consumed_at")
    readonly_fields = ("consumed_at",)
    autocomplete_fields = ("spare_part",)


@admin.register(WorkOrder)
class WorkOrderAdmin(SimpleHistoryAdmin):
    list_display = ("work_order_number", "type", "priority", "status_c",
                    "equipment", "assigned_to", "scheduled_start",
                    "actual_end", "total_cost")
    list_filter = ("status", "type", "priority")
    search_fields = ("work_order_number", "equipment__equipment_number", "title")
    date_hierarchy = "created_at"
    inlines = [SparePartConsumptionInline]
    autocomplete_fields = ("equipment", "plan", "ncr")

    @admin.display(description="Durum")
    def status_c(self, obj):
        c = {"OPEN": "#6b7280", "ASSIGNED": "#0369a1", "IN_PROGRESS": "#ed6c02",
             "ON_HOLD": "#a16207", "COMPLETED": "#2e7d32",
             "CANCELLED": "#991b1b"}.get(obj.status, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_status_display())


@admin.register(CalibrationSchedule)
class CalibrationScheduleAdmin(admin.ModelAdmin):
    list_display = ("equipment", "parameter", "interval_days",
                    "last_calibrated_on", "next_due_date", "external_lab_required", "is_active")
    list_filter = ("is_active", "external_lab_required")
    search_fields = ("equipment__equipment_number", "parameter")


@admin.register(CalibrationRecord)
class CalibrationRecordAdmin(SimpleHistoryAdmin):
    list_display = ("schedule", "performed_at", "performed_by",
                    "result_c", "is_external", "certificate_number")
    list_filter = ("result", "is_external")
    search_fields = ("certificate_number", "schedule__equipment__equipment_number")
    date_hierarchy = "performed_at"

    @admin.display(description="Sonuç")
    def result_c(self, obj):
        c = {"PASS": "#2e7d32", "FAIL": "#c62828",
             "CONDITIONAL": "#ed6c02", "SUSPECT": "#a16207"}.get(obj.result, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_result_display())
