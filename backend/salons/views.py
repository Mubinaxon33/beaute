from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from django.utils import timezone

from .models import Review, Salon


def _salons_queryset_with_ratings():
    return (
        Salon.objects.all()
        .prefetch_related("services", "photos", "employees")
        .annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews"))
    )


def _main_photo_url(salon: Salon):
    if salon.image:
        return salon.image.url

    first_gallery_photo = next((photo for photo in salon.photos.all() if photo.image), None)
    if first_gallery_photo:
        return first_gallery_photo.image.url
    return None


def _review_payload(review: Review):
    return {
        "id": review.id,
        "username": review.user.username,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": timezone.localtime(review.created_at).strftime("%Y-%m-%d %H:%M"),
    }


@require_GET
def home_view(request):
    salons = _salons_queryset_with_ratings().order_by("name")[:12]
    return render(request, "pages/index.html", {"salons": salons})


@require_GET
def salons_list_view(request):
    salons = _salons_queryset_with_ratings().order_by("name")

    if request.GET.get("format") == "json" or "application/json" in request.headers.get("Accept", ""):
        payload = [
            {
                "id": salon.id,
                "name": salon.name,
                "category": salon.category,
                "category_display": salon.get_category_display(),
                "address": salon.address,
                "working_hours": salon.working_hours_display,
                "phone_number": salon.phone_number,
                "email": salon.email,
                "description": salon.description,
                "image": _main_photo_url(salon),
                "avg_rating": f"{(salon.rating if salon.rating is not None else (salon.avg_rating or 0)):.1f}",
                "review_count": salon.review_count,
                "photos": [photo.image.url for photo in salon.photos.all() if photo.image],
                "services": [
                    {
                        "id": service.id,
                        "name": service.name,
                        "duration_minutes": service.duration_minutes,
                        "price": str(service.price),
                        "category": service.category,
                    }
                    for service in salon.services.all()
                ],
                "employees": [
                    {
                        "id": employee.id,
                        "full_name": employee.full_name,
                        "role": employee.role,
                    }
                    for employee in salon.employees.filter(is_active=True)
                ],
            }
            for salon in salons
        ]
        return JsonResponse(payload, safe=False)

    return render(request, "pages/salons.html", {"salons": salons})


@require_GET
def salon_detail_view(request, salon_id: int):
    salon = _salons_queryset_with_ratings().filter(pk=salon_id).first()
    if salon is None:
        if request.GET.get("format") == "json" or "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"detail": "Salon not found."}, status=404)
        return redirect("salons")

    if request.GET.get("format") == "json" or "application/json" in request.headers.get("Accept", ""):
        reviews = list(salon.reviews.select_related("user").all()[:20])
        payload = {
            "id": salon.id,
            "name": salon.name,
            "category": salon.category,
            "category_display": salon.get_category_display(),
            "address": salon.address,
            "working_hours": salon.working_hours_display,
            "phone_number": salon.phone_number,
            "email": salon.email,
            "description": salon.description,
            "image": _main_photo_url(salon),
            "opening_hours": salon.opening_hours,
            "avg_rating": f"{(salon.rating if salon.rating is not None else (salon.avg_rating or 0)):.1f}",
            "review_count": salon.review_count,
            "photos": [photo.image.url for photo in salon.photos.all() if photo.image],
            "services": [
                {
                    "id": service.id,
                    "name": service.name,
                    "duration_minutes": service.duration_minutes,
                    "price": str(service.price),
                    "category": service.category,
                }
                for service in salon.services.all()
            ],
            "employees": [
                {
                    "id": employee.id,
                    "full_name": employee.full_name,
                    "role": employee.role,
                }
                for employee in salon.employees.filter(is_active=True)
            ],
            "reviews": [_review_payload(review) for review in reviews],
        }
        return JsonResponse(payload)

    reviews = salon.reviews.select_related("user").all()[:20]
    return render(request, "pages/salon_detail.html", {"salon": salon, "reviews": reviews})


@require_http_methods(["POST"])
def salon_review_create_view(request, salon_id: int):
    salon = Salon.objects.filter(pk=salon_id).first()
    if salon is None:
        if "application/json" not in request.headers.get("Accept", ""):
            messages.error(request, "Salon not found.")
            return redirect("salons")
        return JsonResponse({"message": "Salon not found."}, status=404)

    wants_json = "application/json" in request.headers.get("Accept", "")

    if not request.user.is_authenticated:
        if wants_json:
            return JsonResponse({"message": "Please log in to leave a review."}, status=401)
        messages.error(request, "Please log in to leave a review.")
        return redirect("login")

    raw_rating = (request.POST.get("rating") or "").strip()
    comment = (request.POST.get("comment") or "").strip()

    try:
        rating = int(raw_rating)
    except ValueError:
        if not wants_json:
            messages.error(request, "Please choose a valid star rating.")
            return redirect("salon-detail", salon_id=salon.id)
        return JsonResponse({"message": "Please choose a valid star rating."}, status=400)

    if rating < 1 or rating > 5:
        if not wants_json:
            messages.error(request, "Rating must be between 1 and 5.")
            return redirect("salon-detail", salon_id=salon.id)
        return JsonResponse({"message": "Rating must be between 1 and 5."}, status=400)

    if not comment:
        if not wants_json:
            messages.error(request, "Please write a comment.")
            return redirect("salon-detail", salon_id=salon.id)
        return JsonResponse({"message": "Please write a comment."}, status=400)

    review = Review.objects.create(user=request.user, salon=salon, rating=rating, comment=comment)

    refreshed = _salons_queryset_with_ratings().filter(pk=salon.id).first()
    average = f"{(refreshed.rating if refreshed and refreshed.rating is not None else ((refreshed.avg_rating if refreshed else 0) or 0)):.1f}"
    review_count = refreshed.review_count if refreshed else salon.reviews.count()

    if not wants_json:
        messages.success(request, "Review submitted successfully.")
        return redirect("salon-detail", salon_id=salon.id)

    return JsonResponse(
        {
            "message": "Review submitted successfully.",
            "review": _review_payload(review),
            "avg_rating": average,
            "review_count": review_count,
        },
        status=201,
    )
