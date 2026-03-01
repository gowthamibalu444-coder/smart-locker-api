"""
URL routes for the accounts app.
"""
from django.urls import path

from .views import LoginView, RegisterView, TokenRefreshAPIView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshAPIView.as_view(), name="auth-token-refresh"),
]
