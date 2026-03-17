import os
import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


def _default_radius_from_env() -> int:
    raw_value = os.environ.get("RECYCLER_RADIUS_METERS", "5000").strip()
    try:
        return max(500, int(raw_value))
    except ValueError:
        return 5000


def _overpass_endpoints() -> list:
    raw = os.environ.get(
        "OVERPASS_ENDPOINTS",
        "https://overpass-api.de/api/interpreter,"
        "https://overpass.kumi.systems/api/interpreter,"
        "https://lz4.overpass-api.de/api/interpreter",
    )
    endpoints = [item.strip() for item in raw.split(",") if item.strip()]
    return endpoints or ["https://overpass-api.de/api/interpreter"]


DEFAULT_RADIUS_METERS = _default_radius_from_env()
OVERPASS_ENDPOINTS = _overpass_endpoints()


def _build_query(lat: float, lon: float, radius: int) -> str:
    # Keep query lightweight to reduce timeout probability on busy mirrors.
    return f"""
[out:json][timeout:20];
(
  node["amenity"="recycling"](around:{radius},{lat},{lon});
  way["amenity"="recycling"](around:{radius},{lat},{lon});
  relation["amenity"="recycling"](around:{radius},{lat},{lon});
);
out center;
"""


def _extract_results(elements: list) -> list:
    results = []
    seen = set()

    for element in elements:
        tags = element.get("tags", {})

        if element.get("type") == "node":
            elem_lat = element.get("lat")
            elem_lon = element.get("lon")
        else:
            center = element.get("center", {})
            elem_lat = center.get("lat")
            elem_lon = center.get("lon")

        if elem_lat is None or elem_lon is None:
            continue

        name = (
            tags.get("name")
            or tags.get("operator")
            or tags.get("brand")
            or "Recycling Centre"
        )
        contact = (
            tags.get("phone")
            or tags.get("contact:phone")
            or tags.get("opening_hours")
            or ""
        )

        unique_key = (name.lower(), round(float(elem_lat), 5), round(float(elem_lon), 5))
        if unique_key in seen:
            continue
        seen.add(unique_key)

        results.append(
            {
                "name": name,
                "lat": elem_lat,
                "lon": elem_lon,
                "contact": contact,
            }
        )

    return results


def get_nearby_recyclers(lat: float, lon: float, radius: int = DEFAULT_RADIUS_METERS) -> list:
    """
    Queries Overpass API mirrors for recycling centres near supplied coords.
    Returns a list of dicts: {name, lat, lon, contact}.
    """
    attempt_radii = [max(500, int(radius)), max(500, int(radius // 2))]
    endpoint_errors = []

    for attempt_radius in attempt_radii:
        query = _build_query(lat, lon, attempt_radius)

        for endpoint in OVERPASS_ENDPOINTS:
            try:
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    timeout=25,
                    headers={"User-Agent": "PlasticAIClassifier/1.0"},
                )
                response.raise_for_status()
                elements = response.json().get("elements", [])
                return _extract_results(elements)
            except requests.Timeout:
                endpoint_errors.append(f"Timeout from {endpoint}")
            except requests.RequestException as exc:
                endpoint_errors.append(f"{endpoint}: {exc}")
            except Exception as exc:
                endpoint_errors.append(f"{endpoint}: unexpected error {exc}")

    return {
        "error": (
            "Recycling-center servers are currently busy or unreachable. "
            "Please try again in 1-2 minutes."
        ),
        "details": endpoint_errors[:3],
    }
