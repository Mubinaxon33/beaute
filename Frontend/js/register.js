const form = document.getElementById("register-form");
const message = document.getElementById("message");
const phoneInput = document.getElementById("phone-number");
const passwordInput = document.getElementById("register-password");
const confirmPasswordInput = document.getElementById("register-confirm-password");
const strengthLabel = document.getElementById("password-strength");
const fieldErrors = document.querySelectorAll(".field-error");

const PHONE_REGEX = /^\+998 \(\d{2}\)-\d{3}-\d{2}-\d{2}$/;
const STRONG_PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/;

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return "";
}

function clearFieldErrors() {
  fieldErrors.forEach((item) => {
    item.textContent = "";
  });
}

function setFieldError(fieldName, errorText) {
  const target = document.querySelector(`.field-error[data-error-for="${fieldName}"]`);
  if (target) {
    target.textContent = errorText;
  }
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

function getPasswordStrength(value) {
  let score = 0;
  if (value.length >= 8) score += 1;
  if (/[a-z]/.test(value)) score += 1;
  if (/[A-Z]/.test(value)) score += 1;
  if (/\d/.test(value)) score += 1;
  if (/[^\w\s]/.test(value)) score += 1;

  if (score <= 2) return "Weak";
  if (score <= 4) return "Medium";
  return "Strong";
}

phoneInput?.addEventListener("input", () => {
  phoneInput.value = maskUzPhone(phoneInput.value);
});

passwordInput?.addEventListener("input", () => {
  strengthLabel.textContent = `Strength: ${getPasswordStrength(passwordInput.value)}`;
});

document.querySelectorAll(".eye-btn").forEach((button) => {
  button.addEventListener("click", () => {
    const target = document.getElementById(button.dataset.target);
    if (!target) {
      return;
    }
    target.type = target.type === "password" ? "text" : "password";
  });
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "";
  clearFieldErrors();

  if (passwordInput.value !== confirmPasswordInput.value) {
    setFieldError("confirm_password", "Passwords do not match.");
    return;
  }
  if (!STRONG_PASSWORD_REGEX.test(passwordInput.value)) {
    setFieldError("password", "Password is not strong enough.");
    return;
  }
  if (!PHONE_REGEX.test(phoneInput.value)) {
    setFieldError("phone_number", "Phone must match +998 (XX)-XXX-XX-XX.");
    return;
  }

  const payload = Object.fromEntries(new FormData(form).entries());
  const response = await fetch("/register/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    credentials: "same-origin",
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  if (response.ok) {
    message.textContent = data.message || "Registration completed.";
    form.reset();
    phoneInput.value = "+998 ";
    strengthLabel.textContent = "Strength: -";
    setTimeout(() => {
      window.location.href = "/login/";
    }, 1300);
    return;
  }

  if (data.errors && typeof data.errors === "object") {
    Object.entries(data.errors).forEach(([field, value]) => {
      setFieldError(field, String(value));
    });
  }
  if (!Object.keys(data.errors || {}).length) {
    message.textContent = data.message || "Registration failed.";
  }
});
