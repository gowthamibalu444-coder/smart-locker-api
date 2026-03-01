"""
Unit tests for the accounts app.
Covers: user registration, login, JWT tokens, validation errors.
Uses Django's test client with an in-memory SQLite DB (no PostgreSQL needed).
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class UserRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("auth-register")

    def test_register_user_success(self):
        payload = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "StrongPass@123",
            "confirm_password": "StrongPass@123",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])
        self.assertEqual(response.data["user"]["role"], "user")

    def test_register_duplicate_email(self):
        User.objects.create_user(
            email="dup@example.com", name="Dup", password="Pass@1234"
        )
        payload = {
            "name": "Another",
            "email": "dup@example.com",
            "password": "Pass@5678",
            "confirm_password": "Pass@5678",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_register_password_mismatch(self):
        payload = {
            "name": "User",
            "email": "user@example.com",
            "password": "StrongPass@123",
            "confirm_password": "WrongPass@999",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        response = self.client.post(self.register_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class UserLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("auth-login")
        self.user = User.objects.create_user(
            email="login@example.com",
            name="Login User",
            password="StrongPass@123",
        )

    def test_login_success(self):
        payload = {"email": "login@example.com", "password": "StrongPass@123"}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["tokens"])

    def test_login_wrong_password(self):
        payload = {"email": "login@example.com", "password": "WrongPass"}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        payload = {"email": "ghost@example.com", "password": "AnyPass@123"}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        payload = {"email": "login@example.com", "password": "StrongPass@123"}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
