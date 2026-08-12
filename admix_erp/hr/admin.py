from django.contrib import admin

from .models import (
    LeaveRequest,
    Shift,
    ShiftAssignment,
    TrainingCourse,
    TrainingRecord,
    TrainingSession,
)


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "start_time", "end_time", "is_night", "is_active")
    list_filter = ("is_night", "is_active")


@admin.register(ShiftAssignment)
class ShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ("date", "shift", "user", "role", "status")
    list_filter = ("status", "shift")
    search_fields = ("user__username", "role")
    date_hierarchy = "date"


@admin.register(TrainingCourse)
class TrainingCourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "duration_hours",
                    "validity_days", "grants_competency", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("code", "name")


class TrainingRecordInline(admin.TabularInline):
    model = TrainingRecord
    extra = 0
    fields = ("user", "result", "score", "certificate_number", "valid_until")


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ("session_number", "course", "date", "location",
                    "trainer", "status")
    list_filter = ("status", "course__category")
    search_fields = ("session_number", "course__code")
    date_hierarchy = "date"
    inlines = [TrainingRecordInline]


@admin.register(TrainingRecord)
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = ("session", "user", "result", "score",
                    "certificate_number", "valid_until")
    list_filter = ("result",)
    search_fields = ("user__username", "certificate_number")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("request_number", "user", "type", "start_date",
                    "end_date", "days", "status", "approved_by")
    list_filter = ("status", "type")
    search_fields = ("request_number", "user__username")
    date_hierarchy = "start_date"
