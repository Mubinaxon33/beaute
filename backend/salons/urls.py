from django.urls import path

from .views import home_view, salon_detail_view, salon_review_create_view, salons_list_view

urlpatterns = [
    path("services/", home_view, name="home"),
    path("salons/", salons_list_view, name="salons"),
    path("salons/<int:salon_id>/", salon_detail_view, name="salons-detail"),
    path("salon/<int:salon_id>/", salon_detail_view, name="salon-detail"),
    path("salon/<int:salon_id>/reviews/", salon_review_create_view, name="salon-review-create"),
]
