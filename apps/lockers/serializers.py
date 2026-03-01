"""
Serializers for the Locker model.
"""
from rest_framework import serializers

from .models import Locker


class LockerSerializer(serializers.ModelSerializer):
    """Full locker serializer for admin CRUD."""

    class Meta:
        model = Locker
        fields = [
            "id",
            "locker_number",
            "location",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_locker_number(self, value):
        """Ensure locker_number is uppercase and alphanumeric."""
        value = value.strip().upper()
        if not value.replace("-", "").replace("_", "").isalnum():
            raise serializers.ValidationError(
                "Locker number must contain only letters, digits, hyphens, or underscores."
            )
        return value


class LockerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views and cached responses."""

    class Meta:
        model = Locker
        fields = ["id", "locker_number", "location", "status"]


class LockerCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin create/update operations."""

    class Meta:
        model = Locker
        fields = ["locker_number", "location", "status"]

    def validate_locker_number(self, value):
        return value.strip().upper()
