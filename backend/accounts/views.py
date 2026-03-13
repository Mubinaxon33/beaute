from collections import Counter
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db import OperationalError, ProgrammingError
from django.db.models import Avg
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from bookings.models import Booking
from salons.models import Review

from .forms import (
    AccountDeleteForm,
    LoginStepOneForm,
    LoginStepTwoForm,
    PasswordChangeForm,
    ProfileImageUpdateForm,
    ProfileUpdateForm,
    RegistrationForm,
    SupportRequestForm,
    TwoFactorUpdateForm,
    get_or_create_security_profile,
    parse_json_body,
)
from .models import SupportRequest

User = get_user_model()
TWO_FA_SIGNER = signing.TimestampSigner(salt="beauty-salon-2fa")
POINTS_PER_CONFIRMED_BOOKING = Decimal("87.5")


def _membership_level(points: Decimal) -> str:
    if points >= Decimal("7001"):
        return "Royal"
    if points >= Decimal("5000"):
        return "Elite"
    if points >= Decimal("4000"):
        return "Diamond"
    if points >= Decimal("3000"):
        return "Platinum"
    if points >= Decimal("2000"):
        return "Gold"
    if points >= Decimal("1000"):
        return "Silver"
    return "Bronze"


def _is_json_request(request: HttpRequest) -> bool:
    return (request.content_type or "").startswith("application/json") or request.GET.get("format") == "json"


def _json_or_template(request: HttpRequest, template_name: str, context: dict):
    if _is_json_request(request):
        return JsonResponse(context)
    return render(request, template_name, context)


def root_redirect_view(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("salons")
    return redirect("login")


@require_http_methods(["GET", "POST"])
def register_view(request: HttpRequest):
    if request.method == "GET":
        return render(request, "accounts/register.html")

    payload = parse_json_body(request)
    form = RegistrationForm(payload if payload is not None else request.POST)
    if not form.is_valid():
        errors = {k: v[0] for k, v in form.errors.items()}
        return JsonResponse({"message": "Invalid registration data", "errors": errors}, status=400)

    user = User.objects.create_user(
        username=form.cleaned_data["username"],
        email=form.cleaned_data["email"],
        password=form.cleaned_data["password"],
    )
    profile = get_or_create_security_profile(user)
    profile.full_name = form.cleaned_data["full_name"]
    profile.phone_number = form.cleaned_data["phone_number"]
    profile.save(update_fields=["full_name", "phone_number"])
    return JsonResponse({"message": "Account Successfully Created"}, status=201)


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest):
    if request.method == "GET":
        return render(request, "accounts/login.html")

    payload = parse_json_body(request)
    form = LoginStepOneForm(payload if payload is not None else request.POST)
    if not form.is_valid():
        return JsonResponse({"message": "Invalid login payload", "errors": form.errors}, status=400)

    username = form.cleaned_data["username"].strip()
    password = form.cleaned_data["password"]
    user = User.objects.filter(username__iexact=username).first()

    if not user:
        return JsonResponse({"message": "Invalid credentials"}, status=401)

    authenticated_user = authenticate(request, username=user.username, password=password)
    if not authenticated_user:
        return JsonResponse({"message": "Invalid credentials"}, status=401)

    security_profile = get_or_create_security_profile(authenticated_user)
    if security_profile.two_factor_enabled:
        token = TWO_FA_SIGNER.sign(str(authenticated_user.pk))
        request.session["pre_2fa_user_id"] = authenticated_user.pk
        return JsonResponse({"require_2fa": True, "token": token, "message": "2FA required"})

    auth_login(request, authenticated_user)
    return JsonResponse({"message": "Login successful"})


@require_http_methods(["GET", "POST"])
def login_2fa_view(request: HttpRequest):
    if request.method == "GET":
        return render(request, "accounts/login_2fa.html")

    payload = parse_json_body(request)
    form = LoginStepTwoForm(payload if payload is not None else request.POST)
    if not form.is_valid():
        return JsonResponse({"message": "Invalid 2FA payload", "errors": form.errors}, status=400)

    token = form.cleaned_data["token"]
    secret_word = form.cleaned_data["secret_word"]

    try:
        token_user_id = int(TWO_FA_SIGNER.unsign(token, max_age=300))
    except signing.BadSignature:
        return JsonResponse({"message": "Invalid or expired 2FA token"}, status=400)

    session_user_id = request.session.get("pre_2fa_user_id")
    if session_user_id != token_user_id:
        return JsonResponse({"message": "2FA session mismatch"}, status=400)

    user = User.objects.filter(pk=token_user_id).first()
    if not user:
        return JsonResponse({"message": "User not found"}, status=404)

    security_profile = get_or_create_security_profile(user)
    if not security_profile.verify_secret_word(secret_word):
        return JsonResponse({"message": "Invalid secret word"}, status=401)

    auth_login(request, user)
    request.session.pop("pre_2fa_user_id", None)
    return JsonResponse({"message": "2FA verification successful"})


