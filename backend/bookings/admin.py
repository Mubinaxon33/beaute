from django.contrib import admin
from django.utils.html import format_html

from .models import Booking, PaymentReceipt


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "salon",
        "service",
        "employee",
        "booking_date",
        "start_time",
        "status",
        "payment_receipt",
    )
    list_filter = ("status", "booking_date", "salon")
    search_fields = ("user__username", "user__email", "salon__name")


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "receipt_preview",
        "user",
        "salon",
        "service",
        "employee",
        "booking_date",
        "start_time",
        "status",
        "payment_receipt",
        "created_at",
    )
    list_filter = ("status", "booking_date", "salon")
    search_fields = ("user__username", "user__email", "salon__name")
    ordering = ("-created_at",)
    readonly_fields = ("receipt_preview",)

    @admin.display(description="Receipt Preview")
    def receipt_preview(self, obj):
        if not obj.payment_receipt:
            return "No receipt"

        file_url = obj.payment_receipt.url
        lower_name = obj.payment_receipt.name.lower()
        if lower_name.endswith((".jpg", ".jpeg", ".png")):
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">'
                '<img src="{}" alt="Receipt" style="width:64px;height:64px;object-fit:cover;border-radius:8px;border:1px solid #ddd;" />'
                "</a>",
                file_url,
                file_url,
            )

        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">Open file</a>', file_url)

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(payment_receipt="").exclude(payment_receipt__isnull=True)
