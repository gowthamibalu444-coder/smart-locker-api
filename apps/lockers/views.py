"""
Locker views with Redis caching for available lockers.
"""
import json
import logging

from django.core.cache import cache
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminRole, IsAuthenticatedAndActive

from .models import Locker
from .serializers import LockerCreateUpdateSerializer, LockerListSerializer, LockerSerializer

logger = logging.getLogger("apps.lockers")


class LockerListCreateView(APIView):
    """
    GET  /api/lockers/ — List all lockers (any authenticated user)
    POST /api/lockers/ — Create a new locker (admin only)
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminRole()]
        return [IsAuthenticatedAndActive()]

    def get(self, request):
        lockers = Locker.objects.all()
        # Filter by status query param if provided
        status_filter = request.query_params.get("status")
        if status_filter:
            lockers = lockers.filter(status=status_filter)
        serializer = LockerSerializer(lockers, many=True)
        logger.info(
            "Listed all lockers",
            extra={"user_id": str(request.user.id), "action": "list_lockers"},
        )
        return Response({"success": True, "count": lockers.count(), "lockers": serializer.data})

    def post(self, request):
        serializer = LockerCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        locker = serializer.save()
        logger.info(
            "Locker created",
            extra={
                "user_id": str(request.user.id),
                "action": "create_locker",
                "locker_id": str(locker.id),
            },
        )
        return Response(
            {"success": True, "message": "Locker created.", "locker": LockerSerializer(locker).data},
            status=status.HTTP_201_CREATED,
        )


class LockerDetailView(APIView):
    """
    GET    /api/lockers/<id>/ — Locker details (any authenticated user)
    PUT    /api/lockers/<id>/ — Update locker (admin only)
    DELETE /api/lockers/<id>/ — Deactivate locker (admin only)
    """

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdminRole()]
        return [IsAuthenticatedAndActive()]

    def _get_locker(self, pk):
        try:
            return Locker.objects.get(pk=pk)
        except Locker.DoesNotExist:
            return None

    def get(self, request, pk):
        locker = self._get_locker(pk)
        if not locker:
            return Response(
                {"success": False, "error": "Locker not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"success": True, "locker": LockerSerializer(locker).data})

    def put(self, request, pk):
        locker = self._get_locker(pk)
        if not locker:
            return Response(
                {"success": False, "error": "Locker not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = LockerCreateUpdateSerializer(locker, data=request.data, partial=False)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated_locker = serializer.save()
        logger.info(
            "Locker updated",
            extra={
                "user_id": str(request.user.id),
                "action": "update_locker",
                "locker_id": str(updated_locker.id),
            },
        )
        return Response(
            {"success": True, "message": "Locker updated.", "locker": LockerSerializer(updated_locker).data}
        )

    def patch(self, request, pk):
        locker = self._get_locker(pk)
        if not locker:
            return Response(
                {"success": False, "error": "Locker not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = LockerCreateUpdateSerializer(locker, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated_locker = serializer.save()
        return Response(
            {"success": True, "message": "Locker updated.", "locker": LockerSerializer(updated_locker).data}
        )

    def delete(self, request, pk):
        locker = self._get_locker(pk)
        if not locker:
            return Response(
                {"success": False, "error": "Locker not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if locker.status == Locker.STATUS_OCCUPIED:
            return Response(
                {"success": False, "error": "Cannot deactivate an occupied locker."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        locker.status = Locker.STATUS_INACTIVE
        locker.save(update_fields=["status", "updated_at"])
        logger.info(
            "Locker deactivated",
            extra={
                "user_id": str(request.user.id),
                "action": "deactivate_locker",
                "locker_id": str(locker.id),
            },
        )
        return Response({"success": True, "message": "Locker deactivated."})


class AvailableLockerListView(APIView):
    """
    GET /api/lockers/available/
    Lists all available lockers.
    Redis-cached with a TTL of AVAILABLE_LOCKERS_CACHE_TTL seconds.
    Cache is NOT invalidated on change — it expires naturally.
    """

    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        cache_key = settings.AVAILABLE_LOCKERS_CACHE_KEY
        ttl = settings.AVAILABLE_LOCKERS_CACHE_TTL

        # --- Check Redis cache first ---
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(
                "Available lockers served from cache",
                extra={"user_id": str(request.user.id), "action": "list_available_lockers_cached"},
            )
            return Response(
                {
                    "success": True,
                    "source": "cache",
                    "count": len(cached),
                    "lockers": cached,
                }
            )

        # --- Cache miss: query DB ---
        available_lockers = Locker.objects.filter(status=Locker.STATUS_AVAILABLE)
        serializer = LockerListSerializer(available_lockers, many=True)
        data = serializer.data

        # Store serialized list in Redis
        cache.set(cache_key, data, timeout=ttl)

        logger.info(
            "Available lockers served from DB and cached",
            extra={"user_id": str(request.user.id), "action": "list_available_lockers_db"},
        )
        return Response(
            {
                "success": True,
                "source": "database",
                "count": len(data),
                "lockers": data,
            }
        )
