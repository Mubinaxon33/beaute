const bookingForm = document.getElementById("booking-form");
const salonId = bookingForm?.dataset.salonId;
const rescheduleBookingId = bookingForm?.dataset.rescheduleBookingId || "";
const initialServiceId = bookingForm?.dataset.initialServiceId || "";
const initialEmployeeId = bookingForm?.dataset.initialEmployeeId || "";
const initialDate = bookingForm?.dataset.initialDate || "";
const initialTime = bookingForm?.dataset.initialTime || "";
const serviceSelect = document.getElementById("service-select");
const bookingDateInput = document.getElementById("booking-date");
const calendarShell = document.getElementById("calendar-shell");
const calendarGrid = document.getElementById("calendar-grid");
const calendarMonthLabel = document.getElementById("calendar-month");
const calendarPrevBtn = document.getElementById("calendar-prev");
const calendarNextBtn = document.getElementById("calendar-next");
const slotsContainer = document.getElementById("time-slots");
const selectedTimeInput = document.getElementById("start-time");
const bookingMessage = document.getElementById("booking-message");
const continueBtn = document.getElementById("continue-btn");
const specialistSelect = document.getElementById("specialist-select");
const specialistHint = document.getElementById("specialist-hint");
const summaryService = document.getElementById("summary-service");
const summarySpecialist = document.getElementById("summary-specialist");
const summaryDate = document.getElementById("summary-date");
const summaryTime = document.getElementById("summary-time");
const summaryDuration = document.getElementById("summary-duration");
const summaryTotal = document.getElementById("summary-total");

let currentServices = [];
let hasAvailableSpecialists = true;
let calendarCursor = new Date();
let initialSelectionApplied = false;

const ICONS = {
  specialist: "M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-4.2 0-7 2.1-7 4v1h14v-1c0-1.9-2.8-4-7-4Z",
  date: "M7 2v2M17 2v2M4 9h16M6 4h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z",
  time: "M12 6v6l4 2",
  duration: "M12 8v5m0 3h.01M5.5 19h13a1.5 1.5 0 0 0 1.3-2.3l-6.5-11.2a1.5 1.5 0 0 0-2.6 0L4.2 16.7A1.5 1.5 0 0 0 5.5 19Z"
};

function setSummaryValue(element, text, icon) {
  if (!element) {
    return;
  }

  element.textContent = "";
  if (icon && ICONS[icon]) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "summary-icon");
    svg.setAttribute("aria-hidden", "true");

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", ICONS[icon]);
    svg.appendChild(path);
    element.appendChild(svg);
  }

  element.appendChild(document.createTextNode(text));
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return "";
}

function toIsoDate(dateObj) {
  const year = dateObj.getFullYear();
  const month = String(dateObj.getMonth() + 1).padStart(2, "0");
  const day = String(dateObj.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseIsoDate(value) {
  if (!value) {
    return null;
  }
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }
  return new Date(year, month - 1, day);
}

function isPastDate(dayDate) {
  const today = new Date();
  const nowDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  return dayDate < nowDate;
}

function renderCalendar() {
  if (!calendarGrid || !calendarMonthLabel) {
    return;
  }

  const year = calendarCursor.getFullYear();
  const month = calendarCursor.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const offset = firstDay.getDay();
  const selectedIso = bookingDateInput?.value || "";

  calendarMonthLabel.textContent = firstDay.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric"
  });

  calendarGrid.innerHTML = "";
  for (let i = 0; i < offset; i += 1) {
    const emptyCell = document.createElement("span");
    emptyCell.className = "calendar-empty";
    calendarGrid.appendChild(emptyCell);
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const dayDate = new Date(year, month, day);
    const iso = toIsoDate(dayDate);
    const dayButton = document.createElement("button");
    dayButton.type = "button";
    dayButton.className = "calendar-day";
    dayButton.textContent = String(day);
    dayButton.dataset.date = iso;

    if (iso === selectedIso) {
      dayButton.classList.add("selected");
    }

    if (isPastDate(dayDate)) {
      dayButton.disabled = true;
      dayButton.classList.add("disabled");
    }

    dayButton.addEventListener("click", () => {
      if (dayButton.disabled) {
        return;
      }
      bookingDateInput.value = iso;
      selectedTimeInput.value = "";
      renderCalendar();
      loadAvailability();
      updateSummary();
    });

    calendarGrid.appendChild(dayButton);
  }
}

