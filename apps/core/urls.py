"""
Mise HERo Finance - Core App URLs
==================================
Authentication and user management endpoints.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (AuditLogViewSet, CurrentUserView,
                    CustomTokenObtainPairView, LogoutView, PasswordChangeView,
                    RegisterView, UserViewSet)

app_name = "core"

# Create router for viewsets
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    # JWT Authentication
    path("auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # User Authentication
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    # Current User
    path("auth/me/", CurrentUserView.as_view(), name="current_user"),
    path("auth/change-password/", PasswordChangeView.as_view(), name="change_password"),
    # ViewSets
    path("", include(router.urls)),
]
