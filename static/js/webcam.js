const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const resultDiv = document.getElementById("result");

// Access webcam
navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
        video.srcObject = stream;
    })
    .catch(err => {
        alert("Webcam access denied!");
        console.error(err);
    });

function captureImage() {
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, 224, 224);

    const imageData = canvas.toDataURL("image/jpeg");

    fetch("/predict", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ image: imageData })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            resultDiv.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
            return;
        }

        resultDiv.innerHTML = `
            <h3>Result</h3>
            <p><b>Plastic Type:</b> ${data.type}</p>
            <p><b>Confidence:</b> ${data.confidence}%</p>
            <p><b>Reuse Ideas:</b></p>
            <ul>${data.reuse.map(r => `<li>${r}</li>`).join("")}</ul>
            <p><b>Recycling Info:</b> ${data.recycle}</p>
        `;
    })
    .catch(err => {
        console.error(err);
        resultDiv.innerHTML = "<p style='color:red;'>Prediction failed</p>";
    });
}