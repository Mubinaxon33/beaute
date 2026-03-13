from django.contrib.auth import get_user_model
from django.test import TestCase

from .admin import SalonAdminForm
from .models import Review, Salon

User = get_user_model()


class SalonsRatingTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="reviewer", email="r@example.com", password="StrongPass123")
		self.salon = Salon.objects.create(
			name="Rated Salon",
			address="Downtown",
			description="Great services",
			opening_hours={"monday": "09:00-18:00"},
		)
		Review.objects.create(user=self.user, salon=self.salon, rating=4, comment="Nice")
		Review.objects.create(user=self.user, salon=self.salon, rating=5, comment="Excellent")

	def test_salons_list_json_contains_aggregated_rating(self):
		response = self.client.get("/salons/?format=json", HTTP_ACCEPT="application/json")
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		target = next(item for item in payload if item["id"] == self.salon.id)
		self.assertEqual(target["avg_rating"], "4.5")
		self.assertEqual(target["review_count"], 2)

	def test_salons_list_json_exposes_unique_main_image_per_salon(self):
		second = Salon.objects.create(
			name="Second Salon",
			address="Uptown",
			description="Another",
			opening_hours={"monday": "09:00-18:00"},
		)
		self.salon.image = "salon_images/2026/03/first.jpg"
		self.salon.save(update_fields=["image"])
		second.image = "salon_images/2026/03/second.jpg"
		second.save(update_fields=["image"])

		response = self.client.get("/salons/?format=json", HTTP_ACCEPT="application/json")
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		first_item = next(item for item in payload if item["id"] == self.salon.id)
		second_item = next(item for item in payload if item["id"] == second.id)

		self.assertIn("first.jpg", first_item["image"])
		self.assertIn("second.jpg", second_item["image"])
		self.assertNotEqual(first_item["image"], second_item["image"])

	def test_salon_detail_json_contains_aggregated_rating(self):
		response = self.client.get(f"/salon/{self.salon.id}/?format=json", HTTP_ACCEPT="application/json")
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload["avg_rating"], "4.5")
		self.assertEqual(payload["review_count"], 2)

	def test_manual_rating_from_admin_overrides_aggregated_rating(self):
		self.salon.category = "spa"
		self.salon.rating = "5.0"
		self.salon.phone_number = "+1 (555) 000-1111"
		self.salon.email = "rated@example.com"
		self.salon.working_hours = "Mon-Sun: 08:00 AM - 10:00 PM"
		self.salon.save()

		response = self.client.get(f"/salon/{self.salon.id}/?format=json", HTTP_ACCEPT="application/json")
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload["avg_rating"], "5.0")
		self.assertEqual(payload["category"], "spa")
		self.assertEqual(payload["category_display"], "Spa")
		self.assertEqual(payload["phone_number"], "+1 (555) 000-1111")
		self.assertEqual(payload["email"], "rated@example.com")
		self.assertEqual(payload["working_hours"], "Mon-Sun: 08:00 AM - 10:00 PM")


class StructuredHoursAdminFormTests(TestCase):
	def test_structured_hours_persist_on_save(self):
		salon = Salon.objects.create(
			name="Hours Salon",
			address="City Center",
			description="Testing structured hours",
			opening_hours={"monday": "09:00-17:00"},
		)

		form = SalonAdminForm(
			data={
				"name": salon.name,
				"category": salon.category,
				"rating": "",
				"address": salon.address,
				"phone_number": "",
				"email": "",
				"description": salon.description,
				"opening_hours": "{}",
				"monday_open": "10:00",
				"monday_close": "18:00",
				"tuesday_open": "09:30",
				"tuesday_close": "16:30",
				"wednesday_open": "",
				"wednesday_close": "",
				"thursday_open": "",
				"thursday_close": "",
				"friday_open": "",
				"friday_close": "",
				"saturday_open": "",
				"saturday_close": "",
				"sunday_open": "",
				"sunday_close": "",
			},
			instance=salon,
		)

		self.assertTrue(form.is_valid(), form.errors)
		saved = form.save()
		saved.refresh_from_db()

		self.assertEqual(saved.opening_hours.get("monday"), "10:00-18:00")
		self.assertEqual(saved.opening_hours.get("tuesday"), "09:30-16:30")
		self.assertIn("Mon: 10:00-18:00", saved.working_hours)
		self.assertIn("Tue: 09:30-16:30", saved.working_hours)


class SalonReviewFlowTests(TestCase):
	def setUp(self):
		self.client = self.client_class()
		self.user = User.objects.create_user(username="reviewuser", email="u@example.com", password="StrongPass123")
		self.salon = Salon.objects.create(
			name="Review Salon",
			address="Center",
			description="Review target",
			opening_hours={"monday": "09:00-18:00"},
		)

	def test_logged_in_user_can_submit_review(self):
		self.client.login(username="reviewuser", password="StrongPass123")
		response = self.client.post(
			f"/salon/{self.salon.id}/reviews/",
			{"rating": "5", "comment": "Amazing service"},
			HTTP_ACCEPT="application/json",
		)
		self.assertEqual(response.status_code, 201)
		self.assertEqual(Review.objects.filter(salon=self.salon).count(), 1)

	def test_html_review_submit_redirects_back_to_salon_detail(self):
		self.client.login(username="reviewuser", password="StrongPass123")
		response = self.client.post(
			f"/salon/{self.salon.id}/reviews/",
			{"rating": "5", "comment": "Great place"},
		)
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response["Location"], f"/salon/{self.salon.id}/")
		self.assertEqual(Review.objects.filter(salon=self.salon).count(), 1)

	def test_review_submission_requires_authentication(self):
		response = self.client.post(
			f"/salon/{self.salon.id}/reviews/",
			{"rating": "4", "comment": "Good"},
			HTTP_ACCEPT="application/json",
		)
		self.assertEqual(response.status_code, 401)

	def test_salon_detail_json_includes_reviews(self):
		Review.objects.create(user=self.user, salon=self.salon, rating=4, comment="Nice and clean")
		response = self.client.get(f"/salon/{self.salon.id}/?format=json", HTTP_ACCEPT="application/json")
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(isinstance(payload.get("reviews"), list))
		self.assertEqual(payload["reviews"][0]["comment"], "Nice and clean")
