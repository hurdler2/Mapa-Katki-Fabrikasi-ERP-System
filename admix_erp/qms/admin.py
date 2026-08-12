from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from .models import CAPA, CAPAAction, CustomerComplaint, Deviation, Nonconformance


SEVERITY_COLORS = {
    "LOW": "#6b7280", "MEDIUM": "#0369a1",
    "HIGH": "#ed6c02", "CRITICAL": "#c62828",
}


def _severity(obj):
    return format_html(
        '<span style="color:{};font-weight:600">{}</span>',
        SEVERITY_COLORS.get(obj.severity, "#000"), obj.get_severity_display(),
    )
_severity.short_description = "Ağırlık"


@admin.register(Nonconformance)
class NonconformanceAdmin(SimpleHistoryAdmin):
    list_display = ("ncr_number", "detected_at", "source", "severity_c", "status",
                    "disposition", "detected_by", "closed_at")
    list_filter = ("status", "severity", "source", "disposition")
    search_fields = ("ncr_number", "title", "description")
    date_hierarchy = "detected_at"

    def severity_c(self, obj): return _severity(obj)
    severity_c.short_description = "Ağırlık"


@admin.register(Deviation)
class DeviationAdmin(SimpleHistoryAdmin):
    list_display = ("deviation_number", "detected_at", "severity_c", "status",
                    "detected_by", "closed_at")
    list_filter = ("status", "severity")
    search_fields = ("deviation_number", "title")
    date_hierarchy = "detected_at"

    def severity_c(self, obj): return _severity(obj)
    severity_c.short_description = "Ağırlık"


class CAPAActionInline(admin.TabularInline):
    model = CAPAAction
    extra = 0
    fields = ("sequence", "description", "assignee", "due_date", "status",
              "completed_at", "evidence")


@admin.register(CAPA)
class CAPAAdmin(SimpleHistoryAdmin):
    list_display = ("capa_number", "type", "title", "severity_c", "status",
                    "owner", "target_date", "closed_at")
    list_filter = ("status", "type", "severity", "root_cause_method")
    search_fields = ("capa_number", "title", "description")
    date_hierarchy = "opened_at"
    filter_horizontal = ("ncrs", "deviations")
    inlines = [CAPAActionInline]

    def severity_c(self, obj): return _severity(obj)
    severity_c.short_description = "Ağırlık"


@admin.register(CustomerComplaint)
class CustomerComplaintAdmin(SimpleHistoryAdmin):
    list_display = ("complaint_number", "customer", "received_at", "severity_c",
                    "status", "customer_satisfied")
    list_filter = ("status", "severity", "customer_satisfied")
    search_fields = ("complaint_number", "customer__code", "customer__name",
                     "reference_batch", "reference_shipment")
    date_hierarchy = "received_at"

    def severity_c(self, obj): return _severity(obj)
    severity_c.short_description = "Ağırlık"
