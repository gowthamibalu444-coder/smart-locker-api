"""
Custom DRF throttle classes for per-endpoint rate limiting.
"""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Strict throttle for the login endpoint.
    Rate: 5 attempts per minute per IP (brute-force protection).
    Defined in settings: DEFAULT_THROTTLE_RATES['login']
    """
    scope = "login"


class RegisterRateThrottle(AnonRateThrottle):
    """
    Throttle for the registration endpoint.
    Rate: 10 registrations per hour per IP (spam prevention).
    Defined in settings: DEFAULT_THROTTLE_RATES['register']
    """
    scope = "register"
