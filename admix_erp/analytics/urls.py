from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("bi/", views.bi_dashboard, name="bi_dashboard"),
    path("iso-audit/", views.iso_audit_view, name="iso_audit"),
    path("iso-audit/pdf/", views.iso_audit_pdf, name="iso_audit_pdf"),
    path("iso-audit/json/", views.iso_audit_json, name="iso_audit_json"),
    path("iso-audit/zip/", views.iso_audit_zip, name="iso_audit_zip"),
]
