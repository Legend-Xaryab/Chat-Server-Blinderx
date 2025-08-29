from flask import Flask, render_template, request, jsonify
import threading
import time
import uuid
import requests

app = Flask(__name__)

VALID_USERNAME = "admin"
VALID_PASSWORD = "secure123"
APP_ACCESS_TOKEN = "YOUR_APP_ACCESS_TOKEN"

tasks = {}

def send_facebook_message(token, recipient_id, message):
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={token}"
    payload = {"recipient":{"id":recipient_id},"message":{"text":message}}
    try:
        requests.post(url, json=payload)
    except:
        pass

def validate_facebook_token(token):
    url = "https://graph.facebook.com/debug_token"
    params = {"input_token": token, "access_token": APP_ACCESS_TOKEN}
    try:
        r = requests.get(url, params=params).json()
        return r.get("data",{}).get("is_valid",False)
    except:
        return False

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if username==VALID_USERNAME and password==VALID_PASSWORD:
        return jsonify({"success":True})
    return jsonify({"success":False, "error":"Invalid credentials"}), 401

@app.route("/start_task", methods=["POST"])
def start_task():
    data = request.json
    tokens = data.get("tokens",[])
    messages = data.get("messages",[])
    chatId = data.get("chatId")
    interval = int(data.get("interval",1))

    valid_tokens = [t for t in tokens if validate_facebook_token(t)]
    if not valid_tokens:
        return jsonify({"success":False,"error":"No valid tokens"}),400

    task_id = str(uuid.uuid4())
    tasks[task_id] = {"thread":None,"messages_sent":0,"active":True}

    def send_loop():
        idx_msg=0
        idx_token=0
        while tasks.get(task_id,{}).get("active",False):
            current_token = valid_tokens[idx_token % len(valid_tokens)]
            current_message = messages[idx_msg % len(messages)]
            send_facebook_message(current_token, chatId, current_message)
            tasks[task_id]["messages_sent"] +=1
            idx_msg+=1
            idx_token+=1
            time.sleep(interval)

    thread = threading.Thread(target=send_loop, daemon=True)
    tasks[task_id]["thread"] = thread
    thread.start()
    return jsonify({"success":True,"taskId":task_id})

@app.route("/stop_task", methods=["POST"])
def stop_task():
    data = request.json
    task_id = data.get("taskId")
    if task_id in tasks:
        tasks[task_id]["active"] = False
        return jsonify({"success":True})
    return jsonify({"success":False,"error":"Invalid Task ID"}),400

@app.route("/status/<task_id>")
def status(task_id):
    if task_id in tasks:
        return jsonify({"messages_sent":tasks[task_id]["messages_sent"]})
    return jsonify({"error":"Invalid Task ID"}),404

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)
