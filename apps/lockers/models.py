"""
Locker model.
"""
import uuid

from django.db import models


class Locker(models.Model):
    """
    Represents a physical storage locker.
    Status transitions:
        available  → occupied  (on reservation)
        occupied   → available (on release)
        any        → inactive  (admin deactivation)
    """

    STATUS_AVAILABLE = "available"
    STATUS_OCCUPIED = "occupied"
    STATUS_INACTIVE = "inactive"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_OCCUPIED, "Occupied"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    locker_number = models.CharField(max_length=50, unique=True)
    location = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lockers"
        ordering = ["locker_number"]

    def __str__(self):
        return f"Locker #{self.locker_number} @ {self.location} [{self.status}]"

    @property
    def is_available(self):
        return self.status == self.STATUS_AVAILABLE
