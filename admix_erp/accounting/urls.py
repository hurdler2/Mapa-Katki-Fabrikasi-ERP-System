from django.urls import path

from . import views

app_name = "accounting"

urlpatterns = [
    path("balance/", views.trial_balance_view, name="trial_balance"),
    path("ledger/<int:account_id>/", views.ledger_view, name="ledger"),
]
