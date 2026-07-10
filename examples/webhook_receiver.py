"""Minimal webhook receiver for mymeet.ai meeting notifications.

How to run:
    pip install flask
    export FLASK_APP=webhook_receiver.py
    flask run

The endpoint must be reachable on a public HTTPS address (mymeet rejects
private/internal addresses such as localhost, 10.x, 192.168.x, cloud
metadata, or docker hostnames with a 400). For local development, expose
this server through a tunnel (e.g. ngrok, cloudflared) that gives you a
public HTTPS URL, and pass that URL as `webhook_url` when creating a meeting
via POST /api/record-meeting or POST /api/video.
"""
import hashlib, hmac, time
from flask import Flask, request

app = Flask(__name__)
SECRET = "YOUR_WEBHOOK_SECRET"  # the same value you passed as webhook_secret

@app.post("/mymeet-webhook")
def hook():
    ts = request.headers.get("X-Mymeet-Timestamp", "")
    signature = request.headers.get("X-Mymeet-Signature", "")
    expected = "sha256=" + hmac.new(
        SECRET.encode(), f"{ts}.".encode() + request.get_data(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return "bad signature", 401
    if abs(time.time() - int(ts)) > 300:  # anti-replay: reject timestamps older than 5 min
        return "stale timestamp", 401
    event = request.get_json()
    print(event["event"], event["meeting_id"], event["data"])
    return "", 200
