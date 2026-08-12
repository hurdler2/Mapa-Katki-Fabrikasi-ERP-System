from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import BusinessLine, RoleBusinessLineScope


@admin.register(BusinessLine)
class BusinessLineAdmin(SimpleHistoryAdmin):
    list_display = ("code", "name", "is_active", "typical_entry")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(RoleBusinessLineScope)
class RoleBusinessLineScopeAdmin(admin.ModelAdmin):
    list_display = ("group", "business_line")
    list_filter = ("business_line",)
    autocomplete_fields = ("group",)
