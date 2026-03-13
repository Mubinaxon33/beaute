from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.html import format_html

from .models import SupportRequest, UserSecurityProfile

User = get_user_model()


class UserSecurityProfileInline(admin.StackedInline):
    model = UserSecurityProfile
    fk_name = "user"
    extra = 0
    max_num = 1
    fields = ("full_name", "profile_image", "profile_image_preview", "phone_number", "location", "two_factor_enabled")
    readonly_fields = ("profile_image_preview",)

    @admin.display(description="Current Profile Picture")
    def profile_image_preview(self, obj):
        if not obj or not obj.profile_image:
            return "No profile picture uploaded"
        return format_html(
            '<img src="{}" alt="profile" style="height:72px;width:72px;border-radius:50%;object-fit:cover;" />',
            obj.profile_image.url,
        )


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(DjangoUserAdmin):
    inlines = [UserSecurityProfileInline]


@admin.register(UserSecurityProfile)
class UserSecurityProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "profile_image_preview", "phone_number", "two_factor_enabled")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("profile_image_preview",)

    @admin.display(description="Profile Picture")
    def profile_image_preview(self, obj):
        if not obj or not obj.profile_image:
            return "No profile picture uploaded"
        return format_html(
            '<img src="{}" alt="profile" style="height:56px;width:56px;border-radius:50%;object-fit:cover;" />',
            obj.profile_image.url,
        )


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = ("subject", "email", "is_resolved", "created_at")
    list_filter = ("is_resolved", "created_at")
    search_fields = ("subject", "email", "message")
    readonly_fields = ("created_at",)