@require_http_methods(["POST"])
def login_support_view(request: HttpRequest):
    payload = parse_json_body(request)
    form = SupportRequestForm(payload if payload is not None else request.POST)
    if not form.is_valid():
        errors = {k: v[0] for k, v in form.errors.items()}
        return JsonResponse({"message": "Support request failed", "errors": errors}, status=400)

    support = SupportRequest.objects.create(
        subject=form.cleaned_data.get("subject", ""),
        email=form.cleaned_data["email"],
        message=form.cleaned_data["message"],
    )
    return JsonResponse(
        {
            "message": "Your support message has been sent. Our admins will contact you soon.",
            "support_request_id": support.id,
        },
        status=201,
    )


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request: HttpRequest):
    profile = get_or_create_security_profile(request.user)

    if request.method == "GET":
        now = timezone.localtime()
        today = timezone.localdate()
        user_bookings_qs = (
            Booking.objects.filter(user=request.user)
            .select_related("salon", "service")
            .order_by("booking_date", "start_time")
        )
        user_bookings = list(user_bookings_qs)

        def _as_dt(item: Booking):
            return timezone.make_aware(datetime.combine(item.booking_date, item.start_time), timezone.get_current_timezone())

        active_statuses = {Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED}
        upcoming_bookings = [
            booking
            for booking in user_bookings
            if booking.status in active_statuses and _as_dt(booking) >= now
        ]
        history_bookings = [
            booking
            for booking in user_bookings
            if booking.status not in active_statuses or _as_dt(booking) < now
        ]
        history_bookings.sort(key=_as_dt, reverse=True)

        this_year_bookings = [booking for booking in user_bookings if booking.booking_date.year == today.year]
        unique_salon_ids = {booking.salon_id for booking in user_bookings}

        # Derived favorites: most frequently booked salons for this user.
        favorite_counts = Counter(booking.salon_id for booking in user_bookings)
        favorite_items = []
        for salon_id, _count in favorite_counts.most_common(4):
            sample = next((booking for booking in user_bookings if booking.salon_id == salon_id), None)
            if sample:
                favorite_items.append(sample)

        confirmed_bookings = [
            booking for booking in user_bookings if booking.status == Booking.STATUS_CONFIRMED
        ]
        loyalty_points = Decimal(len(confirmed_bookings)) * POINTS_PER_CONFIRMED_BOOKING
        membership_level = _membership_level(loyalty_points)

        tier_thresholds = {
            "Bronze": Decimal("1000"),
            "Silver": Decimal("2000"),
            "Gold": Decimal("3000"),
            "Platinum": Decimal("4000"),
            "Diamond": Decimal("5000"),
            "Elite": Decimal("7001"),
            "Royal": Decimal("7001"),
        }
        next_tier_points = tier_thresholds.get(membership_level, Decimal("7001"))
        if membership_level == "Royal":
            points_remaining = Decimal("0")
            progress_percent = 100
        else:
            points_remaining = max(next_tier_points - loyalty_points, Decimal("0"))
            progress_percent = min(int((loyalty_points / next_tier_points) * 100), 100) if next_tier_points else 0

        try:
            avg_rating = Review.objects.filter(user=request.user).aggregate(avg=Avg("rating"))["avg"]
        except (OperationalError, ProgrammingError):
            # Handles temporarily out-of-sync DB schema (e.g., pending migrations).
            avg_rating = None
        avg_rating_display = f"{avg_rating:.1f}" if avg_rating is not None else "0.0"
        context = {
            "two_factor_enabled": profile.two_factor_enabled,
            "full_name": profile.full_name or request.user.username,
            "username": request.user.username,
            "email": request.user.email,
            "phone_number": profile.phone_number,
            "location": profile.location,
            "profile_image_url": profile.profile_image.url if profile.profile_image else None,
            "member_since": request.user.date_joined,
            "upcoming_bookings": upcoming_bookings[:3],
            "history_bookings": history_bookings[:4],
            "favorite_items": favorite_items,
            "total_bookings": len(user_bookings),
            "bookings_this_year": len(this_year_bookings),
            "favorite_salon_count": len(unique_salon_ids),
            "avg_rating_display": avg_rating_display,
            "loyalty_points": f"{loyalty_points:.1f}",
            "membership_level": membership_level,
            "next_tier_points": next_tier_points,
            "points_remaining": int(points_remaining),
            "progress_percent": progress_percent,
        }
        if _is_json_request(request):
            json_payload = {
                "two_factor_enabled": profile.two_factor_enabled,
                "full_name": profile.full_name or request.user.username,
                "username": request.user.username,
                "email": request.user.email,
                "phone_number": profile.phone_number,
                "location": profile.location,
                "member_since": request.user.date_joined.date().isoformat(),
                "total_bookings": len(user_bookings),
                "bookings_this_year": len(this_year_bookings),
                "favorite_salon_count": len(unique_salon_ids),
                "avg_rating_display": avg_rating_display,
                "loyalty_points": f"{loyalty_points:.1f}",
                "membership_level": membership_level,
                "next_tier_points": next_tier_points,
                "points_remaining": int(points_remaining),
                "progress_percent": progress_percent,
                "upcoming_bookings": [
                    {
                        "salon": booking.salon.name,
                        "service": booking.service.name,
                        "booking_date": booking.booking_date.isoformat(),
                        "start_time": booking.start_time.strftime("%H:%M"),
                        "status": booking.status,
                    }
                    for booking in upcoming_bookings[:3]
                ],
            }
            return JsonResponse(json_payload)
        return render(request, "accounts/profile.html", context)

    payload = parse_json_body(request)
    form = TwoFactorUpdateForm(payload if payload is not None else request.POST, user=request.user)
    if not form.is_valid():
        errors = {k: v[0] for k, v in form.errors.items()}
        return JsonResponse({"message": "Invalid profile update", "errors": errors}, status=400)

    enable_2fa = form.cleaned_data["enabled"]
    secret_word = (form.cleaned_data.get("secret_word") or "").strip()

    # Always require current password for toggling 2FA status.
    profile.two_factor_enabled = enable_2fa
    if enable_2fa:
        profile.set_secret_word(secret_word)
    else:
        profile.two_factor_secret_hash = ""
    profile.save(update_fields=["two_factor_enabled", "two_factor_secret_hash"])

    return JsonResponse({"message": "Security settings updated", "two_factor_enabled": profile.two_factor_enabled})


