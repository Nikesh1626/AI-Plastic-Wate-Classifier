// camera.js — Webcam capture module
// Depends on: app.js (sendForPrediction)

let cameraStream = null;

/**
 * Requests camera access and pipes the stream to #videoPreview.
 * Prefers the rear-facing camera on mobile devices.
 */
function initCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showCameraError("Your browser does not support camera access.");
    return;
  }

  const constraints = {
    video: {
      facingMode: { ideal: "environment" },
      width: { ideal: 640 },
      height: { ideal: 480 },
    },
  };

  navigator.mediaDevices
    .getUserMedia(constraints)
    .then((stream) => {
      cameraStream = stream;
      const video = document.getElementById("videoPreview");
      video.srcObject = stream;
    })
    .catch((err) => {
      console.warn("Camera unavailable:", err);
      showCameraError(
        "Camera not available or access denied. Please switch to <strong>Upload</strong> mode.",
      );
    });
}

/**
 * Stops all active camera tracks.
 */
function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
  const video = document.getElementById("videoPreview");
  if (video) video.srcObject = null;
}

/**
 * Captures the current video frame, draws it on the shared canvas,
 * and sends it for classification.
 */
function captureAndClassify() {
  const video = document.getElementById("videoPreview");
  const canvas = document.getElementById("captureCanvas");

  if (!video.srcObject) {
    showCameraError("Camera is not active. Please enable camera access.");
    return;
  }

  canvas.width = 224;
  canvas.height = 224;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, 224, 224);

  const imageData = canvas.toDataURL("image/jpeg", 0.92);
  sendForPrediction(imageData);
}

function showCameraError(htmlMessage) {
  const cameraMode = document.getElementById("cameraMode");
  const existing = cameraMode.querySelector(".camera-error-msg");
  if (existing) existing.remove();

  const alert = document.createElement("div");
  alert.className = "alert alert-warning camera-error-msg mt-2";
  alert.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>${htmlMessage}`;
  cameraMode.insertBefore(alert, cameraMode.firstChild);
}

// Start camera as soon as page DOM is ready
document.addEventListener("DOMContentLoaded", initCamera);
