from flask import Flask, request, jsonify
from flask_cors import CORS  # ✅ Import this
import openai
import os

app = Flask(__name__)
CORS(app)  # ✅ Enable CORS

openai.api_key = "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"

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

if __name__ == "__main__":
    app.run(debug=True)
