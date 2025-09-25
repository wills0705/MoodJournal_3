from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
import requests
import os
from uuid import uuid4

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
SD_API_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"
SD_API_KEY = "sk-HIEZJFa0CsiGdJ5YFj3HypdNlegSSNv3X1I1RGsY8YV1YOQj"
IMAGE_DIR = './generated_images'
os.makedirs(IMAGE_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app)  

# ChatGPT narrative therapy route
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who helps the user to reflect and be expressive when they are journaling. Based on a user's journal, generate 5 - 6 reflective questions using narrative therapy techniques. Just give therapy itself, no other words."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message.content
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
            files={"none": ''},
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
