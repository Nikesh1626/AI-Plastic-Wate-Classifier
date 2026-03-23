// upload.js — File upload module + mode-switching
// Depends on: app.js (sendForPrediction), camera.js (initCamera, stopCamera)

let uploadedImageData = null;
const ALLOWED_UPLOAD_TYPES = ["image/jpeg", "image/jpg", "image/png"];

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
    updateUploadView();
    stopCamera();
  }
}

function updateUploadView() {
  const dropZone = document.getElementById("dropZone");
  const preview = document.getElementById("imagePreview");
  if (!dropZone || !preview) return;

  if (uploadedImageData) {
    dropZone.style.display = "none";
    preview.style.display = "block";
  } else {
    dropZone.style.display = "flex";
    preview.style.display = "none";
  }
}

/**
 * Switches mode and scrolls to the classifier panel.
 * @param {'camera'|'upload'} mode
 */
function goToClassifier(mode) {
  switchMode(mode);
  const classifierSection = document.getElementById("classifierSection");
  if (classifierSection) {
    classifierSection.scrollIntoView({ behavior: "smooth", block: "start" });
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
 * Handles folder selections via webkitdirectory input and loads the first
 * supported image from the selected folder tree.
 * @param {Event} event
 */
function handleFolderSelect(event) {
  const files = Array.from(event.target.files || []);
  const supported = files.filter((file) =>
    ALLOWED_UPLOAD_TYPES.includes(file.type),
  );

  if (!supported.length) {
    alert("No supported images found in the selected folder.");
    return;
  }

  loadImageFile(supported[0]);
}

/**
 * Opens file picker on click. Double-click opens folder picker.
 * @param {MouseEvent} event
 */
function openUploadPicker(event) {
  if (event.target.closest("label")) return;

  const fileInput = document.getElementById("fileInput");
  const folderInput = document.getElementById("folderInput");
  if (!fileInput) return;

  if (event.detail === 2 && folderInput) {
    folderInput.click();
    return;
  }
  fileInput.click();
}

/**
 * Keyboard activation for the upload zone.
 * @param {KeyboardEvent} event
 */
function onUploadZoneKeydown(event) {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  const fileInput = document.getElementById("fileInput");
  if (fileInput) fileInput.click();
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

  if (!ALLOWED_UPLOAD_TYPES.includes(file.type)) {
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

function initUploadZoneClickFeedback() {
  const dropZone = document.getElementById("dropZone");
  if (!dropZone) return;

  const clearPressState = () => dropZone.classList.remove("click-active");

  dropZone.addEventListener("pointerdown", () => {
    dropZone.classList.add("click-active");
  });
  dropZone.addEventListener("pointerup", clearPressState);
  dropZone.addEventListener("pointerleave", clearPressState);
  dropZone.addEventListener("dragstart", clearPressState);
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
    updateUploadView();
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

document.addEventListener("DOMContentLoaded", initUploadZoneClickFeedback);
