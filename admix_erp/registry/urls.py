from django.urls import path

from . import views

app_name = "registry"

urlpatterns = [
    path("", views.registry_list, name="list"),
    path("<int:pk>/", views.registry_detail, name="detail"),
]
