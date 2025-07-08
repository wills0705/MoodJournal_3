from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai
import requests
import os
from uuid import uuid4

# ==== Configuration ====
openai.api_key = "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"
SD_API_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"
SD_API_KEY = "sk-AVPjbBLDSRtGSbdYpsreO42BjzCJejwOuYxLgnN6B3P1hHgF"
IMAGE_DIR = './generated_images'
os.makedirs(IMAGE_DIR, exist_ok=True)

# ==== Flask App Setup ====
app = Flask(__name__)
CORS(app)  # CORS for all routes

# ========== ROUTES ==========

# ChatGPT narrative therapy route
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful mental assistant, this is a user's journal, help me write a narrative therapy, just give therapy itself, no other words"},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message['content']
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Image generation route using Stable Diffusion
@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.json
        prompt = data.get("prompt") if data else None
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        response = requests.post(
            SD_API_URL,
            headers={
                "authorization": f"Bearer {SD_API_KEY}",
                "accept": "image/*"
            },
            files={"none": ''},  # adjust if API requires actual file input
            data={
                "prompt": prompt,
                "output_format": "jpeg",
            },
        )

        if response.status_code == 200:
            filename = f"{uuid4()}.jpeg"
            filepath = os.path.join(IMAGE_DIR, filename)
            with open(filepath, 'wb') as file:
                file.write(response.content)
            return jsonify({
                "message": "Image generated successfully",
                "image_url": f"/generated_images/{filename}"
            }), 200
        else:
            try:
                error_content = response.json()
            except:
                error_content = response.text
            return jsonify({"error": error_content}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve image files
@app.route('/generated_images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_DIR, filename)

# ========== MAIN ==========
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
