// map.js — Leaflet map + Overpass API recycling centre discovery
// Depends on: Leaflet.js (loaded via CDN in index.html)

let leafletMap = null;

/**
 * Initialises (or re-initialises) the Leaflet map centred on user's location.
 * @param {number} lat
 * @param {number} lon
 */
function initMap(lat, lon) {
  if (leafletMap) {
    leafletMap.remove();
    leafletMap = null;
  }

  const mapEl = document.getElementById("map");
  mapEl.style.display = "block";

  leafletMap = L.map("map").setView([lat, lon], 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(leafletMap);

  // Blue dot for user's position
  L.circleMarker([lat, lon], {
    radius: 9,
    color: "#1565c0",
    fillColor: "#2196f3",
    fillOpacity: 0.9,
    weight: 3,
  })
    .addTo(leafletMap)
    .bindPopup("<b>📍 Your Location</b>")
    .openPopup();

  // Force Leaflet to recalculate size after display:none → block transition
  setTimeout(() => leafletMap.invalidateSize(), 150);
}

/**
 * Green recycling-pin icon for Leaflet markers.
 * Falls back to a simple circle if the CDN image fails.
 */
function getRecyclingIcon() {
  return L.icon({
    iconUrl:
      "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png",
    shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  });
}

/**
 * Requests the user's geolocation, renders the map, and fetches nearby
 * recycling centres from the /recyclers backend endpoint.
 */
function findNearbyRecyclers() {
  const placeholder = document.getElementById("mapPlaceholder");
  const statusMsg = document.getElementById("mapStatusMsg");

  if (!navigator.geolocation) {
    placeholder.innerHTML = `
      <i class="bi bi-exclamation-circle-fill text-danger display-5"></i>
      <p class="text-danger mt-3">Geolocation is not supported by your browser.</p>`;
    return;
  }

  placeholder.style.display = "none";
  statusMsg.style.display = "block";
  statusMsg.innerHTML = `
    <div class="spinner-border spinner-border-sm text-success me-2" role="status"></div>
    Detecting your location…`;

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;

      statusMsg.innerHTML = `
        <div class="spinner-border spinner-border-sm text-success me-2" role="status"></div>
        Searching for recycling centres nearby…`;

      initMap(lat, lon);

      fetch("/recyclers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ latitude: lat, longitude: lon }),
      })
        .then((res) => res.json())
        .then((data) => {
          statusMsg.style.display = "none";

          if (!Array.isArray(data)) {
            showMapError(data.error || "Unexpected response from server.");
            return;
          }

          if (data.length === 0) {
            showMapError(
              "No recycling centres found within 5 km of your location.",
            );
            return;
          }

          const icon = getRecyclingIcon();
          data.forEach((centre) => {
            const contact = centre.contact
              ? `<br><i class="bi bi-telephone-fill text-success me-1"></i>${centre.contact}`
              : "";
            L.marker([centre.lat, centre.lon], { icon })
              .addTo(leafletMap)
              .bindPopup(`<b>♻️ ${centre.name}</b>${contact}`);
          });

          // Fit map bounds to include all markers + user
          const allLatLngs = [[lat, lon], ...data.map((c) => [c.lat, c.lon])];
          leafletMap.fitBounds(allLatLngs, { padding: [40, 40] });
        })
        .catch((err) => {
          statusMsg.style.display = "none";
          showMapError("Network error while fetching recycling centres.");
          console.error(err);
        });
    },
    (err) => {
      statusMsg.style.display = "none";
      placeholder.style.display = "block";
      placeholder.innerHTML = `
        <i class="bi bi-geo-slash display-4 text-danger"></i>
        <p class="text-danger mt-3">
          Location access denied or unavailable.<br>
          <small class="text-muted">Please allow location permission in your browser and try again.</small>
        </p>
        <button class="btn btn-outline-success mt-2" onclick="resetMapPlaceholder()">
          <i class="bi bi-arrow-counterclockwise me-1"></i>Try Again
        </button>`;
      console.warn("Geolocation error:", err);
    },
    { timeout: 15000, maximumAge: 60000 },
  );
}

function showMapError(message) {
  const statusMsg = document.getElementById("mapStatusMsg");
  statusMsg.style.display = "block";
  statusMsg.innerHTML = `
    <i class="bi bi-exclamation-circle-fill text-danger me-2"></i>
    ${message}
    <button class="btn btn-sm btn-outline-secondary ms-3" onclick="resetMapPlaceholder()">
      <i class="bi bi-arrow-counterclockwise me-1"></i>Try Again
    </button>`;
}

function resetMapPlaceholder() {
  const placeholder = document.getElementById("mapPlaceholder");
  const statusMsg = document.getElementById("mapStatusMsg");
  const mapEl = document.getElementById("map");

  if (leafletMap) {
    leafletMap.remove();
    leafletMap = null;
  }
  mapEl.style.display = "none";
  statusMsg.style.display = "none";
  placeholder.style.display = "block";
  placeholder.innerHTML = `
    <i class="bi bi-map display-4 text-muted"></i>
    <p class="text-muted mt-3">
      Click <strong>Find Near Me</strong> to discover recycling centres near your location.
    </p>`;
}
