const loginForm = document.getElementById("login-form");
const supportForm = document.getElementById("support-form");
const twofaField = document.getElementById("twofa-field");
const loginMessage = document.getElementById("message");
const supportMessage = document.getElementById("support-message");
const openSupportModalBtn = document.getElementById("open-support-modal");
const closeSupportModalBtn = document.getElementById("close-support-modal");
const supportModal = document.getElementById("support-modal");
let pendingToken = null;

function openSupportModal() {
  if (!supportModal) {
    return;
  }
  supportModal.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeSupportModal() {
  if (!supportModal) {
    return;
  }
  supportModal.classList.add("hidden");
  document.body.style.overflow = "";
}

openSupportModalBtn?.addEventListener("click", openSupportModal);
closeSupportModalBtn?.addEventListener("click", closeSupportModal);

supportModal?.addEventListener("click", (event) => {
  if (event.target === supportModal) {
    closeSupportModal();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && supportModal && !supportModal.classList.contains("hidden")) {
    closeSupportModal();
  }
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

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return "";
}

loginForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(loginForm);
  const payload = {
    username: formData.get("username"),
    password: formData.get("password")
  };

  if (pendingToken) {
    const verifyResponse = await fetch("/login/2fa/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken")
      },
      credentials: "same-origin",
      body: JSON.stringify({ token: pendingToken, secret_word: formData.get("twofa_secret") })
    });
    const verifyData = await verifyResponse.json();
    loginMessage.textContent = verifyData.message || "2FA result received.";
    if (verifyResponse.ok) {
      window.location.href = "/services/";
    }
    return;
  }

  const response = await fetch("/login/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    credentials: "same-origin",
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (data.require_2fa) {
    pendingToken = data.token;
    twofaField.classList.remove("hidden");
    loginMessage.textContent = "2FA required. Enter your secret word.";
    return;
  }

  loginMessage.textContent = data.message || "Login completed.";
  if (response.ok) {
    window.location.href = "/services/";
  }
});

supportForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(supportForm);
  const payload = {
    subject: formData.get("subject"),
    email: formData.get("email"),
    message: formData.get("message")
  };

  const response = await fetch("/login/support/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    credentials: "same-origin",
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  if (supportMessage) {
    const firstError = data.errors ? Object.values(data.errors)[0] : "";
    supportMessage.textContent = response.ok
      ? data.message || "Support request sent."
      : firstError || data.message || "Could not send support request.";
  }

  if (response.ok) {
    supportForm.reset();
    closeSupportModal();
  }
});
