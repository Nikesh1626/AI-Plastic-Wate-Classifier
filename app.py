import os
import logging
from flask import Flask, render_template, request, jsonify
import numpy as np
import cv2
import base64
from tensorflow.keras.models import load_model
from services.gemini_service import get_classification_guidance, get_home_insights
from services.recycler_service import get_nearby_recyclers

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Reject oversized payloads early (default 8 MB, configurable via env).
MAX_CONTENT_LENGTH_MB = max(1, int(os.environ.get("MAX_CONTENT_LENGTH_MB", "8")))
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH_MB * 1024 * 1024

# Load trained model path from environment, fallback to project default
MODEL_PATH = os.environ.get("MODEL_PATH", "plastic-ai-project/model/plastic_model.h5")
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
model = load_model(MODEL_PATH)
# ⚠️ MUST MATCH training order exactly
CLASS_NAMES = ['HDPE', 'LDPE', 'OTHER', 'PET', 'PP', 'PS', 'PVC']


@app.route("/")
def index():
    insights = get_home_insights()
    return render_template(
        "index.html",
        home_tip=insights.get("tip", ""),
        home_fact=insights.get("fact", ""),
    )


@app.route("/predict", methods=["POST"])
def predict():
    try:
        body = request.get_json(silent=True) or {}
        data = body.get("image")
        if not isinstance(data, str) or "," not in data:
            return jsonify({"error": "Invalid image payload."}), 400

        # Decode base64 image
        img_data = base64.b64decode(data.split(",")[1])
        np_img = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"error": "Unable to decode image."}), 400

        # Preprocess
        img = cv2.resize(img, (224, 224))
        img = img / 255.0
        img = np.expand_dims(img, axis=0)

        # Predict
        preds = model.predict(img)
        class_index = int(np.argmax(preds))
        label = CLASS_NAMES[class_index]
        confidence = float(np.max(preds)) * 100

        guidance = get_classification_guidance(label, confidence)

        return jsonify({
            "type": label,
            "confidence": round(confidence, 2),
            "reuse": guidance.get("reuse_ideas", []),
            "recycle_instructions": guidance.get("recycling_instructions", []),
            "ai_advice": guidance.get("ai_advice", ""),
        })

    except Exception:
        app.logger.exception("Prediction failed")
        return jsonify({"error": "Prediction failed. Please try again."}), 500


@app.route("/recyclers", methods=["POST"])
def recyclers():
    try:
        body = request.get_json(silent=True) or {}
        lat = float(body["latitude"])
        lon = float(body["longitude"])

        radius = body.get("radius")
        if radius is not None:
            radius = max(500, int(radius))
            results = get_nearby_recyclers(lat, lon, radius=radius)
        else:
            results = get_nearby_recyclers(lat, lon)

        if isinstance(results, dict) and "error" in results:
            return jsonify(results), 502

        return jsonify(results)
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid request: {e}"}), 400
    except Exception:
        app.logger.exception("Recycler lookup failed")
        return jsonify({"error": "Unable to fetch recycling centres right now."}), 500


@app.route("/home-insights", methods=["GET"])
def home_insights():
    try:
        insights = get_home_insights()
        response = jsonify({
            "tip": insights.get("tip", ""),
            "fact": insights.get("fact", ""),
        })
        response.headers["Cache-Control"] = "no-store"
        return response
    except Exception:
        app.logger.exception("Home insights failed")
        return jsonify({"error": "Unable to load insights right now."}), 500


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(self), camera=(self)",
    )
    return response


if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG)