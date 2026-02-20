from flask import Flask, render_template, request, jsonify
import numpy as np
import cv2
import base64
from tensorflow.keras.models import load_model
from plastic_info import plastic_info

app = Flask(__name__)

# Load trained model
model = load_model("plastic-ai-project/model/plastic_model.h5")
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

        return jsonify({
            "type": label,
            "confidence": round(confidence, 2),
            "reuse": info["reuse"],
            "recycle": info["recycle"]
        })

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)