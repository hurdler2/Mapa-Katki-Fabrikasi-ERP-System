from django.urls import path

from . import views

app_name = "reporting"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("batch/<int:batch_id>/", views.batch_report, name="batch_report"),
]
