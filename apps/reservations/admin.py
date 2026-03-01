"""
Django admin registration for the reservations app.
"""
from django.contrib import admin

from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "locker", "status", "reserved_at", "released_at"]
    list_filter = ["status"]
    search_fields = ["user__email", "locker__locker_number"]
    ordering = ["-reserved_at"]
    readonly_fields = ["id", "reserved_at", "released_at", "created_at", "updated_at"]
