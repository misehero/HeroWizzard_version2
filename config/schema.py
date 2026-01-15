"""
Mise HERo Finance - API Schema Configuration
=============================================
OpenAPI/Swagger documentation setup using drf-spectacular.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter


# Custom JWT Authentication scheme for documentation
class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "rest_framework_simplejwt.authentication.JWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token authentication. Get token from /api/v1/auth/token/",
        }


# Common API parameters
PAGINATION_PARAMETERS = [
    OpenApiParameter(
        name="page",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Page number for pagination",
    ),
    OpenApiParameter(
        name="page_size",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Number of results per page (default: 50)",
    ),
]

DATE_RANGE_PARAMETERS = [
    OpenApiParameter(
        name="date_from",
        type=OpenApiTypes.DATE,
        location=OpenApiParameter.QUERY,
        description="Filter transactions from this date (YYYY-MM-DD)",
    ),
    OpenApiParameter(
        name="date_to",
        type=OpenApiTypes.DATE,
        location=OpenApiParameter.QUERY,
        description="Filter transactions until this date (YYYY-MM-DD)",
    ),
]

TRANSACTION_FILTER_PARAMETERS = DATE_RANGE_PARAMETERS + [
    OpenApiParameter(
        name="status",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Filter by status",
        enum=["importovano", "zpracovano", "schvaleno", "upraveno", "chyba"],
    ),
    OpenApiParameter(
        name="prijem_vydaj",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Filter by income/expense",
        enum=["P", "V"],
    ),
    OpenApiParameter(
        name="projekt",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Filter by project ID",
    ),
    OpenApiParameter(
        name="search",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Search in description, counterparty, merchant",
    ),
    OpenApiParameter(
        name="is_categorized",
        type=OpenApiTypes.BOOL,
        location=OpenApiParameter.QUERY,
        description="Filter by categorization status",
    ),
]


# Example responses for documentation
TRANSACTION_EXAMPLES = {
    "list": OpenApiExample(
        name="Transaction List",
        value={
            "count": 150,
            "next": "http://api/v1/transactions/?page=2",
            "previous": None,
            "results": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "datum": "2024-01-15",
                    "castka": "25000.00",
                    "poznamka_zprava": "Platba za fakturu",
                    "status": "importovano",
                    "prijem_vydaj": "P",
                    "projekt_name": "4CFuture",
                }
            ],
        },
    ),
    "detail": OpenApiExample(
        name="Transaction Detail",
        value={
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "datum": "2024-01-15",
            "ucet": "123456789/0100",
            "typ": "Příchozí platba",
            "poznamka_zprava": "Platba za fakturu 2024001",
            "variabilni_symbol": "2024001",
            "castka": "25000.00",
            "status": "zpracovano",
            "prijem_vydaj": "P",
            "druh": "Produkt",
            "detail": "Školení Silný lídr",
            "kmen": "MH",
            "mh_pct": "100.00",
            "sk_pct": "0.00",
            "xp_pct": "0.00",
            "fr_pct": "0.00",
            "projekt": "4cfuture",
            "projekt_name": "4CFuture",
        },
    ),
}

IMPORT_EXAMPLES = {
    "success": OpenApiExample(
        name="Successful Import",
        value={
            "success": True,
            "batch_id": "123e4567-e89b-12d3-a456-426614174000",
            "total_rows": 100,
            "imported": 98,
            "skipped": 2,
            "errors": 0,
            "duration_seconds": 1.5,
        },
    ),
    "with_errors": OpenApiExample(
        name="Import with Errors",
        value={
            "success": True,
            "batch_id": "123e4567-e89b-12d3-a456-426614174000",
            "total_rows": 100,
            "imported": 95,
            "skipped": 2,
            "errors": 3,
            "duration_seconds": 2.1,
            "error_details": [
                {"row": 15, "error": "Invalid date format"},
                {"row": 42, "error": "Missing required field: castka"},
            ],
        },
    ),
}
