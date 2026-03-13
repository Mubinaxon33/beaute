const params = new URLSearchParams(window.location.search);
const salonId = params.get("id");
const pathSalonMatch = window.location.pathname.match(/\/salons?\/(\d+)\/?$/);
const pathSalonId = pathSalonMatch ? pathSalonMatch[1] : null;
const initialReviewForm = document.getElementById("review-form");
const pageSalonId = salonId || initialReviewForm?.dataset.salonId || pathSalonId;
const detail = document.getElementById("detail");

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return "";
}

function starsText(rating) {
  const safe = Math.max(1, Math.min(5, Number(rating) || 0));
  return "★".repeat(safe) + "☆".repeat(5 - safe);
}

function reviewItemHtml(review) {
  return `
    <article class="review-item">
      <div class="review-head">
        <strong>${review.username}</strong>
        <span class="muted tiny">${review.created_at || "Just now"}</span>
      </div>
      <p class="review-stars" aria-label="${review.rating} out of 5 stars">${starsText(review.rating)}</p>
      <p>${review.comment}</p>
    </article>`;
}

function bindReviewForm(currentSalonId) {
  const reviewForm = document.getElementById("review-form");
  const reviewStatus = document.getElementById("review-status");
  const reviewsList = document.getElementById("reviews-list");
  const ratingValue = document.getElementById("salon-rating-value");
  const ratingCount = document.getElementById("salon-rating-count");

  if (!reviewForm || !reviewsList) {
    return;
  }

  reviewForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(reviewForm);
    const response = await fetch(`/salon/${currentSalonId}/reviews/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
        "Accept": "application/json"
      },
      credentials: "same-origin",
      body: formData
    });

    const data = await response.json();
    if (reviewStatus) {
      reviewStatus.textContent = data.message || "Review submitted.";
    }

    if (!response.ok) {
      return;
    }

    reviewsList.insertAdjacentHTML("afterbegin", reviewItemHtml(data.review));
    reviewForm.reset();

    if (ratingValue && data.avg_rating) {
      ratingValue.textContent = data.avg_rating;
    }
    if (ratingCount && typeof data.review_count !== "undefined") {
      ratingCount.textContent = `(${data.review_count} reviews)`;
    }
  });
}

function iconSvg(type) {
  const icons = {
    star: '<svg class="star-icon" viewBox="0 0 24 24" role="img" focusable="false"><path d="m12 2 2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17l-5.9 3.1 1.2-6.5L2.5 8.9l6.6-.9z"></path></svg>',
    map: '<svg viewBox="0 0 24 24" role="img" focusable="false"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"></path><circle cx="12" cy="10" r="3"></circle></svg>',
    clock: '<svg viewBox="0 0 24 24" role="img" focusable="false"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 3"></path></svg>',
    phone: '<svg viewBox="0 0 24 24" role="img" focusable="false"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.86 19.86 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.86 19.86 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.12.89.32 1.76.59 2.6a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.48-1.16a2 2 0 0 1 2.11-.45c.84.27 1.71.47 2.6.59A2 2 0 0 1 22 16.92z"></path></svg>',
    mail: '<svg viewBox="0 0 24 24" role="img" focusable="false"><rect x="3" y="5" width="18" height="14" rx="2"></rect><path d="m3 7 9 6 9-6"></path></svg>'
  };
  return icons[type] || "";
}

async function loadDetail() {
  if (!salonId) {
    return;
  }

  try {
    const response = await fetch(`/salon/${salonId}/?format=json`, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("Failed to load salon");
    }
    const data = await response.json();
    render(data);
  } catch (_error) {
    render({
      name: "Salon not found",
      address: "-",
      description: "Unable to load salon details.",
      services: []
    });
  }
}

function render(data) {
  const gallery = Array.isArray(data.photos) && data.photos.length ? data.photos : [];
  const mainPhoto = gallery[0] || "https://images.unsplash.com/photo-1611211235015-e2e3a7d09e97?auto=format&fit=crop&w=1400&q=80";
  const sidePhotoOne = gallery[1] || "https://images.unsplash.com/photo-1613457492120-4fcfbb7c3a5b?auto=format&fit=crop&w=900&q=80";
  const sidePhotoTwo = gallery[2] || "https://images.unsplash.com/photo-1723150512429-bfa92988d845?auto=format&fit=crop&w=900&q=80";

  const services = (data.services || [])
    .map(
      (service) => `
      <div class="service">
        <div>
          <h4>${service.name}</h4>
          <p class="muted">${service.duration_minutes} min</p>
        </div>
        <strong class="price">$${service.price}</strong>
      </div>`
    )
    .join("");

  const reviews = (data.reviews || []).map(reviewItemHtml).join("") || '<p class="muted">No reviews yet. Be the first to review this salon.</p>';

  detail.innerHTML = `
    <section class="gallery">
      <img src="${mainPhoto}" alt="${data.name}" />
      <div class="stack">
        <img src="${sidePhotoOne}" alt="Gallery" />
        <img src="${sidePhotoTwo}" alt="Gallery" />
      </div>
    </section>

    <section class="info">
      <div class="panel intro">
        <h2>${data.name}</h2>
        <div class="rating-row">
          <span class="star" aria-hidden="true">${iconSvg("star")}</span>
          <span id="salon-rating-value">${data.avg_rating || "0.0"}</span>
          <span id="salon-rating-count" class="muted">(${data.review_count ?? 0} reviews)</span>
        </div>

        <div class="meta">
          <div class="meta-item"><span class="meta-icon" aria-hidden="true">${iconSvg("map")}</span><span>${data.address || "-"}</span></div>
          <div class="meta-item"><span class="meta-icon" aria-hidden="true">${iconSvg("clock")}</span><span>${data.working_hours || "Hours not specified"}</span></div>
          <div class="meta-item"><span class="meta-icon" aria-hidden="true">${iconSvg("phone")}</span><span>${data.phone_number || "Not provided"}</span></div>
          <div class="meta-item"><span class="meta-icon" aria-hidden="true">${iconSvg("mail")}</span><span>${data.email || "Not provided"}</span></div>
        </div>

        <h3 class="section-title">About</h3>
        <p class="muted">${data.description || "No description available."}</p>
        <h3 class="section-title">Services & Pricing</h3>
        <div class="services">${services || "<p>No services listed.</p>"}</div>

        <h3 id="reviews" class="section-title">Leave a Review</h3>
        <form id="review-form" class="review-form" method="post" data-salon-id="${data.id}" novalidate>
          <div class="star-input-row" role="radiogroup" aria-label="Choose star rating">
            <input type="radio" id="star-5" name="rating" value="5" required />
            <label for="star-5" title="5 stars">★</label>
            <input type="radio" id="star-4" name="rating" value="4" />
            <label for="star-4" title="4 stars">★</label>
            <input type="radio" id="star-3" name="rating" value="3" />
            <label for="star-3" title="3 stars">★</label>
            <input type="radio" id="star-2" name="rating" value="2" />
            <label for="star-2" title="2 stars">★</label>
            <input type="radio" id="star-1" name="rating" value="1" />
            <label for="star-1" title="1 star">★</label>
          </div>
          <label class="review-label">Comment
            <textarea name="comment" rows="4" placeholder="Share your experience with this salon" required></textarea>
          </label>
          <button type="submit" class="review-submit">Submit Review</button>
          <p id="review-status" class="muted tiny"></p>
        </form>

        <h3 class="section-title">Reviews</h3>
        <div id="reviews-list" class="reviews-list">${reviews}</div>
      </div>
      <aside class="panel booking-panel">
        <h3>Book Appointment</h3>
        <p class="muted">Choose your preferred date and time</p>
        <a class="book-btn" href="/booking/${data.id}/">Book Now</a>
        <p class="policy muted">Free cancellation up to 24 hours before your appointment</p>
      </aside>
    </section>
  `;

  bindReviewForm(data.id);
}

if (pageSalonId) {
  bindReviewForm(pageSalonId);
}

loadDetail();
