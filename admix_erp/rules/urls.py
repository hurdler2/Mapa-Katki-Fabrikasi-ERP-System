from django.urls import path

from . import views

app_name = "rules"

urlpatterns = [
    path("", views.violation_list, name="violation_list"),
    path("catalog/", views.rules_catalog, name="catalog"),
    path("<int:pk>/resolve/", views.violation_resolve, name="resolve"),
]
