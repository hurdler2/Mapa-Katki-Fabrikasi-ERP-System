from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("<int:pk>/read/", views.mark_read_view, name="mark_read"),
]
