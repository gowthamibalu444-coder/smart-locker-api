"""
Serializers for the Reservation model.
"""
from rest_framework import serializers

from apps.accounts.serializers import UserProfileSerializer
from apps.lockers.serializers import LockerListSerializer

from .models import Reservation


class ReservationSerializer(serializers.ModelSerializer):
    """Full reservation serializer — includes nested user and locker info."""

    user = UserProfileSerializer(read_only=True)
    locker = LockerListSerializer(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "user",
            "locker",
            "status",
            "reserved_at",
            "released_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ReservationCreateSerializer(serializers.Serializer):
    """Serializer for creating a new reservation — accepts locker_id."""

    locker_id = serializers.UUIDField()

    def validate_locker_id(self, value):
        from apps.lockers.models import Locker

        try:
            locker = Locker.objects.get(pk=value)
        except Locker.DoesNotExist:
            raise serializers.ValidationError("Locker not found.")

        if locker.status != Locker.STATUS_AVAILABLE:
            raise serializers.ValidationError(
                f"Locker is not available (current status: {locker.status})."
            )
        return value
