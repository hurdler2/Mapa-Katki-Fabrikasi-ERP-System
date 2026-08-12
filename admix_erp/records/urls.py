from django.urls import path

from . import views

app_name = "records"

urlpatterns = [
    path("cases/", views.case_list, name="case_list"),
    path("cases/<str:case_id>/", views.case_detail, name="case_detail"),
    path("records/<str:record_id>/", views.record_detail, name="record_detail"),
    path("decisions/<str:decision_id>/", views.decision_detail, name="decision_detail"),
]
