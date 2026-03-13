import json
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

from .models import UserSecurityProfile

User = get_user_model()

ALLOWED_PROFILE_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_PROFILE_IMAGE_SIZE = 5 * 1024 * 1024


def _validate_profile_image(profile_image):
    if not profile_image:
        return profile_image

    file_name = profile_image.name.lower()
    is_valid_ext = any(file_name.endswith(ext) for ext in ALLOWED_PROFILE_IMAGE_EXTENSIONS)
    if not is_valid_ext:
        raise forms.ValidationError("Only JPG, JPEG, and PNG images are allowed.")

    if profile_image.size > MAX_PROFILE_IMAGE_SIZE:
        raise forms.ValidationError("Profile image must be 5MB or less.")
    return profile_image


class RegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=255)
    email = forms.EmailField(max_length=255)
    username = forms.CharField(max_length=150)
    phone_number = forms.CharField(max_length=20)
    password = forms.CharField(min_length=8, widget=forms.PasswordInput)
    confirm_password = forms.CharField(min_length=8, widget=forms.PasswordInput)

    PHONE_REGEX = re.compile(r"^\+998 \(\d{2}\)-\d{3}-\d{2}-\d{2}$")
    STRONG_PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$")

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"].strip()
        if not full_name:
            raise forms.ValidationError("Full name is required.")
        return full_name

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already in use.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already in use.")
        return username

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"].strip()
        if not self.PHONE_REGEX.match(phone_number):
            raise forms.ValidationError("Phone must match +998 (XX)-XXX-XX-XX.")
        if UserSecurityProfile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("Phone number already in use.")
        return phone_number

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.STRONG_PASSWORD_REGEX.match(password):
            raise forms.ValidationError(
                "Password must contain uppercase, lowercase, number, special character, and be at least 8 characters."
            )
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data


class LoginStepOneForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class LoginStepTwoForm(forms.Form):
    token = forms.CharField()
    secret_word = forms.CharField(max_length=255)


class SupportRequestForm(forms.Form):
    subject = forms.CharField(max_length=200, required=False)
    email = forms.EmailField(max_length=255)
    message = forms.CharField(min_length=5, widget=forms.Textarea)

    def clean_subject(self):
        return (self.cleaned_data.get("subject") or "").strip()

    def clean_message(self):
        message = (self.cleaned_data.get("message") or "").strip()
        if len(message) < 5:
            raise forms.ValidationError("Message must be at least 5 characters.")
        return message


class TwoFactorUpdateForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    enabled = forms.BooleanField(required=False)
    secret_word = forms.CharField(required=False, max_length=255)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        current_password = self.cleaned_data["current_password"]
        if not check_password(current_password, self.user.password):
            raise forms.ValidationError("Current password is incorrect.")
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        enabled = cleaned_data.get("enabled")
        secret_word = (cleaned_data.get("secret_word") or "").strip()
        if enabled and not secret_word:
            self.add_error("secret_word", "Secret word is required when enabling 2FA.")
        return cleaned_data


class AccountDeleteForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        current_password = self.cleaned_data["current_password"]
        if not check_password(current_password, self.user.password):
            raise forms.ValidationError("Current password is incorrect.")
        return current_password


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(min_length=8, widget=forms.PasswordInput)
    confirm_new_password = forms.CharField(min_length=8, widget=forms.PasswordInput)

    STRONG_PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        current_password = self.cleaned_data["current_password"]
        if not check_password(current_password, self.user.password):
            raise forms.ValidationError("Current password is incorrect.")
        return current_password

    def clean_new_password(self):
        new_password = self.cleaned_data["new_password"]
        if not self.STRONG_PASSWORD_REGEX.match(new_password):
            raise forms.ValidationError(
                "New password must contain uppercase, lowercase, number, special character, and be at least 8 characters."
            )
        return new_password

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get("current_password")
        new_password = cleaned_data.get("new_password")
        confirm_new_password = cleaned_data.get("confirm_new_password")

        if new_password and confirm_new_password and new_password != confirm_new_password:
            self.add_error("confirm_new_password", "New passwords do not match.")

        if current_password and new_password and current_password == new_password:
            self.add_error("new_password", "New password must be different from current password.")

        return cleaned_data


class ProfileUpdateForm(forms.Form):
    full_name = forms.CharField(max_length=255)
    location = forms.CharField(max_length=255, required=False)
    phone_number = forms.CharField(max_length=20, required=False)
    profile_image = forms.FileField(required=False)

    PHONE_REGEX = re.compile(r"^\+998 \(\d{2}\)-\d{3}-\d{2}-\d{2}$")
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"].strip()
        if not full_name:
            raise forms.ValidationError("Full name is required.")
        return full_name

    def clean_location(self):
        return (self.cleaned_data.get("location") or "").strip()

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if not phone_number:
            return phone_number
        if not self.PHONE_REGEX.match(phone_number):
            raise forms.ValidationError("Phone must match +998 (XX)-XXX-XX-XX.")

        exists = UserSecurityProfile.objects.filter(phone_number=phone_number)
        if self.user:
            exists = exists.exclude(user=self.user)
        if exists.exists():
            raise forms.ValidationError("Phone number already in use.")
        return phone_number

    def clean_profile_image(self):
        profile_image = self.cleaned_data.get("profile_image")
        return _validate_profile_image(profile_image)


class ProfileImageUpdateForm(forms.Form):
    profile_image = forms.FileField(required=True)

    def clean_profile_image(self):
        profile_image = self.cleaned_data.get("profile_image")
        return _validate_profile_image(profile_image)


def parse_json_body(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}
    return None


def get_or_create_security_profile(user):
    profile, _ = UserSecurityProfile.objects.get_or_create(user=user)
    return profile
