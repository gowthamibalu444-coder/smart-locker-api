"""
App configuration for the lockers app.
"""
from django.apps import AppConfig


class LockersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.lockers"
    label = "lockers"
    verbose_name = "Lockers"
