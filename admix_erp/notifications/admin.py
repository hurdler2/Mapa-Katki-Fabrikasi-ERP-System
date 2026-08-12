from django.contrib import admin
from django.utils.html import format_html

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "recipient", "title", "level_c",
                    "is_read", "read_at")
    list_filter = ("level", "is_read")
    search_fields = ("title", "message", "recipient__username")
    date_hierarchy = "created_at"

    @admin.display(description="Seviye")
    def level_c(self, obj):
        c = {"INFO": "#0369a1", "SUCCESS": "#2e7d32",
             "WARNING": "#ed6c02", "ERROR": "#c62828",
             "TASK": "#7c3aed"}.get(obj.level, "#000")
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           c, obj.get_level_display())
