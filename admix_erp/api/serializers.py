"""DRF serializer'ları — kritik modeller için."""
from __future__ import annotations

from rest_framework import serializers

from formulation.models import Recipe, RecipeLine
from inventory.models import RawMaterialLot, StockMovement
from masterdata.models import Container, Customer, Product, RawMaterial, Supplier
from production.models import (
    MaterialConsumption,
    OutputContainer,
    ProductionBatch,
    ProductionOrder,
)
from purchasing.models import GoodsReceipt, PurchaseOrder
from quality.models import CertificateOfAnalysis, QCTestResult
from sales.models import SalesOrder, Shipment


# --- Master data -----------------------------------------------------------

class RawMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawMaterial
        fields = ["id", "code", "name", "material_type", "unit",
                  "density", "shelf_life_days", "is_active"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "code", "name", "unit", "description", "is_active"]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "code", "name", "contact", "tax_no", "is_active"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "code", "name", "contact", "tax_no", "is_active"]


class ContainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Container
        fields = ["id", "code", "name", "container_type",
                  "capacity", "unit", "is_active"]


# --- Formulation -----------------------------------------------------------

class RecipeLineSerializer(serializers.ModelSerializer):
    raw_material_code = serializers.CharField(
        source="raw_material.code", read_only=True)

    class Meta:
        model = RecipeLine
        fields = ["id", "raw_material", "raw_material_code",
                  "quantity", "sequence", "tolerance_pct"]


class RecipeSerializer(serializers.ModelSerializer):
    lines = RecipeLineSerializer(many=True, read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)

    class Meta:
        model = Recipe
        fields = ["id", "product", "product_code", "version",
                  "base_batch_size", "unit", "is_active",
                  "effective_date", "notes", "lines"]


# --- Inventory -------------------------------------------------------------

class RawMaterialLotSerializer(serializers.ModelSerializer):
    raw_material_code = serializers.CharField(
        source="raw_material.code", read_only=True)

    class Meta:
        model = RawMaterialLot
        fields = ["id", "lot_number", "raw_material", "raw_material_code",
                  "supplier", "received_date", "expiry_date",
                  "received_qty", "remaining_qty", "unit_cost",
                  "qc_status", "coa_reference", "container"]


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ["id", "lot", "movement_type", "quantity",
                  "reference", "timestamp", "note"]


# --- Production ------------------------------------------------------------

class ProductionOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionOrder
        fields = ["id", "order_number", "product", "recipe", "target_qty",
                  "unit", "scheduled_date", "reactor", "status", "notes"]


class MaterialConsumptionSerializer(serializers.ModelSerializer):
    deviation_pct = serializers.SerializerMethodField()
    raw_material_code = serializers.CharField(
        source="raw_material.code", read_only=True)

    class Meta:
        model = MaterialConsumption
        fields = ["id", "batch", "raw_material", "raw_material_code",
                  "lot", "target_weight", "actual_weight",
                  "sequence", "dosed_at", "source", "deviation_pct"]

    def get_deviation_pct(self, obj):
        d = obj.deviation_pct
        return str(d) if d is not None else None


class ProductionBatchSerializer(serializers.ModelSerializer):
    consumptions = MaterialConsumptionSerializer(many=True, read_only=True)
    product_code = serializers.CharField(
        source="recipe.product.code", read_only=True)

    class Meta:
        model = ProductionBatch
        fields = ["id", "batch_number", "production_order", "recipe",
                  "product_code", "reactor", "target_qty", "actual_qty",
                  "status", "qc_status", "operator",
                  "started_at", "completed_at", "consumptions"]


class OutputContainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutputContainer
        fields = ["id", "batch", "container", "quantity",
                  "filled_at", "shipment_reference"]


# --- Quality --------------------------------------------------------------

class QCTestResultSerializer(serializers.ModelSerializer):
    parameter_code = serializers.CharField(
        source="parameter.code", read_only=True)

    class Meta:
        model = QCTestResult
        fields = ["id", "parameter", "parameter_code", "lot", "batch",
                  "value", "verdict", "tested_at", "tester", "notes"]


class CertificateOfAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateOfAnalysis
        fields = ["id", "coa_number", "batch", "issued_at",
                  "issued_by", "status", "summary"]


# --- Purchasing ------------------------------------------------------------

class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = ["id", "order_number", "supplier", "order_date",
                  "expected_date", "status", "notes"]


class GoodsReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceipt
        fields = ["id", "receipt_number", "po", "supplier",
                  "received_date", "receiver", "notes"]


# --- Sales -----------------------------------------------------------------

class SalesOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrder
        fields = ["id", "order_number", "customer", "order_date",
                  "delivery_date", "status", "notes"]


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = ["id", "shipment_number", "so", "customer",
                  "shipped_date", "carrier", "vehicle_plate", "notes"]
