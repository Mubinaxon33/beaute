from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class UserSecurityProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="security_profile")
    full_name = models.CharField(max_length=255, blank=True)
    profile_image = models.ImageField(upload_to="profile_images/%Y/%m/", blank=True, null=True)
    phone_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret_hash = models.CharField(max_length=256, blank=True)

    def set_secret_word(self, secret_word: str) -> None:
        self.two_factor_secret_hash = make_password(secret_word)

    def verify_secret_word(self, secret_word: str) -> bool:
        if not self.two_factor_secret_hash:
            return False
        return check_password(secret_word, self.two_factor_secret_hash)

    def __str__(self) -> str:
        return f"Security profile for {self.user.username}"


class SupportRequest(models.Model):
    subject = models.CharField(max_length=200, blank=True)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        subject = self.subject.strip() if self.subject else "No subject"
        return f"{subject} ({self.email})"
