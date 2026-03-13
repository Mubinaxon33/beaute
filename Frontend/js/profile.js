const twofaForm = document.getElementById("twofa-form");
const statusMessage = document.getElementById("status");
const deleteForm = document.getElementById("delete-account-form");
const deleteStatus = document.getElementById("delete-status");
const passwordChangeForm = document.getElementById("password-change-form");
const passwordChangeStatus = document.getElementById("password-change-status");
const profileUpdateForm = document.getElementById("profile-update-form");
const profileUpdateStatus = document.getElementById("profile-update-status");
const locationDisplay = document.getElementById("location-display");
const phoneDisplay = document.getElementById("phone-display");
const locationInput = document.getElementById("location-input");
const phoneInput = document.getElementById("phone-input");
const detectLocationBtn = document.getElementById("detect-location-btn");
const toggleProfileEditBtn = document.getElementById("toggle-profile-edit");
const progressFill = document.querySelector(".progress-fill[data-progress]");
const cancelBookingButtons = document.querySelectorAll(".js-cancel-booking");
const profileAvatar = document.getElementById("profile-avatar");
const openPhotoModalBtn = document.getElementById("open-photo-modal");
const closePhotoModalBtn = document.getElementById("close-photo-modal");
const photoModal = document.getElementById("photo-modal");
const photoInput = document.getElementById("photo-input");
const photoCanvas = document.getElementById("photo-editor-canvas");
const photoZoom = document.getElementById("photo-zoom");
const photoZoomInBtn = document.getElementById("photo-zoom-in");
const photoZoomOutBtn = document.getElementById("photo-zoom-out");
const photoRotateLeftBtn = document.getElementById("photo-rotate-left");
const photoRotateRightBtn = document.getElementById("photo-rotate-right");
const savePhotoBtn = document.getElementById("save-photo-btn");
const photoModalStatus = document.getElementById("photo-modal-status");
const passwordToggleButtons = document.querySelectorAll(".password-toggle[data-password-toggle]");

const MAX_PROFILE_IMAGE_SIZE = 5 * 1024 * 1024;
const ALLOWED_PROFILE_EXTENSIONS = [".jpg", ".jpeg", ".png"];

const photoState = {
  image: null,
  scale: 1,
  rotation: 0
};

if (progressFill) {
  const rawValue = Number(progressFill.getAttribute("data-progress") || "0");
  const boundedValue = Math.max(0, Math.min(rawValue, 100));
  progressFill.style.width = `${boundedValue}%`;
}

passwordToggleButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const targetId = button.dataset.passwordToggle;
    const input = document.getElementById(targetId);
    if (!input) {
      return;
    }

    const nextType = input.type === "password" ? "text" : "password";
    input.type = nextType;
    button.textContent = nextType === "text" ? "🙈" : "👁";
  });
});

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return "";
}

function maskUzPhone(rawValue) {
  let digits = rawValue.replace(/\D/g, "");
  if (digits.startsWith("998")) {
    digits = digits.slice(3);
  }
  digits = digits.slice(0, 9);

  const p1 = digits.slice(0, 2);
  const p2 = digits.slice(2, 5);
  const p3 = digits.slice(5, 7);
  const p4 = digits.slice(7, 9);

  let value = "+998 ";
  if (p1) {
    value += `(${p1}`;
    if (p1.length === 2) {
      value += ")";
    }
  }
  if (p2) {
    value += `-${p2}`;
  }
  if (p3) {
    value += `-${p3}`;
  }
  if (p4) {
    value += `-${p4}`;
  }
  return value;
}

phoneInput?.addEventListener("input", () => {
  phoneInput.value = maskUzPhone(phoneInput.value);
});

twofaForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(twofaForm);
  const payload = {
    current_password: formData.get("current_password"),
    secret_word: formData.get("secret_word"),
    enabled: formData.get("enabled") === "on"
  };

  const response = await fetch("/profile/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    credentials: "same-origin",
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  statusMessage.textContent = data.message || "Profile updated.";
});

passwordChangeForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(passwordChangeForm);
  const payload = {
    current_password: formData.get("current_password"),
    new_password: formData.get("new_password"),
    confirm_new_password: formData.get("confirm_new_password")
  };

  const response = await fetch("/profile/password/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    credentials: "same-origin",
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  if (passwordChangeStatus) {
    const firstError = data.errors ? Object.values(data.errors)[0] : "";
    passwordChangeStatus.textContent = data.message || firstError || "Password update completed.";
  }
  if (response.ok) {
    passwordChangeForm.reset();
  }
});

deleteForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!window.confirm("Delete your account permanently? This cannot be undone.")) {
    return;
  }

  const formData = new FormData(deleteForm);
  const payload = {
    current_password: formData.get("current_password")
  };

  const response = await fetch("/profile/delete/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    credentials: "same-origin",
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  deleteStatus.textContent = data.message || "Request completed.";
  if (response.ok) {
    window.location.href = data.redirect || "/login/";
  }
});

toggleProfileEditBtn?.addEventListener("click", () => {
  profileUpdateForm?.classList.toggle("hidden");
});

detectLocationBtn?.addEventListener("click", () => {
  if (!navigator.geolocation) {
    profileUpdateStatus.textContent = "Geolocation is not supported on this device.";
    return;
  }

  profileUpdateStatus.textContent = "Detecting location...";
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const { latitude, longitude } = position.coords;
      try {
        const response = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}`
        );
        const data = await response.json();
        const label = data.display_name || `Lat ${latitude.toFixed(4)}, Lng ${longitude.toFixed(4)}`;
        if (locationInput) {
          locationInput.value = label;
        }
        profileUpdateStatus.textContent = "Location filled from your device.";
      } catch (_error) {
        if (locationInput) {
          locationInput.value = `Lat ${latitude.toFixed(4)}, Lng ${longitude.toFixed(4)}`;
        }
        profileUpdateStatus.textContent = "Location set using coordinates.";
      }
    },
    () => {
      profileUpdateStatus.textContent = "Unable to access your location.";
    }
  );
});

profileUpdateForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  profileUpdateStatus.textContent = "";

  const formData = new FormData(profileUpdateForm);

  const response = await fetch("/profile/update/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    credentials: "same-origin",
    body: formData
  });

  const data = await response.json();
  profileUpdateStatus.textContent = data.message || "Profile updated.";

  if (!response.ok) {
    return;
  }

  if (data.location && locationDisplay) {
    locationDisplay.textContent = data.location;
  }

  if (data.phone_number && phoneDisplay) {
    phoneDisplay.textContent = data.phone_number;
  }

  profileUpdateForm.classList.add("hidden");
});

cancelBookingButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const bookingId = button.dataset.bookingId;
    if (!bookingId) {
      return;
    }

    if (!window.confirm("Cancel this booking? This action cannot be undone.")) {
      return;
    }

    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = "Cancelling...";

    try {
      const response = await fetch(`/booking/${bookingId}/cancel/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken")
        },
        credentials: "same-origin"
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || "Unable to cancel booking.");
      }

      window.location.reload();
    } catch (error) {
      window.alert(error.message || "Unable to cancel booking.");
      button.disabled = false;
      button.textContent = originalText;
    }
  });
});

function resetPhotoEditorStatus(message) {
  if (photoModalStatus) {
    photoModalStatus.textContent = message || "";
  }
}

function drawPhotoPreview() {
  if (!photoCanvas) {
    return;
  }

  const context = photoCanvas.getContext("2d");
  if (!context) {
    return;
  }

  context.clearRect(0, 0, photoCanvas.width, photoCanvas.height);
  context.fillStyle = "#e9ddca";
  context.fillRect(0, 0, photoCanvas.width, photoCanvas.height);

  if (!photoState.image) {
    context.fillStyle = "#7b6c57";
    context.font = "16px Manrope";
    context.textAlign = "center";
    context.fillText("Select an image to start editing", photoCanvas.width / 2, photoCanvas.height / 2);
    return;
  }

  const image = photoState.image;
  const baseScale = Math.max(photoCanvas.width / image.width, photoCanvas.height / image.height);
  const scale = baseScale * photoState.scale;
  const drawWidth = image.width * scale;
  const drawHeight = image.height * scale;

  context.save();
  context.translate(photoCanvas.width / 2, photoCanvas.height / 2);
  context.rotate((photoState.rotation * Math.PI) / 180);
  context.drawImage(image, -drawWidth / 2, -drawHeight / 2, drawWidth, drawHeight);
  context.restore();
}

