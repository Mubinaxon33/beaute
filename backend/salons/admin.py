from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .models import Employee, Review, Salon, SalonPhoto, Service


WEEKDAYS = [
    ("monday", "Monday"),
    ("tuesday", "Tuesday"),
    ("wednesday", "Wednesday"),
    ("thursday", "Thursday"),
    ("friday", "Friday"),
    ("saturday", "Saturday"),
    ("sunday", "Sunday"),
]


class SalonAdminForm(forms.ModelForm):
    # Structured day-by-day editor for opening hours.
    monday_open = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    monday_close = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    tuesday_open = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    tuesday_close = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    wednesday_open = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    wednesday_close = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    thursday_open = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    thursday_close = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    friday_open = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    friday_close = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    saturday_open = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    saturday_close = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    sunday_open = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    sunday_close = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))

    class Meta:
        model = Salon
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "opening_hours" in self.fields:
            self.fields["opening_hours"].required = False
        if "working_hours" in self.fields:
            self.fields["working_hours"].required = False
        if "image" in self.fields:
            self.fields["image"].label = "Main Photo"
            self.fields["image"].help_text = "Shown on home page and salon cards for this specific salon."

        opening_hours = (self.instance.opening_hours or {}) if self.instance and self.instance.pk else {}
        for day, _label in WEEKDAYS:
            slot = opening_hours.get(day, "")
            if "-" not in slot:
                continue
            start, end = slot.split("-", 1)
            self.initial[f"{day}_open"] = start
            self.initial[f"{day}_close"] = end

    def clean(self):
        cleaned_data = super().clean()
        opening_hours = {}
        summary_parts = []

        for day, label in WEEKDAYS:
            open_key = f"{day}_open"
            close_key = f"{day}_close"
            open_time = cleaned_data.get(open_key)
            close_time = cleaned_data.get(close_key)

            if bool(open_time) ^ bool(close_time):
                raise ValidationError(f"Please provide both opening and closing time for {label}.")

            if open_time and close_time:
                open_str = open_time.strftime("%H:%M")
                close_str = close_time.strftime("%H:%M")
                opening_hours[day] = f"{open_str}-{close_str}"
                summary_parts.append(f"{label[:3]}: {open_str}-{close_str}")

        working_hours = ", ".join(summary_parts)
        # These fields are not editable directly in fieldsets, so persist through instance assignment.
        self.instance.opening_hours = opening_hours
        self.instance.working_hours = working_hours
        cleaned_data["opening_hours"] = opening_hours
        cleaned_data["working_hours"] = working_hours
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.opening_hours = self.instance.opening_hours
        instance.working_hours = self.instance.working_hours
        if commit:
            instance.save()
        return instance


class SalonPhotoInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        active_rows = 0
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            if form.cleaned_data.get("image"):
                active_rows += 1

        if active_rows != 3:
            raise ValidationError("Each salon must have exactly 3 photos.")


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1


class EmployeeInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        active_rows = 0
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            has_name = bool(form.cleaned_data.get("full_name"))
            is_active = form.cleaned_data.get("is_active", False)
            if has_name and is_active:
                active_rows += 1

        if active_rows < 1:
            raise ValidationError("Each salon must have at least 1 active employee.")


class EmployeeInline(admin.TabularInline):
    model = Employee
    extra = 1
    formset = EmployeeInlineFormSet
    fields = ("full_name", "role", "phone_number", "email", "is_active")


class SalonPhotoInline(admin.TabularInline):
    model = SalonPhoto
    extra = 3
    min_num = 3
    max_num = 3
    validate_min = True
    validate_max = True
    formset = SalonPhotoInlineFormSet
    fields = ("image", "caption", "sort_order")


@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    form = SalonAdminForm
    list_display = ("name", "category", "rating", "address", "phone_number", "email")
    search_fields = ("name", "address", "phone_number", "email")
    list_filter = ("category", "rating")
    inlines = [ServiceInline, EmployeeInline, SalonPhotoInline]
    readonly_fields = ("working_hours_readonly", "main_photo_preview")
    fieldsets = (
        (
            "Salon Details",
            {
                "fields": (
                    "name",
                    "category",
                    "rating",
                    "address",
                    "phone_number",
                    "email",
                    "description",
                    "working_hours_readonly",
                )
            },
        ),
        (
            "Main Photo",
            {
                "fields": ("image", "main_photo_preview"),
                "description": "Upload a unique main photo for this salon.",
            },
        ),
        (
            "Structured Working Hours",
            {
                "fields": (
                    ("monday_open", "monday_close"),
                    ("tuesday_open", "tuesday_close"),
                    ("wednesday_open", "wednesday_close"),
                    ("thursday_open", "thursday_close"),
                    ("friday_open", "friday_close"),
                    ("saturday_open", "saturday_close"),
                    ("sunday_open", "sunday_close"),
                ),
                "description": "Fill day-by-day opening and closing times. Leave both empty if closed.",
            },
        ),
    )

    @admin.display(description="Current Working Hours")
    def working_hours_readonly(self, obj):
        if not obj:
            return "Set hours below"
        return obj.working_hours_display

    @admin.display(description="Current Main Photo")
    def main_photo_preview(self, obj):
        if not obj or not obj.image:
            return "No main photo uploaded"
        return format_html('<img src="{}" alt="{}" style="height:64px;border-radius:8px;object-fit:cover;" />', obj.image.url, obj.name)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "salon", "duration_minutes", "price", "category")
    list_filter = ("category", "salon")
    search_fields = ("name", "salon__name")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "salon", "role", "phone_number", "email", "is_active")
    list_filter = ("salon", "is_active")
    search_fields = ("full_name", "role", "salon__name", "phone_number", "email")


@admin.register(SalonPhoto)
class SalonPhotoAdmin(admin.ModelAdmin):
    list_display = ("salon", "sort_order", "caption")
    list_filter = ("salon",)
    search_fields = ("salon__name", "caption")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("salon", "user", "rating", "created_at")
    list_filter = ("rating", "salon")
    search_fields = ("salon__name", "user__username", "comment")
