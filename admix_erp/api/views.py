"""DRF ViewSet'ler + izlenebilirlik action endpoint'leri."""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from formulation.models import Recipe
from inventory.models import RawMaterialLot, StockMovement
from masterdata.models import Container, Customer, Product, RawMaterial, Supplier
from production.models import (
    MaterialConsumption,
    OutputContainer,
    ProductionBatch,
    ProductionOrder,
)
from production.services import backward_trace, forward_trace
from purchasing.models import GoodsReceipt, PurchaseOrder
from quality.models import CertificateOfAnalysis, QCTestResult
from sales.models import SalesOrder, Shipment

from . import serializers as s


class ReadWriteMixin:
    """Standart CRUD + search + filter."""
    filterset_fields = "__all__"


class RawMaterialViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = RawMaterial.objects.all()
    serializer_class = s.RawMaterialSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["material_type", "is_active", "unit"]


class ProductViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = s.ProductSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["is_active"]


class CustomerViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = s.CustomerSerializer
    search_fields = ["code", "name", "tax_no"]
    filterset_fields = ["is_active"]


class SupplierViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = s.SupplierSerializer
    search_fields = ["code", "name", "tax_no"]
    filterset_fields = ["is_active"]


class ContainerViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = Container.objects.all()
    serializer_class = s.ContainerSerializer
    filterset_fields = ["container_type", "is_active"]


class RecipeViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = s.RecipeSerializer
    filterset_fields = ["product", "is_active"]


class RawMaterialLotViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = RawMaterialLot.objects.all()
    serializer_class = s.RawMaterialLotSerializer
    search_fields = ["lot_number", "coa_reference"]
    filterset_fields = ["raw_material", "qc_status", "supplier"]

    @action(detail=True, methods=["get"], url_path="forward-trace")
    def forward_trace(self, request, pk=None):
        lot = self.get_object()
        return Response(forward_trace(lot))


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = s.StockMovementSerializer
    filterset_fields = ["lot", "movement_type"]


class ProductionOrderViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = ProductionOrder.objects.all()
    serializer_class = s.ProductionOrderSerializer
    search_fields = ["order_number"]
    filterset_fields = ["product", "status", "reactor"]


class ProductionBatchViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = ProductionBatch.objects.all()
    serializer_class = s.ProductionBatchSerializer
    search_fields = ["batch_number"]
    filterset_fields = ["status", "qc_status", "reactor", "recipe"]

    @action(detail=True, methods=["get"], url_path="backward-trace")
    def backward_trace(self, request, pk=None):
        batch = self.get_object()
        return Response(backward_trace(batch))


class MaterialConsumptionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MaterialConsumption.objects.all()
    serializer_class = s.MaterialConsumptionSerializer
    filterset_fields = ["batch", "raw_material", "source"]


class OutputContainerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OutputContainer.objects.all()
    serializer_class = s.OutputContainerSerializer
    filterset_fields = ["batch", "container"]


class QCTestResultViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = QCTestResult.objects.all()
    serializer_class = s.QCTestResultSerializer
    filterset_fields = ["parameter", "lot", "batch", "verdict"]


class COAViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = CertificateOfAnalysis.objects.all()
    serializer_class = s.CertificateOfAnalysisSerializer
    filterset_fields = ["status", "batch"]


class PurchaseOrderViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = s.PurchaseOrderSerializer
    search_fields = ["order_number"]
    filterset_fields = ["supplier", "status"]


class GoodsReceiptViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = GoodsReceipt.objects.all()
    serializer_class = s.GoodsReceiptSerializer
    search_fields = ["receipt_number"]
    filterset_fields = ["supplier", "po"]


class SalesOrderViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = SalesOrder.objects.all()
    serializer_class = s.SalesOrderSerializer
    search_fields = ["order_number"]
    filterset_fields = ["customer", "status"]


class ShipmentViewSet(ReadWriteMixin, viewsets.ModelViewSet):
    queryset = Shipment.objects.all()
    serializer_class = s.ShipmentSerializer
    search_fields = ["shipment_number", "vehicle_plate"]
    filterset_fields = ["customer", "so"]
