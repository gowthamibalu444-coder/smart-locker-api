"""
Authentication views: Register, Login, Token Refresh.
"""
import logging

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from core.throttling import LoginRateThrottle, RegisterRateThrottle
from .models import User
from .serializers import LoginSerializer, UserProfileSerializer, UserRegistrationSerializer

logger = logging.getLogger("apps.accounts")


def _get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Register a new user account. Returns JWT tokens on success.
    Rate limited: 10 registrations/hour per IP.
    """

    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        logger.info(
            "New user registered",
            extra={
                "user_id": str(user.id),
                "action": "user_registered",
                "ip": _get_client_ip(request),
            },
        )

        return Response(
            {
                "success": True,
                "message": "Registration successful.",
                "user": UserProfileSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/auth/login/
    Authenticate user with email & password. Returns JWT tokens.
    Rate limited: 5 attempts/minute per IP (brute-force protection).
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        ip = _get_client_ip(request)

        # Check for inactive account first — authenticate() returns None for both
        # wrong passwords AND inactive users, so we distinguish them explicitly.
        try:
            db_user = User.objects.get(email=email)
            if not db_user.is_active:
                logger.warning(
                    "Login attempt by inactive user",
                    extra={"user_id": str(db_user.id), "action": "login_inactive", "ip": ip},
                )
                return Response(
                    {"success": False, "error": "Account is deactivated."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except User.DoesNotExist:
            pass  # Will be caught below as 401

        user = authenticate(request, username=email, password=password)

        if not user:
            logger.warning(
                "Failed login attempt",
                extra={"action": "login_failed", "ip": ip},
            )
            return Response(
                {"success": False, "error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)

        logger.info(
            "User logged in successfully",
            extra={"user_id": str(user.id), "action": "login_success", "ip": ip},
        )

        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "user": UserProfileSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshAPIView(TokenRefreshView):
    """
    POST /api/auth/refresh/
    Refresh access token using a valid refresh token.
    Wraps simplejwt's default refresh view with a consistent response envelope.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return Response(
                {"success": True, "tokens": response.data},
                status=status.HTTP_200_OK,
            )
        return response
