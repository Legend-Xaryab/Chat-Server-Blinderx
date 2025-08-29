from flask import Flask, request, jsonify, render_template
import threading, time, uuid, requests, os

app = Flask(__name__)
tasks = {}  # Store tasks: {task_id: {"thread": thread, "messages_sent": int, "active": bool}}

# --- Helper function to send message ---
def send_facebook_message(token, chat_id, message):
    try:
        # Replace with real Facebook API if needed
        url = f"https://graph.facebook.com/v17.0/me/messages"
        headers = {"Authorization": f"Bearer {token}"}
        data = {"recipient": {"id": chat_id}, "message": {"text": message}}
        r = requests.post(url, json=data, headers=headers, timeout=5)
        return r.status_code == 200
    except:
        return False

# --- Home page ---
@app.route("/")
def index():
    return render_template("index.html")

# --- Start messaging task ---
@app.route("/start_task", methods=["POST"])
def start_task():
    data = request.get_json()
    tokens = data.get("tokens", [])
    messages = data.get("messages", [])
    chat_id = data.get("chatId")
    interval = int(data.get("interval", 1))

    if not tokens or not messages or not chat_id or interval < 1:
        return jsonify({"success": False, "error": "All fields are required"}), 400

    valid_tokens = tokens.copy()
    invalid_tokens = []

    task_id = str(uuid.uuid4())
    tasks[task_id] = {"thread": None, "messages_sent": 0, "active": True}

    def message_loop():
        msg_index = 0
        token_index = 0
        while tasks.get(task_id, {}).get("active", False):
            current_token = valid_tokens[token_index % len(valid_tokens)]
            current_message = messages[msg_index % len(messages)]

            success = send_facebook_message(current_token, chat_id, current_message)
            if not success:
                invalid_tokens.append(current_token)
                valid_tokens.remove(current_token)

            tasks[task_id]["messages_sent"] += 1
            msg_index += 1
            token_index += 1

            if not valid_tokens:
                tasks[task_id]["active"] = False
                break

            time.sleep(interval)

    thread = threading.Thread(target=message_loop, daemon=True)
    tasks[task_id]["thread"] = thread
    thread.start()

    return jsonify({
        "success": True,
        "taskId": task_id,
        "accepted_tokens": tokens,
        "invalid_tokens_initially": invalid_tokens
    })

# --- Stop task ---
@app.route("/stop_task", methods=["POST"])
def stop_task():
    data = request.get_json()
    task_id = data.get("taskId")
    if task_id in tasks:
        tasks[task_id]["active"] = False
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid Task ID"}), 400

# --- Task status ---
@app.route("/status/<task_id>", methods=["GET"])
def status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404
    return jsonify({
        "messages_sent": task["messages_sent"],
        "active": task["active"]
    })

# --- Main entry ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
