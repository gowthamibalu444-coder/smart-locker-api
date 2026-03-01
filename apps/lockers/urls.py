"""
URL routes for the lockers app.
"""
from django.urls import path

from .views import AvailableLockerListView, LockerDetailView, LockerListCreateView

urlpatterns = [
    # NOTE: 'available/' MUST come before '<pk>/' to avoid UUID matching
    path("available/", AvailableLockerListView.as_view(), name="locker-available"),
    path("", LockerListCreateView.as_view(), name="locker-list-create"),
    path("<uuid:pk>/", LockerDetailView.as_view(), name="locker-detail"),
]
