from flask import Flask, render_template, request, jsonify
import threading
import time
import uuid
import requests

app = Flask(__name__)

# ----------------- Login credentials -----------------
VALID_USERNAME = "admin"        # Change this to your username
VALID_PASSWORD = "secure123"    # Change this to your password

# ----------------- Facebook App Token -----------------
APP_ACCESS_TOKEN = "YOUR_APP_ACCESS_TOKEN"  # Replace with your Facebook App token

# ----------------- Task storage -----------------
tasks = {}

# ----------------- Facebook API -----------------
def send_facebook_message(token, recipient_id, message):
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={token}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }
    response = requests.post(url, json=payload)
    return response.json()

def validate_facebook_token(token):
    url = "https://graph.facebook.com/debug_token"
    params = {
        "input_token": token,
        "access_token": APP_ACCESS_TOKEN
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if "data" in data and data["data"].get("is_valid"):
            return True
        return False
    except Exception as e:
        print(f"Token validation error: {e}")
        return False

# ----------------- Routes -----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route("/validate_token", methods=["POST"])
def validate_token_endpoint():
    data = request.json
    token = data.get("token")
    is_valid = validate_facebook_token(token)
    return jsonify({"valid": is_valid})

@app.route("/start_task", methods=["POST"])
def start_task():
    data = request.json
    tokens = data.get("tokens", [])
    messages = data.get("messages", [])
    chat_id = data.get("chatId")
    interval = int(data.get("interval", 1))

    valid_tokens = [t for t in tokens if validate_facebook_token(t)]
    if not valid_tokens:
        return jsonify({"success": False, "error": "No valid tokens provided"}), 400

    task_id = str(uuid.uuid4())

    def send_messages():
        idx_msg = 0
        idx_token = 0
        while task_id in tasks:
            current_token = valid_tokens[idx_token % len(valid_tokens)]
            current_message = messages[idx_msg % len(messages)]
            try:
                send_facebook_message(current_token, chat_id, current_message)
            except Exception as e:
                print(f"Error sending message: {e}")
            tasks[task_id]["messages_sent"] += 1
            idx_msg += 1
            idx_token += 1
            time.sleep(interval)

    tasks[task_id] = {"thread": threading.Thread(target=send_messages, daemon=True), "messages_sent": 0}
    tasks[task_id]["thread"].start()

    return jsonify({"success": True, "taskId": task_id})

@app.route("/stop_task", methods=["POST"])
def stop_task():
    data = request.json
    task_id = data.get("taskId")
    if task_id in tasks:
        del tasks[task_id]
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid Task ID"}), 400

@app.route("/status/<task_id>")
def status(task_id):
    if task_id in tasks:
        return jsonify({"messages_sent": tasks[task_id]["messages_sent"]})
    return jsonify({"error": "Invalid Task ID"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
