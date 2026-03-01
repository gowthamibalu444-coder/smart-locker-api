"""
Test settings — uses SQLite in-memory DB and LocMemCache.
No PostgreSQL or Redis needed to run the test suite.

Usage:
    python manage.py test --settings=config.settings.test
"""
from .base import *  # noqa: F401, F403

DEBUG = True

# Override DB with SQLite for fast, dependency-free test runs
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Override Redis cache with in-memory cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Speed up password hashing during tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
