"""
Unit tests for the reservations app.
Covers: create reservation, prevent double-booking, release, ownership checks, admin visibility.
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.lockers.models import Locker
from apps.reservations.models import Reservation


def auth_header(user):
    token = RefreshToken.for_user(user)
    return f"Bearer {str(token.access_token)}"


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
class ReservationCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@res.com", name="Res User", password="Pass@1234", role="user"
        )
        self.user2 = User.objects.create_user(
            email="user2@res.com", name="Res User 2", password="Pass@1234", role="user"
        )
        self.admin = User.objects.create_user(
            email="admin@res.com", name="Admin", password="Pass@1234", role="admin"
        )
        self.locker = Locker.objects.create(
            locker_number="R001", location="Block A", status="available"
        )

    def _post_reservation(self, user, locker_id):
        self.client.credentials(HTTP_AUTHORIZATION=auth_header(user))
        return self.client.post(
            reverse("reservation-list-create"),
            {"locker_id": str(locker_id)},
            format="json",
        )

    # --- Create ---

    def test_user_can_reserve_available_locker(self):
        response = self._post_reservation(self.user, self.locker.pk)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.locker.refresh_from_db()
        self.assertEqual(self.locker.status, "occupied")

    def test_cannot_reserve_occupied_locker(self):
        # First reservation succeeds
        self._post_reservation(self.user, self.locker.pk)
        # Second reservation: serializer catches status='occupied' → 400
        # (If race condition bypasses serializer, view returns 409)
        response = self._post_reservation(self.user2, self.locker.pk)
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT],
        )

    def test_cannot_reserve_inactive_locker(self):
        self.locker.status = "inactive"
        self.locker.save()
        response = self._post_reservation(self.user, self.locker.pk)
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT])

    def test_reserve_nonexistent_locker_returns_400(self):
        import uuid
        response = self._post_reservation(self.user, uuid.uuid4())
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
class ReservationReleaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="owner@res.com", name="Owner", password="Pass@1234", role="user"
        )
        self.other_user = User.objects.create_user(
            email="other@res.com", name="Other", password="Pass@1234", role="user"
        )
        self.admin = User.objects.create_user(
            email="admin@res.com", name="Admin", password="Pass@1234", role="admin"
        )
        self.locker = Locker.objects.create(
            locker_number="R002", location="Block B", status="occupied"
        )
        self.reservation = Reservation.objects.create(
            user=self.user, locker=self.locker, status="active"
        )

    def test_owner_can_release_reservation(self):
        self.client.credentials(HTTP_AUTHORIZATION=auth_header(self.user))
        response = self.client.put(
            reverse("reservation-release", kwargs={"pk": self.reservation.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.reservation.refresh_from_db()
        self.locker.refresh_from_db()
        self.assertEqual(self.reservation.status, "released")
        self.assertEqual(self.locker.status, "available")

    def test_admin_can_release_any_reservation(self):
        self.client.credentials(HTTP_AUTHORIZATION=auth_header(self.admin))
        response = self.client.put(
            reverse("reservation-release", kwargs={"pk": self.reservation.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_user_cannot_release_reservation(self):
        self.client.credentials(HTTP_AUTHORIZATION=auth_header(self.other_user))
        response = self.client.put(
            reverse("reservation-release", kwargs={"pk": self.reservation.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_release_already_released_reservation(self):
        self.reservation.status = "released"
        self.reservation.save()
        self.client.credentials(HTTP_AUTHORIZATION=auth_header(self.user))
        response = self.client.put(
            reverse("reservation-release", kwargs={"pk": self.reservation.pk})
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
class ReservationListVisibilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email="u1@test.com", name="U1", password="Pass@1234", role="user"
        )
        self.user2 = User.objects.create_user(
            email="u2@test.com", name="U2", password="Pass@1234", role="user"
        )
        self.admin = User.objects.create_user(
            email="ad@test.com", name="Admin", password="Pass@1234", role="admin"
        )
        self.locker1 = Locker.objects.create(
            locker_number="V001", location="Zone V", status="occupied"
        )
        self.locker2 = Locker.objects.create(
            locker_number="V002", location="Zone V", status="occupied"
        )
        Reservation.objects.create(user=self.user1, locker=self.locker1, status="active")
        Reservation.objects.create(user=self.user2, locker=self.locker2, status="active")

    def test_user_sees_only_own_reservations(self):
        self.client.credentials(HTTP_AUTHORIZATION=auth_header(self.user1))
        response = self.client.get(reverse("reservation-list-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_admin_sees_all_reservations(self):
        self.client.credentials(HTTP_AUTHORIZATION=auth_header(self.admin))
        response = self.client.get(reverse("reservation-list-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
