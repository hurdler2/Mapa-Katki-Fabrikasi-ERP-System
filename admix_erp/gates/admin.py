from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Gate, GateSection


class GateSectionInline(admin.TabularInline):
    model = GateSection
    extra = 0
    filter_horizontal = ("evidence",)


@admin.register(Gate)
class GateAdmin(SimpleHistoryAdmin):
    list_display = ("gate_id", "case", "status", "owner",
                    "opened_at", "closed_at")
    list_filter = ("status", "business_line")
    search_fields = ("gate_id", "case__case_id", "scope")
    autocomplete_fields = ("case", "owner", "closed_by")
    inlines = [GateSectionInline]


@admin.register(GateSection)
class GateSectionAdmin(admin.ModelAdmin):
    list_display = ("gate", "section", "completion_status",
                    "reviewer", "reviewed_at")
    list_filter = ("section", "completion_status")
    search_fields = ("gate__gate_id",)
    filter_horizontal = ("evidence",)
