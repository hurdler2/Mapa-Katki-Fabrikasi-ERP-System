from django.contrib import admin

from .models import ApprovalRequest


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "title", "required_role",
                    "status", "requested_by", "decided_by", "decided_at")
    list_filter = ("status", "kind", "required_role")
    search_fields = ("title", "description")
    readonly_fields = ("content_type", "object_id", "requested_by",
                       "decided_by", "decided_at")
