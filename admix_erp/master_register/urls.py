from django.urls import path

from . import views

app_name = "master_register"

urlpatterns = [
    path("integrated/", views.integrated_list, name="integrated_list"),
    path("integrated/<str:event_id>/", views.integrated_detail,
         name="integrated_detail"),
    path("security/", views.security_list, name="security_list"),
]
