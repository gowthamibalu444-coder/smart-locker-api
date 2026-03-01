"""
Django admin registration for the lockers app.
"""
from django.contrib import admin

from .models import Locker


@admin.register(Locker)
class LockerAdmin(admin.ModelAdmin):
    list_display = ["locker_number", "location", "status", "created_at"]
    list_filter = ["status", "location"]
    search_fields = ["locker_number", "location"]
    ordering = ["locker_number"]
    readonly_fields = ["id", "created_at", "updated_at"]
