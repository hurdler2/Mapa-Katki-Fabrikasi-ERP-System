from django.urls import path

from . import views

app_name = "gates"

urlpatterns = [
    path("", views.gate_list, name="list"),
    path("<str:gate_id>/", views.gate_detail, name="detail"),
]
