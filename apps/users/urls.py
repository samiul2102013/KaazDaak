from django.urls import path

from .views import (
    CurrentUserView,
    GeneralRegisterView,
    LoginView,
    LogoutView,
    ProviderRegisterView,
    ResendOTPView,
    TokenRefreshView,
    VerifyEmailView,
)

urlpatterns = [
    path("register/general/", GeneralRegisterView.as_view(), name="register-general"),
    path(
        "register/provider/",
        ProviderRegisterView.as_view(),
        name="register-provider",
    ),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
]
