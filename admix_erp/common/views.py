"""Ana sayfa hub view — tüm modüllere yönlendiren merkez ekran."""
from __future__ import annotations

import datetime as dt

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def home(request: HttpRequest) -> HttpResponse:
    """Rol tabanlı hub ekranı. KPI özetleri + modül kartları."""
    # Bu import'lar view scope'unda tutuluyor ki circular import olmasın
    from chemicals.models import ShelfLifeAlert
    from cmms.models import CalibrationSchedule, WorkOrder
    from inventory.models import RawMaterialLot
    from notifications.models import Notification
    from production.models import ProductionBatch
    from qms.models import CAPA, Nonconformance
    from quality.models import CertificateOfAnalysis

    today = dt.date.today()
    since_30 = today - dt.timedelta(days=30)

    kpis = {
        "batches_30d": ProductionBatch.objects.filter(
            created_at__date__gte=since_30).count(),
        "batches_released_30d": ProductionBatch.objects.filter(
            created_at__date__gte=since_30,
            qc_status=ProductionBatch.QCStatus.RELEASED).count(),
        "pending_lots": RawMaterialLot.objects.filter(
            qc_status=RawMaterialLot.QCStatus.PENDING).count(),
        "coa_issued_30d": CertificateOfAnalysis.objects.filter(
            issued_at__date__gte=since_30,
            status=CertificateOfAnalysis.Status.ISSUED).count(),
        "open_ncr": Nonconformance.objects.exclude(
            status=Nonconformance.Status.CLOSED).count(),
        "open_capa": CAPA.objects.exclude(
            status=CAPA.Status.CLOSED).count(),
        "wo_open": WorkOrder.objects.filter(
            status__in=[WorkOrder.Status.OPEN, WorkOrder.Status.ASSIGNED,
                        WorkOrder.Status.IN_PROGRESS]).count(),
        "calibration_overdue": CalibrationSchedule.objects.filter(
            is_active=True, next_due_date__isnull=False,
            next_due_date__lt=today).count(),
        "shelf_alerts_open": ShelfLifeAlert.objects.filter(
            status=ShelfLifeAlert.Status.OPEN).count(),
        "unread_notifications": Notification.objects.filter(
            recipient=request.user, is_read=False).count(),
    }

    # Kullanıcının rolleri
    user_roles = list(request.user.groups.values_list("name", flat=True))
    is_super = request.user.is_superuser

    return render(request, "home.html", {
        "kpis": kpis,
        "user_roles": user_roles,
        "is_super": is_super,
    })
