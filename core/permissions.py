"""
Custom DRF permission classes for role-based access control.
"""
from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Allows access only to users with role='admin'.
    """

    message = "Access restricted to administrators only."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsUserRole(BasePermission):
    """
    Allows access only to users with role='user'.
    """

    message = "Access restricted to regular users only."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "user"
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission: allows access if the requesting user
    owns the object OR has the 'admin' role.
    The object must have a `user` attribute (FK).
    """

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == "admin":
            return True
        # Check ownership via `user` FK
        return getattr(obj, "user", None) == request.user


class IsAuthenticatedAndActive(BasePermission):
    """
    Allows access to any authenticated, active user (admin or user).
    """

    message = "Authentication credentials were not provided or account is inactive."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )
