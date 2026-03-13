let salons = [];
const fallbackSalons = [
  {
    id: null,
    name: "Luxe Beauty Studio",
    address: "Downtown, Manhattan",
    description: "Premium hair and skin care",
    image: "https://images.unsplash.com/photo-1611211235015-e2e3a7d09e97?auto=format&fit=crop&w=1000&q=80",
    avg_rating: "4.9",
    review_count: 256,
    price: "$$$",
    href: "/salons/",
    actionLabel: "Browse salons"
  }
];

const list = document.getElementById("salons-list");
const search = document.getElementById("search");

async function loadSalons() {
  let apiLoaded = false;

  try {
    const response = await fetch("/salons/?format=json", { headers: { Accept: "application/json" } });
    if (response.ok) {
      salons = await response.json();
      apiLoaded = true;
    }
  } catch (_error) {
    salons = [];
  }

  if (!salons.length) {
    salons = fallbackSalons;
  }
  render(salons);
}

function render(data) {
  list.innerHTML = data
    .map(
      (salon) => `
      <article class="card">
        <img src="${salon.image || "https://images.unsplash.com/photo-1611211235015-e2e3a7d09e97?auto=format&fit=crop&w=1000&q=80"}" alt="${salon.name}" />
        <div class="card-body">
          <h3>${salon.name}</h3>
          <p>${salon.avg_rating || "0.0"} (${salon.review_count ?? 0} reviews)</p>
          <p>${salon.address}</p>
          <p>${salon.price || "$$$"}</p>
          <a href="${salon.href || `/salon/${salon.id}/`}">${salon.actionLabel || "Open"}</a>
        </div>
      </article>`
    )
    .join("");
}

search?.addEventListener("input", () => {
  const query = search.value.trim().toLowerCase();
  const filtered = salons.filter(
    (salon) => salon.name.toLowerCase().includes(query) || salon.address.toLowerCase().includes(query)
  );
  render(filtered);
});

loadSalons();
