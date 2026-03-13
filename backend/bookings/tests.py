from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, TestCase

from salons.models import Employee, Salon, Service

from .models import Booking
from .views import _availability_payload

User = get_user_model()


class BookingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="booker", password="StrongPass123")
        self.salon = Salon.objects.create(
            name="Nova Studio",
            address="Central Ave",
            description="Test salon",
            opening_hours={"monday": "09:00-10:00"},
        )
        self.service = Service.objects.create(
            salon=self.salon,
            name="Haircut",
            duration_minutes=30,
            price="25.00",
            category="Hair",
        )
        self.employee = Employee.objects.create(salon=self.salon, full_name="Sarah Johnson", role="Stylist")

    def test_booking_uniqueness_constraint(self):
        Booking.objects.create(
            user=self.user,
            salon=self.salon,
            service=self.service,
            employee=self.employee,
            booking_date=date(2026, 3, 16),
            start_time=time(9, 0),
        )
        with self.assertRaises(IntegrityError):
            Booking.objects.create(
                user=self.user,
                salon=self.salon,
                service=self.service,
                employee=self.employee,
                booking_date=date(2026, 3, 16),
                start_time=time(9, 0),
            )

    def test_detect_fully_booked_day(self):
        Booking.objects.create(
            user=self.user,
            salon=self.salon,
            service=self.service,
            employee=self.employee,
            booking_date=date(2026, 3, 16),
            start_time=time(9, 0),
        )
        Booking.objects.create(
            user=self.user,
            salon=self.salon,
            service=self.service,
            employee=self.employee,
            booking_date=date(2026, 3, 16),
            start_time=time(9, 30),
        )
        payload = _availability_payload(self.salon, date(2026, 3, 16))
        self.assertTrue(payload["fully_booked"])


class BookingCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="apiuser", password="StrongPass123")
        self.client.login(username="apiuser", password="StrongPass123")
        self.salon = Salon.objects.create(
            name="Mia Beauty",
            address="Rose Street",
            description="-",
            opening_hours={"monday": "09:00-11:00"},
        )
        self.service = Service.objects.create(
            salon=self.salon,
            name="Manicure",
            duration_minutes=30,
            price="20.00",
            category="Nails",
        )
        self.employee = Employee.objects.create(salon=self.salon, full_name="Emily Chen", role="Nail Artist")

    def test_booking_create_endpoint(self):
        response = self.client.post(
            f"/booking/{self.salon.id}/create/",
            {
                "service": self.service.id,
                "employee": self.employee.id,
                "booking_date": "2026-03-16",
                "start_time": "09:30",
                "notes": "Window side seat",
            },
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(Booking.objects.count(), 0)

    def test_payment_submit_creates_booking(self):
        prepare = self.client.post(
            f"/booking/{self.salon.id}/create/",
            {
                "service": self.service.id,
                "employee": self.employee.id,
                "booking_date": "2026-03-16",
                "start_time": "09:30",
                "notes": "Window side seat",
            },
        )
        self.assertEqual(prepare.status_code, 202)

        response = self.client.post(
            "/payment/submit/",
            {
                "payment_receipt": SimpleUploadedFile("receipt.jpg", b"image", content_type="image/jpeg"),
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Booking.objects.count(), 1)


class BookingLifecycleActionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="lifecycle", password="StrongPass123")
        self.other_user = User.objects.create_user(username="someoneelse", password="StrongPass123")
        self.client.login(username="lifecycle", password="StrongPass123")
        self.salon = Salon.objects.create(
            name="Flow Salon",
            address="One Street",
            description="-",
            opening_hours={"monday": "09:00-11:00"},
        )
        self.service = Service.objects.create(
            salon=self.salon,
            name="Style",
            duration_minutes=30,
            price="30.00",
            category="Hair",
        )
        self.employee = Employee.objects.create(salon=self.salon, full_name="Diana", role="Stylist")

    def test_cancel_booking_updates_status(self):
        booking = Booking.objects.create(
            user=self.user,
            salon=self.salon,
            service=self.service,
            employee=self.employee,
            booking_date=date(2099, 3, 16),
            start_time=time(9, 0),
            status=Booking.STATUS_CONFIRMED,
        )

        response = self.client.post(f"/booking/{booking.id}/cancel/")
        self.assertEqual(response.status_code, 200)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.STATUS_CANCELLED)

    def test_cancel_booking_disallows_other_user(self):
        booking = Booking.objects.create(
            user=self.other_user,
            salon=self.salon,
            service=self.service,
            employee=self.employee,
            booking_date=date(2099, 3, 16),
            start_time=time(9, 0),
        )

        response = self.client.post(f"/booking/{booking.id}/cancel/")
        self.assertEqual(response.status_code, 404)

    def test_reschedule_booking_updates_date_and_time(self):
        booking = Booking.objects.create(
            user=self.user,
            salon=self.salon,
            service=self.service,
            employee=self.employee,
            booking_date=date(2099, 3, 16),
            start_time=time(9, 0),
        )

        response = self.client.post(
            f"/booking/{booking.id}/reschedule/",
            {
                "service": self.service.id,
                "employee": self.employee.id,
                "booking_date": "2099-03-16",
                "start_time": "10:00",
                "notes": "Updated slot",
            },
        )
        self.assertEqual(response.status_code, 200)

        booking.refresh_from_db()
        self.assertEqual(booking.start_time, time(10, 0))
        self.assertEqual(booking.notes, "Updated slot")

    def test_reschedule_booking_rejects_taken_slot(self):
        booking = Booking.objects.create(
            user=self.user,
            salon=self.salon,
            service=self.service,
            employee=self.employee,
            booking_date=date(2099, 3, 16),
            start_time=time(9, 0),
        )
        Booking.objects.create(
            user=self.other_user,
            salon=self.salon,
            service=self.service,
            employee=self.employee,
            booking_date=date(2099, 3, 16),
            start_time=time(10, 0),
        )

        response = self.client.post(
            f"/booking/{booking.id}/reschedule/",
            {
                "service": self.service.id,
                "employee": self.employee.id,
                "booking_date": "2099-03-16",
                "start_time": "10:00",
            },
        )
        self.assertEqual(response.status_code, 409)