@login_required
def logout_view(request: HttpRequest):
    auth_logout(request)
    messages.success(request, "Logged out")
    return redirect("login")


@login_required
@require_http_methods(["POST"])
def account_delete_view(request: HttpRequest):
    payload = parse_json_body(request)
    form = AccountDeleteForm(payload if payload is not None else request.POST, user=request.user)
    if not form.is_valid():
        errors = {k: v[0] for k, v in form.errors.items()}
        return JsonResponse({"message": "Account deletion failed", "errors": errors}, status=400)

    request.user.delete()
    auth_logout(request)
    return JsonResponse({"message": "Your account has been deleted.", "redirect": "/login/"}, status=200)


@login_required
@require_http_methods(["POST"])
def profile_password_change_view(request: HttpRequest):
    payload = parse_json_body(request)
    form = PasswordChangeForm(payload if payload is not None else request.POST, user=request.user)
    if not form.is_valid():
        errors = {k: v[0] for k, v in form.errors.items()}
        return JsonResponse({"message": "Password change failed", "errors": errors}, status=400)

    request.user.set_password(form.cleaned_data["new_password"])
    request.user.save(update_fields=["password"])
    auth_login(request, request.user)

    return JsonResponse({"message": "Password changed successfully."}, status=200)


@login_required
@require_http_methods(["POST"])
def profile_update_view(request: HttpRequest):
    profile = get_or_create_security_profile(request.user)
    form = ProfileUpdateForm(request.POST, request.FILES, user=request.user)
    if not form.is_valid():
        errors = {k: v[0] for k, v in form.errors.items()}
        return JsonResponse({"message": "Profile update failed", "errors": errors}, status=400)

    profile.full_name = form.cleaned_data["full_name"]
    profile.location = form.cleaned_data.get("location") or ""
    profile.phone_number = form.cleaned_data.get("phone_number") or ""
    if form.cleaned_data.get("profile_image"):
        profile.profile_image = form.cleaned_data["profile_image"]

    profile.save(update_fields=["full_name", "location", "phone_number", "profile_image"])
    return JsonResponse(
        {
            "message": "Profile updated successfully.",
            "full_name": profile.full_name,
            "location": profile.location,
            "phone_number": profile.phone_number,
            "profile_image_url": profile.profile_image.url if profile.profile_image else "",
        }
    )


@login_required
@require_http_methods(["POST"])
def profile_photo_update_view(request: HttpRequest):
    profile = get_or_create_security_profile(request.user)
    form = ProfileImageUpdateForm(request.POST, request.FILES)
    if not form.is_valid():
        errors = {k: v[0] for k, v in form.errors.items()}
        return JsonResponse({"message": "Profile photo update failed", "errors": errors}, status=400)

    profile.profile_image = form.cleaned_data["profile_image"]
    profile.save(update_fields=["profile_image"])

    return JsonResponse(
        {
            "message": "Profile photo updated successfully.",
            "profile_image_url": profile.profile_image.url if profile.profile_image else "",
        }
    )
