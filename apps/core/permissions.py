"""
Mise HERo Finance - Custom Permissions
=======================================
DRF permission classes for access control.
"""

from rest_framework import permissions


class IsAdminOrSelf(permissions.BasePermission):
    """
    Permission that allows admins full access,
    and users access to their own resources.
    """

    def has_object_permission(self, request, view, obj):
        # Admin has full access
        if request.user.is_staff or request.user.role == "admin":
            return True

        # Users can access their own profile
        if hasattr(obj, "id") and obj.id == request.user.id:
            return True

        return False


class IsAdminOrManager(permissions.BasePermission):
    """
    Permission that allows only admins and managers.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return request.user.role in ["admin", "manager"] or request.user.is_staff


class IsAccountant(permissions.BasePermission):
    """
    Permission for accountant-level access.
    Allows admins, managers, and accountants.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return (
            request.user.role in ["admin", "manager", "accountant"]
            or request.user.is_staff
        )


class ReadOnlyOrAdmin(permissions.BasePermission):
    """
    Permission that allows read-only access to all authenticated users,
    but write access only to admins.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Allow read-only methods for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write methods require admin
        return request.user.is_staff or request.user.role == "admin"


class CanManageRules(permissions.BasePermission):
    """
    Permission for managing category rules.
    Requires manager or admin role.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Allow read-only for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write operations require elevated role
        return request.user.role in ["admin", "manager"] or request.user.is_staff


class CanImport(permissions.BasePermission):
    """
    Permission for importing transactions.
    Requires accountant, manager, or admin role.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return (
            request.user.role in ["admin", "manager", "accountant"]
            or request.user.is_staff
        )


class CanExport(permissions.BasePermission):
    """
    Permission for exporting data.
    All authenticated users can export.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated
