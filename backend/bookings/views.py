from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from django.utils import timezone

from salons.models import Salon

from .forms import BookingCreateForm
from .models import Booking, generate_slots_for_day, validate_receipt_file


PENDING_BOOKING_SESSION_KEY = "pending_booking"


def _booking_datetime_local(booking: Booking):
    return timezone.make_aware(
        datetime.combine(booking.booking_date, booking.start_time),
        timezone.get_current_timezone(),
    )


def _availability_payload(salon: Salon, target_date: date):
    all_slots = generate_slots_for_day(salon, target_date)
    booked_times = set(
        Booking.objects.filter(salon=salon, booking_date=target_date)
        .exclude(status__in=[Booking.STATUS_REJECTED, Booking.STATUS_CANCELLED])
        .values_list("start_time", flat=True)
    )

    available_slots = [
        {"time": slot.strftime("%H:%M"), "available": slot not in booked_times}
        for slot in all_slots
    ]
    fully_booked = bool(all_slots) and all(not item["available"] for item in available_slots)
    return {"available_slots": available_slots, "fully_booked": fully_booked}


@login_required
@require_GET
def booking_landing_view(request):
    return redirect("salons")


@login_required
@require_GET
def booking_page_view(request, salon_id: int):
    salon = get_object_or_404(Salon.objects.prefetch_related("services", "employees"), pk=salon_id)
    context = {"salon": salon, "reschedule_booking": None}

    reschedule_booking_id = request.GET.get("reschedule_booking")
    if reschedule_booking_id:
        booking = Booking.objects.filter(
            pk=reschedule_booking_id,
            user=request.user,
            salon=salon,
        ).first()
        if (
            booking
            and booking.status not in {Booking.STATUS_CANCELLED, Booking.STATUS_REJECTED}
            and _booking_datetime_local(booking) >= timezone.localtime()
        ):
            context["reschedule_booking"] = booking

    return render(request, "bookings/booking.html", context)


@login_required
@require_GET
def payment_page_view(request):
    pending = request.session.get(PENDING_BOOKING_SESSION_KEY)
    summary = None

    if pending:
        salon = Salon.objects.filter(pk=pending.get("salon_id")).first()
        service = None
        employee = None
        if salon:
            service = salon.services.filter(pk=pending.get("service_id")).first()
            employee = salon.employees.filter(pk=pending.get("employee_id")).first()

        booking_date_raw = pending.get("booking_date") or ""
        start_time_raw = pending.get("start_time") or ""
        try:
            booking_date_display = datetime.fromisoformat(booking_date_raw).strftime("%A, %B %d, %Y")
        except ValueError:
            booking_date_display = booking_date_raw or "Not selected"

        try:
            start_time_display = datetime.strptime(start_time_raw, "%H:%M").strftime("%I:%M %p").lstrip("0")
        except ValueError:
            start_time_display = start_time_raw or "Not selected"

        summary = {
            "back_to_booking_url": f"/booking/{salon.id}/" if salon else "/salons/",
            "salon_name": salon.name if salon else "Not selected",
            "service_name": service.name if service else "Not selected",
            "service_price": str(service.price) if service else "0",
            "service_fee": "5.00",
            "total_price": f"{(float(service.price) + 5):.2f}" if service else "5.00",
            "duration": f"{service.duration_minutes} minutes" if service else "Not selected",
            "employee_name": employee.full_name if employee else "Not selected",
            "booking_date": booking_date_display,
            "start_time": start_time_display,
        }

    return render(request, "bookings/payment.html", {"pending_booking": summary})


@require_GET
def salon_availability_api(request, salon_id: int):
    date_value = request.GET.get("date")
    if not date_value:
        return JsonResponse({"message": "date query parameter is required"}, status=400)

    try:
        target_date = date.fromisoformat(date_value)
    except ValueError:
        return JsonResponse({"message": "date must be YYYY-MM-DD"}, status=400)

    salon = Salon.objects.filter(pk=salon_id).first()
    if not salon:
        return JsonResponse({"message": "Salon not found"}, status=404)

    return JsonResponse(_availability_payload(salon, target_date))


@login_required
@require_http_methods(["POST"])
def booking_create_view(request, salon_id: int):
    salon = get_object_or_404(Salon, pk=salon_id)
    form = BookingCreateForm(request.POST, salon=salon)
    if not form.is_valid():
        errors = {field: str(errs[0]) for field, errs in form.errors.items()}
        return JsonResponse({"message": "Invalid booking payload", "errors": errors}, status=400)

    booking_date = form.cleaned_data["booking_date"]
    request.session[PENDING_BOOKING_SESSION_KEY] = {
        "salon_id": salon.id,
        "service_id": form.cleaned_data["service"].id,
        "employee_id": form.cleaned_data["employee"].id,
        "booking_date": booking_date.isoformat(),
        "start_time": form.cleaned_data["start_time"].strftime("%H:%M"),
        "notes": form.cleaned_data.get("notes", ""),
    }
    request.session.modified = True

    availability = _availability_payload(salon, booking_date)
    return JsonResponse(
        {
            "message": "Booking details saved. Continue to payment.",
            "redirect_to": "/payment/",
            "fully_booked": availability["fully_booked"],
        },
        status=202,
    )


