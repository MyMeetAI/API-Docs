"""Minimal webhook receiver for mymeet.ai meeting notifications.

How to run:
    pip install fastapi uvicorn
    uvicorn webhook_receiver:app

The endpoint must be reachable on a public HTTPS address (mymeet rejects
private/internal addresses such as localhost, 10.x, 192.168.x, cloud
metadata, or docker hostnames with a 400). For local development, expose
this server through a tunnel (e.g. ngrok, cloudflared) that gives you a
public HTTPS URL, and pass that URL as `webhook_url` when creating a meeting
via POST /api/record-meeting or POST /api/video.
"""
import hashlib, hmac, time
from fastapi import FastAPI, Request, Response

app = FastAPI()
SECRET = "YOUR_WEBHOOK_SECRET"  # the same value you passed as webhook_secret

@app.post("/mymeet-webhook")
async def hook(request: Request):
    raw_body = await request.body()
    ts = request.headers.get("x-mymeet-timestamp", "")
    signature = request.headers.get("x-mymeet-signature", "")
    expected = "sha256=" + hmac.new(
        SECRET.encode(), f"{ts}.".encode() + raw_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return Response("bad signature", status_code=401)
    if abs(time.time() - int(ts)) > 300:  # anti-replay: reject timestamps older than 5 min
        return Response("stale timestamp", status_code=401)
    event = await request.json()
    print(event["event"], event["meeting_id"], event["data"])
    return Response(status_code=200)