function openPhotoModal() {
  if (!photoModal) {
    return;
  }

  photoModal.classList.remove("hidden");
  document.body.style.overflow = "hidden";
  drawPhotoPreview();
  resetPhotoEditorStatus("");
}

function closePhotoModal() {
  if (!photoModal) {
    return;
  }

  photoModal.classList.add("hidden");
  document.body.style.overflow = "";
}

function isValidProfileImageFile(file) {
  const lowerName = String(file.name || "").toLowerCase();
  const validExt = ALLOWED_PROFILE_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
  if (!validExt) {
    resetPhotoEditorStatus("Only JPG, JPEG, and PNG files are allowed.");
    return false;
  }

  if (file.size > MAX_PROFILE_IMAGE_SIZE) {
    resetPhotoEditorStatus("Profile image must be 5MB or less.");
    return false;
  }

  return true;
}

photoInput?.addEventListener("change", () => {
  const file = photoInput.files?.[0];
  if (!file || !isValidProfileImageFile(file)) {
    drawPhotoPreview();
    return;
  }

  const objectUrl = URL.createObjectURL(file);
  const image = new Image();
  image.onload = () => {
    photoState.image = image;
    photoState.scale = 1;
    photoState.rotation = 0;
    if (photoZoom) {
      photoZoom.value = "1";
    }
    drawPhotoPreview();
    resetPhotoEditorStatus("Adjust crop, zoom, or rotation, then save.");
    URL.revokeObjectURL(objectUrl);
  };
  image.onerror = () => {
    resetPhotoEditorStatus("Could not read this image file.");
    URL.revokeObjectURL(objectUrl);
  };
  image.src = objectUrl;
});

photoZoom?.addEventListener("input", () => {
  photoState.scale = Number(photoZoom.value);
  drawPhotoPreview();
});

photoZoomInBtn?.addEventListener("click", () => {
  if (!photoZoom) {
    return;
  }
  const next = Math.min(Number(photoZoom.max), Number(photoZoom.value) + 0.1);
  photoZoom.value = next.toFixed(2);
  photoState.scale = next;
  drawPhotoPreview();
});

photoZoomOutBtn?.addEventListener("click", () => {
  if (!photoZoom) {
    return;
  }
  const next = Math.max(Number(photoZoom.min), Number(photoZoom.value) - 0.1);
  photoZoom.value = next.toFixed(2);
  photoState.scale = next;
  drawPhotoPreview();
});

photoRotateLeftBtn?.addEventListener("click", () => {
  photoState.rotation -= 90;
  drawPhotoPreview();
});

photoRotateRightBtn?.addEventListener("click", () => {
  photoState.rotation += 90;
  drawPhotoPreview();
});

openPhotoModalBtn?.addEventListener("click", openPhotoModal);
closePhotoModalBtn?.addEventListener("click", closePhotoModal);

photoModal?.addEventListener("click", (event) => {
  if (event.target === photoModal) {
    closePhotoModal();
  }
});

savePhotoBtn?.addEventListener("click", () => {
  if (!photoState.image || !photoCanvas) {
    resetPhotoEditorStatus("Please upload an image first.");
    return;
  }

  savePhotoBtn.disabled = true;
  savePhotoBtn.textContent = "Saving...";

  photoCanvas.toBlob(async (blob) => {
    if (!blob) {
      resetPhotoEditorStatus("Could not prepare edited image.");
      savePhotoBtn.disabled = false;
      savePhotoBtn.textContent = "Save Photo";
      return;
    }

    const formData = new FormData();
    formData.append("profile_image", blob, "profile.jpg");

    try {
      const response = await fetch("/profile/photo/", {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken")
        },
        credentials: "same-origin",
        body: formData
      });

      const data = await response.json();
      if (!response.ok) {
        const firstError = data.errors ? Object.values(data.errors)[0] : null;
        throw new Error(firstError || data.message || "Profile photo update failed.");
      }

      if (profileAvatar && data.profile_image_url) {
        profileAvatar.src = data.profile_image_url;
      }
      resetPhotoEditorStatus(data.message || "Profile photo updated successfully.");
      closePhotoModal();
    } catch (error) {
      resetPhotoEditorStatus(error.message || "Profile photo update failed.");
    } finally {
      savePhotoBtn.disabled = false;
      savePhotoBtn.textContent = "Save Photo";
    }
  }, "image/jpeg", 0.92);
});

drawPhotoPreview();
