from django.contrib import admin
from django.utils.html import format_html

from .models import LimsEndpoint, LimsSyncLog, SampleRequest


@admin.register(LimsEndpoint)
class LimsEndpointAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "protocol", "endpoint_url", "is_active")
    list_filter = ("protocol", "is_active")


@admin.register(SampleRequest)
class SampleRequestAdmin(admin.ModelAdmin):
    list_display = ("request_number", "endpoint", "target", "status_c",
                    "priority", "sent_at", "received_at")
    list_filter = ("status", "endpoint", "priority")
    search_fields = ("request_number", "lims_reference")
    filter_horizontal = ("parameters",)
    readonly_fields = ("payload_sent", "payload_received", "sent_at",
                       "received_at", "lims_reference")

    @admin.display(description="Hedef")
    def target(self, obj):
        return obj.batch or obj.lot

    @admin.display(description="Durum")
    def status_c(self, obj):
        c = {"PENDING": "#6b7280", "SENT": "#0369a1",
             "RECEIVED": "#2e7d32", "FAILED": "#c62828"}.get(obj.status, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_status_display())


@admin.register(LimsSyncLog)
class LimsSyncLogAdmin(admin.ModelAdmin):
    list_display = ("executed_at", "endpoint", "direction", "status_c",
                    "records_processed", "executed_by")
    list_filter = ("status", "direction", "endpoint")
    date_hierarchy = "executed_at"
    readonly_fields = ("payload_summary", "error_message")

    @admin.display(description="Durum")
    def status_c(self, obj):
        c = {"SUCCESS": "#2e7d32", "FAILED": "#c62828",
             "PARTIAL": "#ed6c02"}.get(obj.status, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_status_display())
