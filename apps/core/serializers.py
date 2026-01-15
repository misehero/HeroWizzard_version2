"""
Mise HERo Finance - Core App Serializers
=========================================
Serializers for user management and authentication.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import AuditLog, User

# =============================================================================
# USER SERIALIZERS
# =============================================================================


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    Used for listing and retrieving users.
    """

    role_display = serializers.CharField(source="get_role_display", read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "role_display",
            "primary_kmen",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
            "last_login",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_login"]


class UserDetailSerializer(UserSerializer):
    """
    Extended serializer with additional user details.
    """

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["last_login_ip"]


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users.
    Includes password validation.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "role",
            "primary_kmen",
        ]

    def validate(self, data):
        """Validate passwords match."""
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Hesla se neshodují."}
            )
        return data

    def create(self, validated_data):
        """Create user with hashed password."""
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    Password changes handled separately.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "primary_kmen"]


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for changing user password.
    """

    current_password = serializers.CharField(
        required=True,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        required=True,
        style={"input_type": "password"},
        validators=[validate_password],
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={"input_type": "password"},
    )

    def validate_current_password(self, value):
        """Validate current password is correct."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Současné heslo není správné.")
        return value

    def validate(self, data):
        """Validate new passwords match."""
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Nová hesla se neshodují."}
            )
        return data

    def save(self):
        """Update user password."""
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


# =============================================================================
# AUTHENTICATION SERIALIZERS
# =============================================================================


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes user info in response.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add user info to response
        data["user"] = {
            "id": str(self.user.id),
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "full_name": self.user.full_name,
            "role": self.user.role,
            "role_display": self.user.get_role_display(),
            "primary_kmen": self.user.primary_kmen,
        }

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims to token
        token["email"] = user.email
        token["role"] = user.role
        token["full_name"] = user.full_name

        return token


class LoginSerializer(serializers.Serializer):
    """
    Serializer for login endpoint (non-JWT).
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        style={"input_type": "password"},
    )

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        if email and password:
            user = authenticate(
                request=self.context.get("request"), email=email, password=password
            )

            if not user:
                raise serializers.ValidationError(
                    "Neplatné přihlašovací údaje.", code="authentication"
                )

            if not user.is_active:
                raise serializers.ValidationError(
                    "Uživatelský účet je deaktivován.", code="authentication"
                )

            data["user"] = user
        else:
            raise serializers.ValidationError(
                "Email a heslo jsou povinné.", code="authentication"
            )

        return data


# =============================================================================
# AUDIT LOG SERIALIZER
# =============================================================================


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for AuditLog model.
    """

    action_display = serializers.CharField(source="get_action_display", read_only=True)
    user_email = serializers.EmailField(
        source="user.email", read_only=True, allow_null=True
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "user_email",
            "action",
            "action_display",
            "model_name",
            "object_id",
            "object_repr",
            "changes",
            "ip_address",
            "user_agent",
            "timestamp",
        ]
        read_only_fields = fields
