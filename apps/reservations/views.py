"""
Reservation views with concurrency protection via select_for_update.
"""
import logging
from datetime import datetime, timezone

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.lockers.models import Locker
from core.permissions import IsAdminRole, IsAuthenticatedAndActive, IsOwnerOrAdmin

from .models import Reservation
from .serializers import ReservationCreateSerializer, ReservationSerializer

logger = logging.getLogger("apps.reservations")


class ReservationListCreateView(APIView):
    """
    GET  /api/reservations/ — List reservations (User: own / Admin: all)
    POST /api/reservations/ — Create a new reservation (authenticated users)
    """

    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        user = request.user
        if user.role == "admin":
            reservations = Reservation.objects.select_related("user", "locker").all()
        else:
            reservations = Reservation.objects.select_related("user", "locker").filter(user=user)

        serializer = ReservationSerializer(reservations, many=True)
        return Response(
            {
                "success": True,
                "count": reservations.count(),
                "reservations": serializer.data,
            }
        )

    def post(self, request):
        """
        Reserve a locker.
        Uses select_for_update() inside a transaction to prevent race conditions.
        DB-level UniqueConstraint on (locker, status='active') provides the safety net.
        """
        serializer = ReservationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        locker_id = serializer.validated_data["locker_id"]

        try:
            with transaction.atomic():
                # Lock the locker row to prevent concurrent reservations
                locker = Locker.objects.select_for_update().get(pk=locker_id)

                if locker.status != Locker.STATUS_AVAILABLE:
                    return Response(
                        {
                            "success": False,
                            "error": f"Locker is no longer available (status: {locker.status}).",
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                # Mark locker as occupied
                locker.status = Locker.STATUS_OCCUPIED
                locker.save(update_fields=["status", "updated_at"])

                # Create the reservation
                reservation = Reservation.objects.create(
                    user=request.user,
                    locker=locker,
                    status=Reservation.STATUS_ACTIVE,
                )

        except IntegrityError:
            # UniqueConstraint violation — another request beat us to it
            logger.warning(
                "Concurrent reservation conflict",
                extra={
                    "user_id": str(request.user.id),
                    "action": "reservation_conflict",
                    "locker_id": str(locker_id),
                },
            )
            return Response(
                {"success": False, "error": "Locker was just reserved by another user. Please try a different locker."},
                status=status.HTTP_409_CONFLICT,
            )

        logger.info(
            "Reservation created",
            extra={
                "user_id": str(request.user.id),
                "action": "create_reservation",
                "locker_id": str(locker.id),
                "reservation_id": str(reservation.id),
            },
        )

        return Response(
            {
                "success": True,
                "message": "Locker reserved successfully.",
                "reservation": ReservationSerializer(reservation).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ReservationDetailView(APIView):
    """
    GET /api/reservations/<id>/ — Get reservation details (owner or admin)
    """

    permission_classes = [IsAuthenticatedAndActive]

    def _get_reservation(self, pk):
        try:
            return Reservation.objects.select_related("user", "locker").get(pk=pk)
        except Reservation.DoesNotExist:
            return None

    def get(self, request, pk):
        reservation = self._get_reservation(pk)
        if not reservation:
            return Response(
                {"success": False, "error": "Reservation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check ownership: only owner or admin can view
        permission = IsOwnerOrAdmin()
        if not permission.has_object_permission(request, self, reservation):
            return Response(
                {"success": False, "error": "You do not have permission to view this reservation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response({"success": True, "reservation": ReservationSerializer(reservation).data})


class ReleaseReservationView(APIView):
    """
    PUT /api/reservations/<id>/release/
    Release an active reservation, freeing the locker.
    Only the reservation owner or an admin can release.
    """

    permission_classes = [IsAuthenticatedAndActive]

    def _get_reservation(self, pk):
        try:
            return Reservation.objects.select_related("user", "locker").get(pk=pk)
        except Reservation.DoesNotExist:
            return None

    def put(self, request, pk):
        reservation = self._get_reservation(pk)
        if not reservation:
            return Response(
                {"success": False, "error": "Reservation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check ownership
        permission = IsOwnerOrAdmin()
        if not permission.has_object_permission(request, self, reservation):
            return Response(
                {"success": False, "error": "You do not have permission to release this reservation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if reservation.status == Reservation.STATUS_RELEASED:
            return Response(
                {"success": False, "error": "This reservation has already been released."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Release the reservation
            reservation.status = Reservation.STATUS_RELEASED
            reservation.released_at = datetime.now(timezone.utc)
            reservation.save(update_fields=["status", "released_at", "updated_at"])

            # Free the locker
            locker = reservation.locker
            locker.status = Locker.STATUS_AVAILABLE
            locker.save(update_fields=["status", "updated_at"])

        logger.info(
            "Reservation released",
            extra={
                "user_id": str(request.user.id),
                "action": "release_reservation",
                "locker_id": str(locker.id),
                "reservation_id": str(reservation.id),
            },
        )

        return Response(
            {
                "success": True,
                "message": "Locker released successfully.",
                "reservation": ReservationSerializer(reservation).data,
            }
        )