function initCalendar() {
  if (!bookingDateInput) {
    return;
  }

  const selectedDate = parseIsoDate(bookingDateInput.value);
  calendarCursor = selectedDate || new Date();
  renderCalendar();

  calendarPrevBtn?.addEventListener("click", () => {
    calendarCursor = new Date(calendarCursor.getFullYear(), calendarCursor.getMonth() - 1, 1);
    renderCalendar();
  });

  calendarNextBtn?.addEventListener("click", () => {
    calendarCursor = new Date(calendarCursor.getFullYear(), calendarCursor.getMonth() + 1, 1);
    renderCalendar();
  });
}

async function loadSalonData() {
  if (!salonId) {
    bookingMessage.textContent = "Please open booking from a salon detail page.";
    return;
  }

  const response = await fetch(`/salon/${salonId}/?format=json`, { headers: { Accept: "application/json" } });
  const salon = response.ok ? await response.json() : null;
  if (!salon) {
    bookingMessage.textContent = "Could not load salon details.";
    return;
  }

  fillServices(salon.services || []);
  fillSpecialists(salon.employees || []);
  await applyInitialSelection();
  updateSummary();
}

async function applyInitialSelection() {
  if (initialSelectionApplied) {
    return;
  }

  if (initialServiceId && serviceSelect) {
    serviceSelect.value = initialServiceId;
  }

  if (initialEmployeeId && specialistSelect) {
    specialistSelect.value = initialEmployeeId;
  }

  if (initialDate && bookingDateInput) {
    bookingDateInput.value = initialDate;
    const selectedDate = parseIsoDate(initialDate);
    if (selectedDate) {
      calendarCursor = selectedDate;
      renderCalendar();
    }
    await loadAvailability();
  }

  if (initialTime && slotsContainer) {
    const initialSlotBtn = slotsContainer.querySelector(`.slot[data-time="${initialTime}"]:not(.disabled)`);
    initialSlotBtn?.click();
  }

  initialSelectionApplied = true;
}

function setSpecialistHint(message, mode) {
  if (!specialistHint) {
    return;
  }

  specialistHint.textContent = message;
  specialistHint.classList.remove("is-error", "is-info");
  if (mode === "error") {
    specialistHint.classList.add("is-error");
  }
  if (mode === "info") {
    specialistHint.classList.add("is-info");
  }
}

function setBookingLocked(locked) {
  if (serviceSelect) {
    serviceSelect.disabled = locked;
  }
  if (bookingDateInput) {
    bookingDateInput.disabled = locked;
  }
  calendarPrevBtn && (calendarPrevBtn.disabled = locked);
  calendarNextBtn && (calendarNextBtn.disabled = locked);
  calendarShell?.classList.toggle("is-disabled", locked);

  bookingDateInput.value = "";
  selectedTimeInput.value = "";
  renderCalendar();
  if (locked) {
    slotsContainer.innerHTML = '<p class="slot-note">Add an active specialist in Admin to open booking slots.</p>';
  } else {
    slotsContainer.innerHTML = "";
  }
}

function fillServices(services) {
  currentServices = services;
  serviceSelect.innerHTML = services
    .map((service) => `<option value="${service.id}">${service.name} - ${service.duration_minutes}min</option>`)
    .join("");
  updateSummary();
}

