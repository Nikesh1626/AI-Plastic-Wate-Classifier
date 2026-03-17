// upload.js — File upload module + mode-switching
// Depends on: app.js (sendForPrediction), camera.js (initCamera, stopCamera)

let uploadedImageData = null;

/**
 * Switches the input panel between 'camera' and 'upload' modes.
 * @param {'camera'|'upload'} mode
 */
function switchMode(mode) {
  const cameraSection = document.getElementById("cameraMode");
  const uploadSection = document.getElementById("uploadMode");
  const cameraTabBtn = document.getElementById("cameraTabBtn");
  const uploadTabBtn = document.getElementById("uploadTabBtn");

  if (mode === "camera") {
    cameraSection.style.display = "block";
    uploadSection.style.display = "none";
    cameraTabBtn.classList.add("active");
    uploadTabBtn.classList.remove("active");
    initCamera();
  } else {
    cameraSection.style.display = "none";
    uploadSection.style.display = "block";
    cameraTabBtn.classList.remove("active");
    uploadTabBtn.classList.add("active");
    stopCamera();
  }
}

/**
 * Handles a file selected via the <input type="file"> element.
 * @param {Event} event
 */
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) loadImageFile(file);
}

/**
 * Handles a file dropped onto the drop zone.
 * @param {DragEvent} event
 */
function handleDrop(event) {
  event.preventDefault();
  const dropZone = document.getElementById("dropZone");
  dropZone.classList.remove("border-success");

  const file = event.dataTransfer.files[0];
  if (!file) return;

  const allowed = ["image/jpeg", "image/jpg", "image/png"];
  if (!allowed.includes(file.type)) {
    alert("Unsupported file type. Please upload a JPG or PNG image.");
    return;
  }
  loadImageFile(file);
}

function handleDragOver(event) {
  event.preventDefault();
  document.getElementById("dropZone").classList.add("border-success");
}

function handleDragLeave() {
  document.getElementById("dropZone").classList.remove("border-success");
}

/**
 * Reads the File object, shows a preview image, and arms the classify button.
 * @param {File} file
 */
function loadImageFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    uploadedImageData = e.target.result;
    const preview = document.getElementById("imagePreview");
    preview.src = uploadedImageData;
    preview.style.display = "block";
    document.getElementById("classifyUploadBtn").disabled = false;
  };
  reader.readAsDataURL(file);
}

/**
 * Resizes the uploaded image to 224×224 on the shared canvas,
 * then calls sendForPrediction.
 */
function classifyUpload() {
  if (!uploadedImageData) return;

  const img = new Image();
  img.onload = () => {
    const canvas = document.getElementById("captureCanvas");
    canvas.width = 224;
    canvas.height = 224;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0, 224, 224);
    const imageData = canvas.toDataURL("image/jpeg", 0.92);
    sendForPrediction(imageData);
  };
  img.src = uploadedImageData;
}
