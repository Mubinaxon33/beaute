const demoSalons = [
  {
    id: 1001,
    name: "Luxe Beauty Studio",
    address: "Downtown, Manhattan",
    description: "Hair, nails, and glow facials",
    image: "https://images.unsplash.com/photo-1611211235015-e2e3a7d09e97?auto=format&fit=crop&w=1000&q=80",
    avg_rating: "4.9",
    review_count: 256,
    price: "$$$",
    actionLabel: "Browse Salon"
  },
  {
    id: 1002,
    name: "Glamour Spa & Salon",
    address: "Upper East Side",
    description: "Bridal and premium makeup",
    image: "https://images.unsplash.com/photo-1613457492120-4fcfbb7c3a5b?auto=format&fit=crop&w=1000&q=80",
    avg_rating: "4.8",
    review_count: 189,
    price: "$$$$",
    actionLabel: "Browse Salon"
  },
  {
    id: 1003,
    name: "Serenity Wellness Spa",
    address: "Midtown West",
    description: "Luxury spa rituals",
    image: "https://images.unsplash.com/photo-1731514771613-991a02407132?auto=format&fit=crop&w=1000&q=80",
    avg_rating: "4.9",
    review_count: 312,
    price: "$$$",
    actionLabel: "Browse Salon"
  }
];

const grid = document.getElementById("salon-grid");
const categoryButtons = Array.from(document.querySelectorAll(".category-filter[data-category]"));
const serviceSearchInput = document.getElementById("service-search");
const locationInput = document.getElementById("location-filter");
const locationSearchButton = document.getElementById("location-search-btn");
const selectedCategories = new Set();
let serviceQuery = "";
let locationQuery = "";
let allSalons = [];

function normalizeCategory(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "");
}

function salonCategories(salon) {
  const fromServices = Array.isArray(salon.services)
    ? salon.services.map((service) => normalizeCategory(service.category || service.name))
    : [];
  const fromSalon = salon.category ? [normalizeCategory(salon.category), normalizeCategory(salon.category_display)] : [];
  return new Set([...fromServices, ...fromSalon].filter(Boolean));
}

function normalizeText(value) {
  return String(value || "").trim().toLowerCase();
}

function matchesCategoryFilter(salon) {
  if (!selectedCategories.size || selectedCategories.size === categoryButtons.length) {
    return true;
  }

  const categories = salonCategories(salon);
  return [...selectedCategories].some((category) => categories.has(category));
}

function matchesLocationFilter(salon) {
  if (!locationQuery) {
    return true;
  }

  const addressText = normalizeText(salon.address);
  const cityText = normalizeText(salon.city);
  return addressText.includes(locationQuery) || cityText.includes(locationQuery);
}

function matchesServiceFilter(salon) {
  if (!serviceQuery) {
    return true;
  }

  const searchableFields = [
    salon.name,
    salon.description,
    salon.category,
    salon.category_display,
    ...(Array.isArray(salon.services)
      ? salon.services.flatMap((service) => [service.name, service.category])
      : []),
  ].map(normalizeText);

  return searchableFields.some((value) => value.includes(serviceQuery));
}

function shouldShowSalon(salon) {
  return matchesCategoryFilter(salon) && matchesLocationFilter(salon) && matchesServiceFilter(salon);
}

function filteredSalons() {
  return allSalons.filter(shouldShowSalon);
}

function applyFilters() {
  render(filteredSalons());
}

function applyLocationFilter() {
  locationQuery = normalizeText(locationInput?.value);
  applyFilters();
}

function applyServiceFilter() {
  serviceQuery = normalizeText(serviceSearchInput?.value);
  applyFilters();
}

function updateButtonStates() {
  categoryButtons.forEach((button) => {
    const key = normalizeCategory(button.dataset.category);
    const isActive = selectedCategories.has(key);
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
}

function toggleCategory(button) {
  const key = normalizeCategory(button.dataset.category);
  if (!key) {
    return;
  }

  if (selectedCategories.has(key)) {
    selectedCategories.delete(key);
  } else {
    selectedCategories.add(key);
  }

  updateButtonStates();
  applyFilters();
}

function initializeCategoryFilters() {
  if (!categoryButtons.length) {
    return;
  }

  categoryButtons.forEach((button) => {
    button.addEventListener("click", () => toggleCategory(button));
    button.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        toggleCategory(button);
      }
    });
  });

  updateButtonStates();
}

function render(salons) {
  if (!grid) {
    return;
  }

  if (!salons.length) {
    grid.innerHTML = '<p class="muted">No salons match the selected filters.</p>';
    return;
  }

  grid.innerHTML = salons
    .map(
      (salon) => `
      <article class="card">
        <img src="${salon.image || "https://images.unsplash.com/photo-1611211235015-e2e3a7d09e97?auto=format&fit=crop&w=1000&q=80"}" alt="${salon.name}" />
        <div class="card-body">
        <h3>${salon.name}</h3>
        <p>${salon.avg_rating || "0.0"} (${salon.review_count ?? 0} reviews)</p>
        <p>${salon.address}</p>
        <p>${salon.price || "$$$"}</p>
        <a href="${salon.href || `/salon/${salon.id}/`}">${salon.actionLabel || "View details"}</a>
        </div>
      </article>`
    )
    .join("");
}

async function loadSalons() {
  try {
    const response = await fetch("/salons/?format=json", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("Failed to load salons");
    }

    const salons = await response.json();
    allSalons = salons.length ? salons.slice(0, 12) : demoSalons;
    applyFilters();
    return;
  } catch (_error) {
    // Keep graceful fallback for non-Django static preview.
  }

  allSalons = demoSalons;
  applyFilters();
}

initializeCategoryFilters();

locationSearchButton?.addEventListener("click", applyLocationFilter);
locationInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    applyLocationFilter();
  }
});

locationInput?.addEventListener("input", applyLocationFilter);

serviceSearchInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    applyServiceFilter();
  }
});

serviceSearchInput?.addEventListener("input", applyServiceFilter);

loadSalons();
