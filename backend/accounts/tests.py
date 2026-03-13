import json
import base64
from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from bookings.models import Booking
from .models import UserSecurityProfile
from salons.models import Review, Salon, Service

User = get_user_model()


class TwoFactorTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="alice", email="alice@example.com", password="StrongPass123")

    def test_enable_disable_two_factor_requires_password_and_hashes_secret(self):
        self.client.login(username="alice", password="StrongPass123")

        response = self.client.post(
            "/profile/",
            data=json.dumps({"current_password": "StrongPass123", "enabled": True, "secret_word": "violet-rain"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        profile = UserSecurityProfile.objects.get(user=self.user)
        self.assertTrue(profile.two_factor_enabled)
        self.assertNotEqual(profile.two_factor_secret_hash, "violet-rain")
        self.assertTrue(profile.verify_secret_word("violet-rain"))

        disable_response = self.client.post(
            "/profile/",
            data=json.dumps({"current_password": "StrongPass123", "enabled": False, "secret_word": ""}),
            content_type="application/json",
        )
        self.assertEqual(disable_response.status_code, 200)
        profile.refresh_from_db()
        self.assertFalse(profile.two_factor_enabled)

    def test_login_flow_with_two_factor(self):
        profile = UserSecurityProfile.objects.create(user=self.user, two_factor_enabled=True)
        profile.set_secret_word("amber")
        profile.save()

        first_step = self.client.post(
            "/login/",
            data=json.dumps({"username": "alice", "password": "StrongPass123"}),
            content_type="application/json",
        )
        self.assertEqual(first_step.status_code, 200)
        payload = first_step.json()
        self.assertTrue(payload["require_2fa"])

        second_step = self.client.post(
            "/login/2fa/",
            data=json.dumps({"token": payload["token"], "secret_word": "amber"}),
            content_type="application/json",
        )
        self.assertEqual(second_step.status_code, 200)


class RegistrationValidationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_registration_requires_strong_password_and_matching_confirm(self):
        weak = self.client.post(
            "/register/",
            data=json.dumps(
                {
                    "full_name": "Weak User",
                    "email": "weak@example.com",
                    "username": "weakuser",
                    "phone_number": "+998 (90)-123-45-67",
                    "password": "weakpass",
                    "confirm_password": "weakpass",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(weak.status_code, 400)

        mismatch = self.client.post(
            "/register/",
            data=json.dumps(
                {
                    "full_name": "Mismatch User",
                    "email": "mismatch@example.com",
                    "username": "mismatchuser",
                    "phone_number": "+998 (91)-123-45-67",
                    "password": "StrongPass1!",
                    "confirm_password": "StrongPass2!",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(mismatch.status_code, 400)

    def test_registration_requires_unique_phone(self):
        first = self.client.post(
            "/register/",
            data=json.dumps(
                {
                    "full_name": "User One",
                    "email": "one@example.com",
                    "username": "userone",
                    "phone_number": "+998 (93)-123-45-67",
                    "password": "StrongPass1!",
                    "confirm_password": "StrongPass1!",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            "/register/",
            data=json.dumps(
                {
                    "full_name": "User Two",
                    "email": "two@example.com",
                    "username": "usertwo",
                    "phone_number": "+998 (93)-123-45-67",
                    "password": "StrongPass1!",
                    "confirm_password": "StrongPass1!",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 400)


class LoginSupportTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_login_support_creates_support_request(self):
        response = self.client.post(
            "/login/support/",
            data=json.dumps(
                {
                    "subject": "Cannot sign in",
                    "email": "help@example.com",
                    "message": "I forgot my password and cannot complete login.",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_login_support_requires_email(self):
        response = self.client.post(
            "/login/support/",
            data=json.dumps(
                {
                    "subject": "Need help",
                    "email": "",
                    "message": "Please contact me.",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class ProfileStatsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="profileuser", email="p@example.com", password="StrongPass123")
        self.salon = Salon.objects.create(
            name="Sample Salon",
            address="Main Street",
            description="Sample",
            opening_hours={"monday": "09:00-18:00"},
        )

    def test_profile_avg_rating_is_computed_from_reviews(self):
        self.client.login(username="profileuser", password="StrongPass123")
        Review.objects.create(user=self.user, salon=self.salon, rating=5, comment="Excellent")
        Review.objects.create(user=self.user, salon=self.salon, rating=3, comment="Good")

        response = self.client.get("/profile/?format=json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["avg_rating_display"], "4.0")


class AccountDeletionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="deleteme", email="d@example.com", password="StrongPass123")

    def test_account_delete_removes_user_and_logs_out(self):
        self.client.login(username="deleteme", password="StrongPass123")
        response = self.client.post(
            "/profile/delete/",
            data=json.dumps({"current_password": "StrongPass123"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="deleteme").exists())

        protected_response = self.client.get("/profile/")
        self.assertEqual(protected_response.status_code, 302)

    def test_account_delete_requires_valid_password(self):
        self.client.login(username="deleteme", password="StrongPass123")
        response = self.client.post(
            "/profile/delete/",
            data=json.dumps({"current_password": "WrongPassword"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(username="deleteme").exists())


class ProfileEnhancementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="enhanced", email="enhanced@example.com", password="StrongPass123")
        self.profile = UserSecurityProfile.objects.create(user=self.user, full_name="Enhanced User")
        self.salon = Salon.objects.create(
            name="Enhance Salon",
            address="City",
            description="Desc",
            opening_hours={"monday": "09:00-18:00"},
        )
        self.service = Service.objects.create(
            salon=self.salon,
            name="Hair Cut",
            duration_minutes=60,
            price="45.00",
            category="Hair",
        )

    def _receipt(self, name="receipt.png"):
        return SimpleUploadedFile(name, b"fake-image-bytes", content_type="image/png")

    def test_membership_and_points_use_confirmed_bookings(self):
        Booking.objects.create(
            user=self.user,
            salon=self.salon,
            service=self.service,
            booking_date=date(2026, 3, 20),
            start_time=time(10, 0),
            payment_receipt=self._receipt("one.png"),
            status=Booking.STATUS_CONFIRMED,
        )
        Booking.objects.create(
            user=self.user,
            salon=self.salon,
            service=self.service,
            booking_date=date(2026, 3, 21),
            start_time=time(11, 0),
            payment_receipt=self._receipt("two.png"),
            status=Booking.STATUS_PENDING,
        )

        self.client.login(username="enhanced", password="StrongPass123")
        response = self.client.get("/profile/?format=json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["loyalty_points"], "87.5")
        self.assertEqual(payload["membership_level"], "Bronze")

    def test_profile_json_contains_member_since(self):
        self.client.login(username="enhanced", password="StrongPass123")
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Member since")

    def test_profile_update_rejects_large_or_invalid_image(self):
        self.client.login(username="enhanced", password="StrongPass123")
        big_file = SimpleUploadedFile("avatar.png", b"a" * (5 * 1024 * 1024 + 10), content_type="image/png")
        bad_ext = SimpleUploadedFile("avatar.gif", b"small", content_type="image/gif")

        large_response = self.client.post(
            "/profile/update/",
            data={"full_name": "Enhanced User", "location": "Tashkent", "profile_image": big_file},
        )
        self.assertEqual(large_response.status_code, 400)

        ext_response = self.client.post(
            "/profile/update/",
            data={"full_name": "Enhanced User", "location": "Tashkent", "profile_image": bad_ext},
        )
        self.assertEqual(ext_response.status_code, 400)

    def test_profile_photo_update_endpoint_accepts_valid_image(self):
        self.client.login(username="enhanced", password="StrongPass123")
        image = SimpleUploadedFile(
            "avatar.png",
            base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5n8f8AAAAASUVORK5CYII="),
            content_type="image/png",
        )

        response = self.client.post("/profile/photo/", data={"profile_image": image})
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertTrue(bool(self.profile.profile_image))

    def test_profile_update_can_change_phone_number(self):
        self.client.login(username="enhanced", password="StrongPass123")
        response = self.client.post(
            "/profile/update/",
            data={
                "full_name": "Enhanced User",
                "location": "Tashkent",
                "phone_number": "+998 (90)-111-22-33",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.phone_number, "+998 (90)-111-22-33")

    def test_profile_password_change_success(self):
        self.client.login(username="enhanced", password="StrongPass123")
        response = self.client.post(
            "/profile/password/",
            data=json.dumps(
                {
                    "current_password": "StrongPass123",
                    "new_password": "StrongerPass1!",
                    "confirm_new_password": "StrongerPass1!",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.client.logout()
        relogin = self.client.login(username="enhanced", password="StrongerPass1!")
        self.assertTrue(relogin)

    def test_profile_password_change_rejects_invalid_current_password(self):
        self.client.login(username="enhanced", password="StrongPass123")
        response = self.client.post(
            "/profile/password/",
            data=json.dumps(
                {
                    "current_password": "WrongCurrent1!",
                    "new_password": "StrongerPass1!",
                    "confirm_new_password": "StrongerPass1!",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
