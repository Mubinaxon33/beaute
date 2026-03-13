import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import root_redirect_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", root_redirect_view, name="root-redirect"),
    path("", include("accounts.urls")),
    path("", include("salons.urls")),
    path("", include("bookings.urls")),
]

if settings.DEBUG or os.getenv("DJANGO_USE_SQLITE", "False").lower() == "true":
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
