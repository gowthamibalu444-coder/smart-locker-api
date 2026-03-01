"""
Unit tests for the lockers app.
Covers: CRUD permissions (admin vs user), available locker listing, Redis cache behavior.
"""
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.lockers.models import Locker


def get_auth_header(user):
    """Helper to generate Bearer token for a user."""
    token = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {str(token.access_token)}"}


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    AVAILABLE_LOCKERS_CACHE_KEY="locker:available",
    AVAILABLE_LOCKERS_CACHE_TTL=60,
)
class LockerCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com", name="Admin", password="Admin@1234", role="admin"
        )
        self.user = User.objects.create_user(
            email="user@test.com", name="User", password="User@1234", role="user"
        )
        self.locker = Locker.objects.create(
            locker_number="L001", location="Floor 1", status="available"
        )

    # --- Create Locker ---

    def test_admin_can_create_locker(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(self.admin).access_token)}"
        )
        payload = {"locker_number": "L002", "location": "Floor 2"}
        response = self.client.post(reverse("locker-list-create"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])

    def test_user_cannot_create_locker(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(self.user).access_token)}"
        )
        payload = {"locker_number": "L003", "location": "Floor 3"}
        response = self.client.post(reverse("locker-list-create"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- List Lockers ---

    def test_any_user_can_list_lockers(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(self.user).access_token)}"
        )
        response = self.client.get(reverse("locker-list-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_unauthenticated_cannot_list_lockers(self):
        response = self.client.get(reverse("locker-list-create"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Get Locker Detail ---

    def test_get_locker_detail(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(self.user).access_token)}"
        )
        response = self.client.get(reverse("locker-detail", kwargs={"pk": self.locker.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["locker"]["locker_number"], "L001")

    def test_get_nonexistent_locker_returns_404(self):
        import uuid
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(self.user).access_token)}"
        )
        response = self.client.get(
            reverse("locker-detail", kwargs={"pk": uuid.uuid4()})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Update Locker (Admin only) ---

    def test_admin_can_update_locker(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(self.admin).access_token)}"
        )
        payload = {"locker_number": "L001", "location": "Floor 1 Updated", "status": "available"}
        response = self.client.put(
            reverse("locker-detail", kwargs={"pk": self.locker.pk}), payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["locker"]["location"], "Floor 1 Updated")

    # --- Deactivate Locker (Admin only) ---

    def test_admin_can_deactivate_locker(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(self.admin).access_token)}"
        )
        response = self.client.delete(
            reverse("locker-detail", kwargs={"pk": self.locker.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.locker.refresh_from_db()
        self.assertEqual(self.locker.status, "inactive")

    def test_cannot_deactivate_occupied_locker(self):
        self.locker.status = "occupied"
        self.locker.save()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(self.admin).access_token)}"
        )
        response = self.client.delete(
            reverse("locker-detail", kwargs={"pk": self.locker.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    AVAILABLE_LOCKERS_CACHE_KEY="locker:available",
    AVAILABLE_LOCKERS_CACHE_TTL=60,
)
class AvailableLockerCacheTests(TestCase):
    """Tests Redis caching behavior on /api/lockers/available/."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # Ensure each test starts with a clean cache
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@cache.com", name="Cache User", password="Pass@1234", role="user"
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(self.user).access_token)}"
        )
        Locker.objects.create(locker_number="A001", location="Zone A", status="available")
        Locker.objects.create(locker_number="A002", location="Zone A", status="occupied")

    def test_available_lockers_returns_only_available(self):
        response = self.client.get(reverse("locker-available"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["lockers"][0]["locker_number"], "A001")

    def test_first_call_hits_database(self):
        response = self.client.get(reverse("locker-available"))
        self.assertEqual(response.data["source"], "database")

    def test_second_call_hits_cache(self):
        self.client.get(reverse("locker-available"))  # Populate cache
        response = self.client.get(reverse("locker-available"))  # Should hit cache
        self.assertEqual(response.data["source"], "cache")
