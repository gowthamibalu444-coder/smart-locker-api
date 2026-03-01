"""
Reservation model — links a User to a Locker with lifecycle tracking.
"""
import uuid

from django.conf import settings
from django.db import models

from apps.lockers.models import Locker


class Reservation(models.Model):
    """
    Tracks a locker reservation lifecycle.
    Status:
        active   — Locker is currently reserved by the user.
        released — User has returned the locker.
    """

    STATUS_ACTIVE = "active"
    STATUS_RELEASED = "released"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_RELEASED, "Released"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    locker = models.ForeignKey(
        Locker,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True
    )
    reserved_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reservations"
        ordering = ["-reserved_at"]
        constraints = [
            # A locker can only have ONE active reservation at a time
            models.UniqueConstraint(
                fields=["locker"],
                condition=models.Q(status="active"),
                name="unique_active_reservation_per_locker",
            )
        ]

    def __str__(self):
        return f"Reservation {self.id} | User={self.user.email} | Locker={self.locker.locker_number} | {self.status}"
