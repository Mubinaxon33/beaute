from datetime import date, datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from salons.models import Employee, Salon, Service


def payment_upload_path(instance, filename):
    now = datetime.now()
    return f"payments/{now.year}/{now.month:02d}/{filename}"


class Booking(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="bookings")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="bookings")
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, related_name="bookings", null=True, blank=True)
    booking_date = models.DateField()
    start_time = models.TimeField()
    notes = models.TextField(blank=True)
    payment_receipt = models.FileField(upload_to=payment_upload_path, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["salon", "booking_date", "start_time"], name="uniq_salon_date_start_slot")
        ]
        ordering = ["booking_date", "start_time"]

    def __str__(self):
        return f"{self.user} - {self.salon} - {self.booking_date} {self.start_time}"


class PaymentReceipt(Booking):
    class Meta:
        proxy = True
        verbose_name = "Payment Receipt"
        verbose_name_plural = "Payment Receipts"


def get_day_key(target_date: date) -> str:
    return target_date.strftime("%A").lower()


def generate_slots_for_day(salon: Salon, target_date: date, interval_minutes: int = 30):
    day_key = get_day_key(target_date)
    value = salon.opening_hours.get(day_key)
    if not value or "-" not in value:
        return []

    start_str, end_str = value.split("-", 1)
    opening = datetime.combine(target_date, time.fromisoformat(start_str.strip()))
    closing = datetime.combine(target_date, time.fromisoformat(end_str.strip()))

    slots = []
    current = opening
    while current < closing:
        slots.append(current.time())
        current += timedelta(minutes=interval_minutes)
    return slots


def validate_receipt_file(file_obj):
    allowed_ext = {".jpg", ".jpeg", ".png", ".pdf"}
    ext = Path(file_obj.name).suffix.lower()
    if ext not in allowed_ext:
        raise ValidationError("Only JPG, PNG, and PDF files are allowed.")
    if file_obj.size > 10 * 1024 * 1024:
        raise ValidationError("File size must be 10MB or less.")
