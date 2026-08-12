from django.contrib import admin

from .models import Competency, Department, ESignature, UserCompetency, UserProfile


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "parent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "employee_no", "department", "title", "hire_date")
    list_filter = ("department",)
    search_fields = ("user__username", "employee_no", "title")


@admin.register(Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "valid_days")
    search_fields = ("code", "name")


@admin.register(UserCompetency)
class UserCompetencyAdmin(admin.ModelAdmin):
    list_display = ("user", "competency", "obtained_on", "expires_on", "evidence")
    list_filter = ("competency",)
    search_fields = ("user__username", "evidence")


@admin.register(ESignature)
class ESignatureAdmin(admin.ModelAdmin):
    list_display = ("signed_at", "user", "meaning", "content_type", "object_id", "reason")
    list_filter = ("meaning", "content_type")
    search_fields = ("user__username", "reason")
    readonly_fields = ("user", "meaning", "reason", "content_type", "object_id",
                       "signed_at", "ip_address")
    date_hierarchy = "signed_at"

    def has_add_permission(self, request):
        return False  # E-imza yalnız servis üzerinden oluşur

    def has_delete_permission(self, request, obj=None):
        return False  # İmzalar silinmez (audit)
