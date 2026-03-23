// app.js — Shared prediction logic and result rendering
// Loaded first so camera.js, upload.js and map.js can call sendForPrediction().

/**
 * Safely escapes HTML to prevent XSS when rendering API-sourced text.
 */
function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Converts basic Gemini markdown to safe HTML for display.
 * Operates on already-escaped text so only the markdown tokens are trusted.
 */
function markdownToHtml(raw) {
  return escapeHtml(raw)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/^[\*\-]\s+/gm, "• ")
    .replace(/\n/g, "<br>");
}

/**
 * Sends a base64-encoded image to /predict and renders the result.
 * @param {string} imageData  base64 data-URL (image/jpeg)
 */
function sendForPrediction(imageData) {
  const spinner = document.getElementById("loadingSpinner");
  const resultCard = document.getElementById("resultCard");
  const placeholderCard = document.getElementById("placeholderCard");
  const captureBtn = document.getElementById("captureBtn");
  const classifyUploadBtn = document.getElementById("classifyUploadBtn");

  // Show spinner, lock buttons
  spinner.style.display = "block";
  if (captureBtn) captureBtn.disabled = true;
  if (classifyUploadBtn) classifyUploadBtn.disabled = true;
  resultCard.style.display = "none";
  placeholderCard.style.display = "none";

  fetch("/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: imageData }),
  })
    .then((res) => res.json())
    .then((data) => {
      spinner.style.display = "none";
      if (captureBtn) captureBtn.disabled = false;
      if (classifyUploadBtn) classifyUploadBtn.disabled = false;

      if (data.error) {
        showPredictionError(escapeHtml(data.error));
        return;
      }
      displayResult(data);
    })
    .catch((err) => {
      spinner.style.display = "none";
      if (captureBtn) captureBtn.disabled = false;
      if (classifyUploadBtn) classifyUploadBtn.disabled = false;
      showPredictionError("Connection error. Please try again.");
      console.error(err);
    });
}

function displayResult(data) {
  const resultCard = document.getElementById("resultCard");
  const placeholderCard = document.getElementById("placeholderCard");

  // Plastic type badge
  document.getElementById("plasticTypeLabel").textContent = escapeHtml(
    data.type,
  );

  // Confidence bar
  const conf = parseFloat(data.confidence) || 0;
  document.getElementById("confidenceText").textContent = conf + "%";
  const bar = document.getElementById("confidenceBar");
  const boundedConf = Math.max(0, Math.min(100, conf));
  bar.style.width = boundedConf + "%";
  if (boundedConf >= 75) {
    bar.style.background = "linear-gradient(135deg, #006e1c 0%, #4caf50 100%)";
  } else if (boundedConf >= 45) {
    bar.style.background = "linear-gradient(135deg, #8b7a09 0%, #d4b10b 100%)";
  } else {
    bar.style.background = "linear-gradient(135deg, #8a1c1c 0%, #d64545 100%)";
  }

  // Reuse list (desi ideas shown in quotes)
  const reuseList = document.getElementById("reuseList");
  if (Array.isArray(data.reuse)) {
    reuseList.innerHTML = data.reuse
      .map((item) => {
        const cleanItem = String(item)
          .trim()
          .replace(/^"+|"+$/g, "");
        return `<li class="mb-0.5 leading-6">"${escapeHtml(cleanItem)}"</li>`;
      })
      .join("");
  }

  // Recycling instructions (2-3 pointwise)
  const recycleInfo = document.getElementById("recycleInfo");
  const recycleItems = Array.isArray(data.recycle_instructions)
    ? data.recycle_instructions
    : [];

  if (recycleItems.length) {
    recycleInfo.innerHTML = recycleItems
      .map((item) => `<li class="mb-0.5 leading-6">${escapeHtml(item)}</li>`)
      .join("");
  } else {
    recycleInfo.innerHTML =
      '<li class="mb-0.5 leading-6">Recycling instructions are currently unavailable.</li>';
  }

  // AI advice — Gemini markdown converted to safe HTML
  const aiText = document.getElementById("aiAdviceText");
  if (data.ai_advice) {
    aiText.innerHTML = markdownToHtml(data.ai_advice);
  } else {
    aiText.textContent = "AI advice unavailable.";
  }

  placeholderCard.style.display = "none";
  resultCard.style.display = "block";

  // On mobile, scroll result into view
  if (window.innerWidth < 992) {
    resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function showPredictionError(safeMessage) {
  const placeholderCard = document.getElementById("placeholderCard");
  placeholderCard.innerHTML = `
    <i class="bi bi-exclamation-circle-fill display-4 text-danger"></i>
    <p class="text-danger mt-3">${safeMessage}</p>
    <p class="text-muted small">Check the console for details.</p>
  `;
  placeholderCard.style.display = "block";
}

function scrollToMapSection() {
  const locationsSection = document.getElementById("locationsSection");
  if (locationsSection) {
    locationsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}
