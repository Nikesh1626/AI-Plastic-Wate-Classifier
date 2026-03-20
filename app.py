import os
from flask import Flask, render_template, request, jsonify
import numpy as np
import cv2
import base64
from tensorflow.keras.models import load_model
from plastic_info import plastic_info
from services.gemini_service import get_recycling_advice
from services.recycler_service import get_nearby_recyclers

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

app = Flask(__name__)

# Load trained model path from environment, fallback to project default
MODEL_PATH = os.environ.get("MODEL_PATH", "plastic-ai-project/model/plastic_model.h5")
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "true").strip().lower() in {
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
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json["image"]

        # Decode base64 image
        img_data = base64.b64decode(data.split(",")[1])
        np_img = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        # Preprocess
        img = cv2.resize(img, (224, 224))
        img = img / 255.0
        img = np.expand_dims(img, axis=0)

        # Predict
        preds = model.predict(img)
        class_index = int(np.argmax(preds))
        label = CLASS_NAMES[class_index]
        confidence = float(np.max(preds)) * 100

        info = plastic_info[label]
        ai_advice = get_recycling_advice(label, confidence)

        return jsonify({
            "type": label,
            "confidence": round(confidence, 2),
            "reuse": info["reuse"],
            "recycle": info["recycle"],
            "ai_advice": ai_advice,
        })

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/recyclers", methods=["POST"])
def recyclers():
    try:
        body = request.json
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG)