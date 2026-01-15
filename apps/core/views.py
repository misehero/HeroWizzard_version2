"""
Mise HERo Finance - Core App Views
===================================
Views for user management and authentication.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import AuditLog, User
from .permissions import IsAdminOrSelf
from .serializers import (AuditLogSerializer, CustomTokenObtainPairSerializer,
                          PasswordChangeSerializer, UserCreateSerializer,
                          UserDetailSerializer, UserSerializer,
                          UserUpdateSerializer)

# =============================================================================
# AUTHENTICATION VIEWS
# =============================================================================


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT login endpoint that returns user info along with tokens.

    POST /api/v1/auth/token/
    {
        "email": "user@example.com",
        "password": "password123"
    }

    Returns:
    {
        "access": "...",
        "refresh": "...",
        "user": {...}
    }
    """

    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """
    Logout endpoint that blacklists the refresh token.

    POST /api/v1/auth/logout/
    {
        "refresh": "..."
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            return Response({"success": True, "message": "Úspěšně odhlášeno."})
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class RegisterView(generics.CreateAPIView):
    """
    User registration endpoint.

    POST /api/v1/auth/register/
    {
        "email": "newuser@example.com",
        "password": "password123",
        "password_confirm": "password123",
        "first_name": "Jan",
        "last_name": "Novák"
    }
    """

    serializer_class = UserCreateSerializer
    permission_classes = [
        AllowAny
    ]  # Change to IsAdminUser if registration should be admin-only

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens for new user
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "success": True,
                "message": "Uživatel úspěšně vytvořen.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# USER VIEWS
# =============================================================================


class CurrentUserView(APIView):
    """
    Get or update current authenticated user.

    GET /api/v1/auth/me/
    PATCH /api/v1/auth/me/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user profile."""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        """Update current user profile."""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(UserDetailSerializer(request.user).data)


class PasswordChangeView(APIView):
    """
    Change password for current user.

    POST /api/v1/auth/change-password/
    {
        "current_password": "oldpassword",
        "new_password": "newpassword123",
        "new_password_confirm": "newpassword123"
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"success": True, "message": "Heslo bylo úspěšně změněno."})


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user management (admin only).

    list: Get all users
    retrieve: Get single user
    create: Create new user
    update: Update user
    destroy: Deactivate user
    """

    queryset = User.objects.all().order_by("-created_at")
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["role", "is_active", "primary_kmen"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["email", "created_at", "last_login"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        elif self.action == "retrieve":
            return UserDetailSerializer
        return UserSerializer

    def get_permissions(self):
        """Allow users to view/update their own profile."""
        if self.action in ["retrieve", "update", "partial_update"]:
            return [IsAuthenticated(), IsAdminOrSelf()]
        return super().get_permissions()

    def perform_destroy(self, instance):
        """Soft delete by deactivating user."""
        instance.is_active = False
        instance.save()

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Reactivate a deactivated user."""
        user = self.get_object()
        user.is_active = True
        user.save()

        return Response(
            {"success": True, "message": f"Uživatel {user.email} byl aktivován."}
        )

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        """
        Admin endpoint to reset user password.
        Generates a random password and returns it.
        """
        import secrets
        import string

        user = self.get_object()

        # Generate random password
        alphabet = string.ascii_letters + string.digits
        new_password = "".join(secrets.choice(alphabet) for _ in range(12))

        user.set_password(new_password)
        user.save()

        return Response(
            {
                "success": True,
                "message": f"Heslo pro {user.email} bylo resetováno.",
                "temporary_password": new_password,
            }
        )


# =============================================================================
# AUDIT LOG VIEWS
# =============================================================================


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing audit logs (admin only).
    """

    queryset = AuditLog.objects.select_related("user").order_by("-timestamp")
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["action", "model_name", "user"]
    ordering_fields = ["timestamp"]
    ordering = ["-timestamp"]