@login_required
@require_http_methods(["POST"])
def payment_submit_view(request):
    pending = request.session.get(PENDING_BOOKING_SESSION_KEY)
    if not pending:
        return JsonResponse({"message": "No pending booking found. Please book first."}, status=400)

    receipt = request.FILES.get("payment_receipt")
    if not receipt:
        return JsonResponse({"message": "Payment receipt is required."}, status=400)

    try:
        validate_receipt_file(receipt)
    except Exception as error:
        return JsonResponse({"message": str(error)}, status=400)

    salon = Salon.objects.filter(pk=pending.get("salon_id")).first()
    if not salon:
        return JsonResponse({"message": "Selected salon no longer exists."}, status=400)

    service = salon.services.filter(pk=pending.get("service_id")).first()
    employee = salon.employees.filter(pk=pending.get("employee_id"), is_active=True).first()
    if not service or not employee:
        return JsonResponse({"message": "Selected service or specialist is no longer available."}, status=400)

    try:
        booking_date = date.fromisoformat(pending.get("booking_date", ""))
    except ValueError:
        return JsonResponse({"message": "Invalid booking date in pending request."}, status=400)

    try:
        parsed_time = datetime.strptime(pending.get("start_time", ""), "%H:%M").time()
    except ValueError:
        return JsonResponse({"message": "Invalid booking time in pending request."}, status=400)

    try:
        with transaction.atomic():
            list(Booking.objects.select_for_update().filter(salon=salon, booking_date=booking_date))
            booking = Booking.objects.create(
                user=request.user,
                salon=salon,
                service=service,
                employee=employee,
                booking_date=booking_date,
                start_time=parsed_time,
                notes=pending.get("notes", ""),
                payment_receipt=receipt,
            )
    except IntegrityError:
        return JsonResponse({"message": "This slot has already been booked."}, status=409)

    request.session.pop(PENDING_BOOKING_SESSION_KEY, None)
    request.session.modified = True
    return JsonResponse(
        {
            "message": "Booking created successfully after payment receipt submission.",
            "booking_id": booking.id,
            "redirect_to": "/",
        },
        status=201,
    )


@login_required
@require_http_methods(["POST"])
def booking_cancel_view(request, booking_id: int):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)

    if booking.status in {Booking.STATUS_CANCELLED, Booking.STATUS_REJECTED}:
        return JsonResponse({"message": "This booking has already been closed."}, status=400)

    if _booking_datetime_local(booking) < timezone.localtime():
        return JsonResponse({"message": "Past bookings cannot be cancelled."}, status=400)

    booking.status = Booking.STATUS_CANCELLED
    booking.save(update_fields=["status"])
    return JsonResponse({"message": "Booking cancelled successfully.", "booking_id": booking.id})


@login_required
@require_http_methods(["POST"])
def booking_reschedule_view(request, booking_id: int):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)

    if booking.status in {Booking.STATUS_CANCELLED, Booking.STATUS_REJECTED}:
        return JsonResponse({"message": "This booking cannot be rescheduled."}, status=400)

    if _booking_datetime_local(booking) < timezone.localtime():
        return JsonResponse({"message": "Past bookings cannot be rescheduled."}, status=400)

    form = BookingCreateForm(request.POST, salon=booking.salon)
    if not form.is_valid():
        errors = {field: str(errs[0]) for field, errs in form.errors.items()}
        return JsonResponse({"message": "Invalid reschedule payload", "errors": errors}, status=400)

    booking_date = form.cleaned_data["booking_date"]
    start_time = form.cleaned_data["start_time"]
    target_dt = timezone.make_aware(
        datetime.combine(booking_date, start_time),
        timezone.get_current_timezone(),
    )
    if target_dt < timezone.localtime():
        return JsonResponse({"message": "Please choose a future time slot."}, status=400)

    conflict_exists = (
        Booking.objects.filter(
            salon=booking.salon,
            booking_date=booking_date,
            start_time=start_time,
        )
        .exclude(pk=booking.pk)
        .exclude(status__in=[Booking.STATUS_REJECTED, Booking.STATUS_CANCELLED])
        .exists()
    )
    if conflict_exists:
        return JsonResponse({"message": "This slot has already been booked."}, status=409)

    booking.service = form.cleaned_data["service"]
    booking.employee = form.cleaned_data["employee"]
    booking.booking_date = booking_date
    booking.start_time = start_time
    booking.notes = form.cleaned_data.get("notes", "")
    booking.save(update_fields=["service", "employee", "booking_date", "start_time", "notes"])

    return JsonResponse(
        {
            "message": "Booking rescheduled successfully.",
            "booking_id": booking.id,
            "redirect_to": "/profile/",
        }
    )