function fillSpecialists(employees) {
  if (!specialistSelect) {
    return;
  }

  if (!employees.length) {
    hasAvailableSpecialists = false;
    specialistSelect.innerHTML = '<option value="">No specialists available yet</option>';
    specialistSelect.disabled = true;
    setSpecialistHint("No active specialists in this salon yet. Please try again later.", "error");
    setBookingLocked(true);
    updateSummary();
    return;
  }

  hasAvailableSpecialists = true;
  specialistSelect.disabled = false;
  setSpecialistHint("Select your preferred specialist for this appointment.", "info");
  setBookingLocked(false);

  specialistSelect.innerHTML = [
    '<option value="">Choose a specialist</option>',
    ...employees.map((employee) => {
      const roleSuffix = employee.role ? ` (${employee.role})` : "";
      return `<option value="${employee.id}">${employee.full_name}${roleSuffix}</option>`;
    })
  ].join("");
}

function updateSummary() {
  const selectedService = currentServices.find((item) => String(item.id) === serviceSelect.value);
  summaryService.textContent = selectedService ? selectedService.name : "Not selected";
  setSummaryValue(summaryDuration, selectedService ? `${selectedService.duration_minutes} min` : "-", "duration");
  summaryTotal.textContent = selectedService ? `$${selectedService.price}` : "$0";

  const specialistName = specialistSelect?.selectedOptions?.[0]?.textContent || "Not selected";
  setSummaryValue(summarySpecialist, specialistName, "specialist");

  if (bookingDateInput?.value) {
    const dateObj = new Date(`${bookingDateInput.value}T00:00:00`);
    setSummaryValue(summaryDate, dateObj.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric"
    }), "date");
  } else {
    setSummaryValue(summaryDate, "Not selected", "date");
  }

  setSummaryValue(summaryTime, selectedTimeInput.value || "Not selected", "time");

  const valid =
    hasAvailableSpecialists &&
    Boolean(bookingDateInput?.value) &&
    Boolean(selectedTimeInput.value) &&
    Boolean(serviceSelect?.value) &&
    Boolean(specialistSelect?.value);

  if (continueBtn) {
    continueBtn.disabled = !valid;
  }
}

async function loadAvailability() {
  const date = bookingDateInput.value;
  if (!salonId || !date) {
    return;
  }

  const response = await fetch(`/api/salon/${salonId}/availability/?date=${date}`);
  const data = await response.json();
  renderSlots(data.available_slots || [], data.fully_booked);
}

function renderSlots(slots, fullyBooked) {
  selectedTimeInput.value = "";
  updateSummary();
  if (fullyBooked) {
    slotsContainer.innerHTML = "<p>This day is fully booked.</p>";
    if (continueBtn) continueBtn.disabled = true;
    return;
  }

  slotsContainer.innerHTML = slots
    .map((slot) => `<button type="button" class="slot ${slot.available ? "" : "disabled"}" data-time="${slot.time}" ${slot.available ? "" : "disabled"}>${slot.time}</button>`)
    .join("");

  slotsContainer.querySelectorAll(".slot:not(.disabled)").forEach((button) => {
    button.addEventListener("click", () => {
      slotsContainer.querySelectorAll(".slot").forEach((item) => item.classList.remove("selected"));
      button.classList.add("selected");
      selectedTimeInput.value = button.dataset.time;
      updateSummary();
    });
  });
}

serviceSelect?.addEventListener("change", updateSummary);
specialistSelect?.addEventListener("change", updateSummary);

bookingForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!hasAvailableSpecialists) {
    bookingMessage.textContent = "Booking is unavailable until the salon has at least one active specialist.";
    return;
  }

  const formData = new FormData(bookingForm);
  if (!selectedTimeInput.value) {
    bookingMessage.textContent = "Select an available time slot.";
    return;
  }

  const submitUrl = rescheduleBookingId
    ? `/booking/${rescheduleBookingId}/reschedule/`
    : `/booking/${salonId}/create/`;

  const response = await fetch(submitUrl, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    credentials: "same-origin",
    body: formData
  });
  const data = await response.json();
  bookingMessage.textContent = data.message || "Booking response received.";
  if (response.ok) {
    window.location.href = data.redirect_to || (rescheduleBookingId ? "/profile/" : "/payment/");
  }
});

initCalendar();
loadSalonData();
updateSummary();
