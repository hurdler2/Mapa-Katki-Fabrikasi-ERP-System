from django.contrib import admin

from .models import RuleViolation


@admin.register(RuleViolation)
class RuleViolationAdmin(admin.ModelAdmin):
    list_display = ("rule_no", "rule_title", "target_model", "target_repr",
                    "attempted_action", "blocked", "resolved", "created_at")
    list_filter = ("rule_no", "blocked", "resolved", "attempted_action",
                    "target_model")
    search_fields = ("rule_title", "target_repr", "reason", "target_pk",
                     "user__username")
    readonly_fields = ("rule_no", "rule_title", "user", "target_model",
                        "target_pk", "target_repr", "attempted_action",
                        "reason", "context", "blocked",
                        "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("rule_no", "rule_title", "attempted_action",
                            "blocked", "created_at")}),
        ("Hedef", {"fields": ("user", "target_model", "target_pk",
                                "target_repr")}),
        ("Detay", {"fields": ("reason", "context")}),
        ("Çözüm", {"fields": ("resolved", "resolution_note")}),
    )
