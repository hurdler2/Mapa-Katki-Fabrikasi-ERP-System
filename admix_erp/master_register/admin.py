from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import IntegratedEventRegister, SecurityEventRegister


@admin.register(IntegratedEventRegister)
class IntegratedEventRegisterAdmin(SimpleHistoryAdmin):
    list_display = ("event_id", "family", "ev_class", "d_level", "status",
                    "hold_flag", "owner", "detection_date", "close_date",
                    "is_snapshot")
    list_filter = ("family", "ev_class", "status", "hold_flag", "is_snapshot")
    search_fields = ("event_id", "site_process", "scope_summary",
                     "related_records", "case__case_id")
    readonly_fields = ("is_snapshot", "snapshot_of",
                       "created_at", "updated_at")


@admin.register(SecurityEventRegister)
class SecurityEventRegisterAdmin(SimpleHistoryAdmin):
    list_display = ("incident_id", "severity", "current_status",
                    "affected_asset", "owner", "detection_datetime",
                    "close_date", "escalation_status", "is_snapshot")
    list_filter = ("severity", "current_status", "escalation_status",
                    "is_personal_data", "is_snapshot")
    search_fields = ("incident_id", "affected_asset", "scope_impact_summary")
    readonly_fields = ("is_snapshot", "snapshot_of",
                       "created_at", "updated_at")
