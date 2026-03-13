const copyButton = document.getElementById("copy-btn");
const status = document.getElementById("status");
const form = document.getElementById("payment-form");
const receipt = document.getElementById("receipt");
const uploadZone = document.getElementById("upload-zone");
const uploadPlaceholder = document.getElementById("upload-placeholder");
const uploadFile = document.getElementById("upload-file");
const fileName = document.getElementById("file-name");
const fileSize = document.getElementById("file-size");
const submitBtn = document.getElementById("submit-btn");
const paymentPage = document.getElementById("payment-page");
const successScreen = document.getElementById("success-screen");
const successHomeBtn = document.getElementById("success-home-btn");

let copiedTimer = null;

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return "";
}

copyButton?.addEventListener("click", async () => {
  const value = document.getElementById("card")?.textContent?.replace(/\s/g, "") || "";
  try {
    await navigator.clipboard.writeText(value);
    copyButton.textContent = "Copied!";
    copyButton.classList.add("copied");
    if (copiedTimer) {
      clearTimeout(copiedTimer);
    }
    copiedTimer = setTimeout(() => {
      copyButton.textContent = "Copy";
      copyButton.classList.remove("copied");
    }, 2000);
  } catch (_error) {
    status.textContent = "Could not copy card number.";
  }
});

receipt?.addEventListener("change", () => {
  const selectedFile = receipt.files?.[0];
  if (!selectedFile) {
    uploadZone?.classList.remove("has-file");
    uploadPlaceholder.hidden = false;
    uploadFile.hidden = true;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Please Upload Receipt First";
    }
    return;
  }

  uploadZone?.classList.add("has-file");
  uploadPlaceholder.hidden = true;
  uploadFile.hidden = false;
  if (fileName) {
    fileName.textContent = selectedFile.name;
  }
  if (fileSize) {
    fileSize.textContent = `${(selectedFile.size / 1024).toFixed(2)} KB`;
  }
  if (submitBtn) {
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit Payment Receipt";
  }
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!receipt?.files?.length) {
    status.textContent = "Please upload your payment receipt";
    return;
  }

  const formData = new FormData(form);
  const response = await fetch("/payment/submit/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    credentials: "same-origin",
    body: formData,
  });
  const data = await response.json();
  status.textContent = data.message || "Payment response received.";
  if (response.ok) {
    if (paymentPage) {
      paymentPage.hidden = true;
    }
    if (successScreen) {
      successScreen.hidden = false;
    }
    setTimeout(() => {
      window.location.href = data.redirect_to || "/salons/";
    }, 2000);
  }
});

successHomeBtn?.addEventListener("click", () => {
  window.location.href = "/salons/";
});
