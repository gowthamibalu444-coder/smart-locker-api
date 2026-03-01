"""
URL routes for the reservations app.
"""
from django.urls import path

from .views import ReleaseReservationView, ReservationDetailView, ReservationListCreateView

urlpatterns = [
    path("", ReservationListCreateView.as_view(), name="reservation-list-create"),
    path("<uuid:pk>/", ReservationDetailView.as_view(), name="reservation-detail"),
    path("<uuid:pk>/release/", ReleaseReservationView.as_view(), name="reservation-release"),
]
