from django.urls import path

from .views import (
    booking_cancel_view,
    booking_create_view,
    booking_landing_view,
    booking_page_view,
    booking_reschedule_view,
    payment_page_view,
    payment_submit_view,
    salon_availability_api,
)

urlpatterns = [
    path("booking/", booking_landing_view, name="booking-landing"),
    path("booking/<int:salon_id>/", booking_page_view, name="booking-page"),
    path("payment/", payment_page_view, name="payment-page"),
    path("payment/submit/", payment_submit_view, name="payment-submit"),
    path("booking/<int:salon_id>/create/", booking_create_view, name="booking-create"),
    path("booking/<int:booking_id>/cancel/", booking_cancel_view, name="booking-cancel"),
    path("booking/<int:booking_id>/reschedule/", booking_reschedule_view, name="booking-reschedule"),
    path("api/salon/<int:salon_id>/availability/", salon_availability_api, name="salon-availability"),
]
