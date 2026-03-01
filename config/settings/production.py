# Production settings — extends base settings.
import os
import dj_database_url
from .base import *  # noqa: F401, F403

DEBUG = False

# Allow host from env or default to allow all if not set
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")


# Neon / Render PostgreSQL connection
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Use local memory cache instead of Redis for free tier
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# WhiteNoise for static files
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
