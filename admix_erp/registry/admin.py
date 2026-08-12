from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import ControlledCode, ControlledCodeRevision


class ControlledCodeRevisionInline(admin.TabularInline):
    model = ControlledCodeRevision
    extra = 0
    fields = ("revision", "revision_date", "issue_state",
              "change_summary", "reviewed_by", "approved_by")


@admin.register(ControlledCode)
class ControlledCodeAdmin(SimpleHistoryAdmin):
    list_display = ("full_code", "short_alias", "title", "type",
                    "level", "function", "status", "revision", "is_active")
    list_filter = ("function", "type", "level", "status", "is_active",
                   "business_lines")
    search_fields = ("full_code", "short_alias", "title", "owner_role")
    filter_horizontal = ("business_lines",)
    inlines = [ControlledCodeRevisionInline]

    fieldsets = (
        (None, {"fields": ("full_code", "short_alias", "title",
                           "type", "level", "function",
                           "business_lines", "is_active")}),
        ("Sahiplik & kaynak", {"fields": (
            "owner_role", "source_procedure", "package_wave",
            "status", "revision",
        )}),
        ("Aktivasyon & kanıt", {"fields": (
            "activation_gate", "objective_evidence_rule",
        )}),
        ("Kullanım", {"fields": (
            "trigger_type", "primary_preparer_role", "review_approval_model",
            "example_record_id_pattern", "archive_path_pattern",
            "retention_authority",
        )}),
        ("Notlar", {"fields": ("notes",)}),
    )


@admin.register(ControlledCodeRevision)
class ControlledCodeRevisionAdmin(admin.ModelAdmin):
    list_display = ("code", "revision", "revision_date",
                    "issue_state", "authority_record")
    list_filter = ("issue_state",)
    search_fields = ("code__full_code", "revision", "authority_record")
    date_hierarchy = "revision_date"
