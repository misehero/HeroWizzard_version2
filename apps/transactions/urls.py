"""
Mise HERo Finance - Transactions App URLs
==========================================
API endpoints for transaction management.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CategoryRuleViewSet, CostDetailViewSet, ImportBatchViewSet,
                    ProductSubgroupViewSet, ProductViewSet, ProjectViewSet,
                    TransactionViewSet)

app_name = "transactions"

# Create router and register viewsets
router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"subgroups", ProductSubgroupViewSet, basename="subgroup")
router.register(r"cost-details", CostDetailViewSet, basename="cost-detail")
router.register(r"transactions", TransactionViewSet, basename="transaction")
router.register(r"category-rules", CategoryRuleViewSet, basename="category-rule")
router.register(r"imports", ImportBatchViewSet, basename="import")

urlpatterns = [
    path("", include(router.urls)),
]
