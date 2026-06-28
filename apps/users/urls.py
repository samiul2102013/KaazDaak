from django.urls import path

from .views import (
    CurrentUserView,
    HirerRegisterView,
    KaazbirRegisterView,
    KYCSubmitView,
    LoginView,
    LogoutView,
    ResendOTPView,
    TokenRefreshView,
    VerifyEmailView,
)

urlpatterns = [
    path("register/hirer/", HirerRegisterView.as_view(), name="register-hirer"),
    path(
        "register/kaazbir/",
        KaazbirRegisterView.as_view(),
        name="register-kaazbir",
    ),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("kyc/submit/", KYCSubmitView.as_view(), name="kyc-submit"),
]
