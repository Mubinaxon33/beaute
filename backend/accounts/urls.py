from django.urls import path

from .views import (
    account_delete_view,
    login_2fa_view,
    login_support_view,
    login_view,
    logout_view,
    profile_password_change_view,
    profile_photo_update_view,
    profile_update_view,
    profile_view,
    register_view,
)

urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("login/2fa/", login_2fa_view, name="login-2fa"),
    path("login/support/", login_support_view, name="login-support"),
    path("profile/", profile_view, name="profile"),
    path("profile/update/", profile_update_view, name="profile-update"),
    path("profile/photo/", profile_photo_update_view, name="profile-photo-update"),
    path("profile/password/", profile_password_change_view, name="profile-password-change"),
    path("profile/delete/", account_delete_view, name="account-delete"),
    path("logout/", logout_view, name="logout"),
]
