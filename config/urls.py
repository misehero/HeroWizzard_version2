"""
URL configuration for Mise HERo Finance project.

API v1 Endpoints:
- /api/v1/auth/         - Authentication (login, register, token)
- /api/v1/users/        - User management
- /api/v1/transactions/ - Transaction CRUD
- /api/v1/imports/      - CSV import
- /api/v1/projects/     - Project lookup
- /api/v1/products/     - Product lookup
- /api/v1/category-rules/ - Auto-detection rules
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    """API root endpoint with available endpoints."""
    return Response(
        {
            "version": "1.0",
            "endpoints": {
                "auth": {
                    "login": "/api/v1/auth/token/",
                    "refresh": "/api/v1/auth/token/refresh/",
                    "register": "/api/v1/auth/register/",
                    "me": "/api/v1/auth/me/",
                },
                "resources": {
                    "transactions": "/api/v1/transactions/",
                    "imports": "/api/v1/imports/",
                    "projects": "/api/v1/projects/",
                    "products": "/api/v1/products/",
                    "category_rules": "/api/v1/category-rules/",
                    "users": "/api/v1/users/",
                },
            },
        }
    )


urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API root
    path("api/v1/", api_root, name="api-root"),
    # Authentication endpoints
    path("api/v1/", include("apps.core.urls", namespace="core")),
    # Transaction endpoints (main business logic)
    path("api/v1/", include("apps.transactions.urls", namespace="transactions")),
    # Future modules (placeholders)
    path("api/v1/analytics/", include("apps.analytics.urls", namespace="analytics")),
    path(
        "api/v1/predictions/", include("apps.predictions.urls", namespace="predictions")
    ),
]

# Serve media/static in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
