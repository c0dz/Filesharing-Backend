from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from accounts import views

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("verify/", views.VerifyLinkView.as_view(), name="verify_request"),
    path(
        "verify/<user_id>/<token>/", views.VerifyLinkView.as_view(), name="verify_link"
    ),
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
