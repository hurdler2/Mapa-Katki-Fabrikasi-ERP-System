from django.contrib import admin
from django.utils.html import format_html

from .models import PLCEndpoint, RecipeDownload, WeighmentEvent


@admin.register(PLCEndpoint)
class PLCEndpointAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "protocol", "host", "port", "is_active")
    list_filter = ("protocol", "is_active")
    search_fields = ("code", "name", "host")


@admin.register(RecipeDownload)
class RecipeDownloadAdmin(admin.ModelAdmin):
    list_display = ("created_at", "production_order", "endpoint", "batch", "status", "sent_at")
    list_filter = ("status", "endpoint")
    search_fields = ("production_order__order_number", "batch__batch_number")
    date_hierarchy = "created_at"
    readonly_fields = ("payload", "response", "sent_at")


@admin.register(WeighmentEvent)
class WeighmentEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "tag", "weight", "status_colored", "consumption", "endpoint")
    list_filter = ("status", "endpoint")
    search_fields = ("tag",)
    date_hierarchy = "created_at"
    readonly_fields = ("raw_payload",)

    @admin.display(description="Durum")
    def status_colored(self, obj: WeighmentEvent) -> str:
        colors = {
            WeighmentEvent.Status.RECEIVED: "#6b7280",
            WeighmentEvent.Status.MATCHED: "#2e7d32",
            WeighmentEvent.Status.UNMATCHED: "#ed6c02",
            WeighmentEvent.Status.FAILED: "#c62828",
        }
        color = colors.get(obj.status, "#000")
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            color, obj.get_status_display(),
        )
