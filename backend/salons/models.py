from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Salon(models.Model):
    CATEGORY_HAIR = "hair"
    CATEGORY_NAILS = "nails"
    CATEGORY_MAKEUP = "makeup"
    CATEGORY_SKINCARE = "skincare"
    CATEGORY_SPA = "spa"
    CATEGORY_CHOICES = [
        (CATEGORY_HAIR, "Hair"),
        (CATEGORY_NAILS, "Nails"),
        (CATEGORY_MAKEUP, "Makeup"),
        (CATEGORY_SKINCARE, "Skincare"),
        (CATEGORY_SPA, "Spa"),
    ]

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_HAIR)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Optional manual rating shown in the UI (0.0-5.0).",
    )
    address = models.CharField(max_length=500)
    working_hours = models.CharField(max_length=255, blank=True, default="")
    phone_number = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    description = models.TextField()
    image = models.ImageField(upload_to="salon_images/%Y/%m/", blank=True, null=True)
    # Example: {"monday": "09:00-18:00", ..., "sunday": "10:00-16:00"}
    opening_hours = models.JSONField(default=dict)

    @property
    def working_hours_display(self) -> str:
        if self.working_hours:
            return self.working_hours
        if not self.opening_hours:
            return "Hours not specified"

        ordered_days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        parts = []
        for day in ordered_days:
            if day in self.opening_hours:
                parts.append(f"{day[:3].title()}: {self.opening_hours[day]}")
        return ", ".join(parts) if parts else "Hours not specified"

    def __str__(self) -> str:
        return self.name


class SalonPhoto(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="salon_gallery/%Y/%m/")
    caption = models.CharField(max_length=150, blank=True, default="")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"Photo {self.id} - {self.salon.name}"


class Employee(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="employees")
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=120, blank=True, default="")
    phone_number = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["full_name", "id"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.salon.name})"


class Service(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=255)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.CharField(max_length=120)

    def __str__(self) -> str:
        return f"{self.name} ({self.salon.name})"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="salon_reviews")
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} -> {self.salon} ({self.rating})"
