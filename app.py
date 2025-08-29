from flask import Flask, render_template, request, jsonify
import threading
import time
import uuid
import requests

app = Flask(__name__)

# ----------------- Configuration -----------------
VALID_USERNAME = "admin"
VALID_PASSWORD = "secure123"

tasks = {}

# ----------------- Facebook API -----------------
def send_facebook_message(token, recipient_id, message):
    """
    Sends a message using the provided token.
    Returns True if successful, False otherwise.
    """
    url = f"https://graph.facebook.com/v15.0/me/messages?access_token={token}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Failed to send message: {response.text}")
            return False
        return True
    except Exception as e:
        print(f"Send message error: {e}")
        return False

def validate_facebook_token(token):
    """
    Validates the token by calling the /me endpoint.
    Returns True if the token is valid.
    """
    try:
        response = requests.get(f"https://graph.facebook.com/v15.0/me?access_token={token}")
        data = response.json()
        return "id" in data
    except Exception as e:
        print(f"Token validation error: {e}")
        return False

# ----------------- Flask Routes -----------------
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

    # Validate tokens
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
    app.run(host="0.0.0.0", port=5000, debug=True)
