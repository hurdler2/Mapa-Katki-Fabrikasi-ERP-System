from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView, TokenVerifyView,
)

from . import retrieval, scada_endpoints, views


router = DefaultRouter()
router.register("raw-materials", views.RawMaterialViewSet, basename="rawmaterial")
router.register("products", views.ProductViewSet, basename="product")
router.register("customers", views.CustomerViewSet, basename="customer")
router.register("suppliers", views.SupplierViewSet, basename="supplier")
router.register("containers", views.ContainerViewSet, basename="container")
router.register("recipes", views.RecipeViewSet, basename="recipe")
router.register("lots", views.RawMaterialLotViewSet, basename="lot")
router.register("stock-movements", views.StockMovementViewSet, basename="stockmovement")
router.register("production-orders", views.ProductionOrderViewSet, basename="productionorder")
router.register("batches", views.ProductionBatchViewSet, basename="batch")
router.register("consumptions", views.MaterialConsumptionViewSet, basename="consumption")
router.register("output-containers", views.OutputContainerViewSet, basename="outputcontainer")
router.register("qc-results", views.QCTestResultViewSet, basename="qcresult")
router.register("coa", views.COAViewSet, basename="coa")
router.register("purchase-orders", views.PurchaseOrderViewSet, basename="po")
router.register("goods-receipts", views.GoodsReceiptViewSet, basename="gr")
router.register("sales-orders", views.SalesOrderViewSet, basename="so")
router.register("shipments", views.ShipmentViewSet, basename="shipment")


urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # MCOS Faz F — Retrieval endpoint (00_MCO_1 sinav kriteri: <2 dk)
    path("retrieve/", retrieval.retrieve, name="mcos_retrieve"),
    # SCADA köprüsü — 3 endpoint (batch POST, recipe GET, status GET)
    # NOT: Django URL prefix'i /api/v1/ olduğundan tam URL'ler:
    #   POST  /api/v1/production/batches/from-scada/
    #   GET   /api/v1/production/active-recipe/
    #   GET   /api/v1/production/scada/status/
    path("production/batches/from-scada/",
         scada_endpoints.batch_from_scada,
         name="scada_batch_ingest"),
    path("production/active-recipe/",
         scada_endpoints.active_recipe_for_scada,
         name="scada_active_recipe"),
    path("production/scada/status/",
         scada_endpoints.scada_status,
         name="scada_status"),
    path("", include(router.urls)),
    path("auth/session/", include("rest_framework.urls")),
]
