# Pre-requirements

1. Register account on https://app.mymeet.ai/
2. API is only available for B2B clients. Contact [sales team](https://mymeet.ai/contact) to get your API key.
3. You can try some requests from [Swagger UI](https://backend.mymeet.ai/docs/)

# API methods

Example code on Python [here](https://github.com/MyMeetAI/API-Docs/blob/main/test_api.py).

# MCP server

https://github.com/MyMeetAI/mymeet-mcp-server

https://mcp.mymeet.ai


## Record online-meeting

Now we support recording meeting from Google Meet, Zoom, Yandex.Telemost and SberJazz.
Here is sample code to record your online meeting and process after it finished:

```
payload = {
    'api_key': API_KEY,
    'link': 'https://meet.google.com/zyj-qrmk-gvo',
    'meeting_password': '', # Meeting password (optional)
    # UTC DateTime of meeting in cron format. To record NOW meeting leave it empty
    'cron': '30 12 25 4 *',
    'local_date_time': '2024-04-25T15:30:00+03:00',  # Local DateTime of meeting
    'title': 'Daily sync',
    'source': 'gmeet',  # [gmeet, zoom, yandextelemost, sberjazz]
    'webhook_url': 'https://example.com/mymeet-webhook',  # optional: get notified when the report is ready, see Webhooks below
    'webhook_secret': 'YOUR_WEBHOOK_SECRET_16_128',        # optional: sign notifications
}
response = requests.post("https://backend.mymeet.ai/api/record-meeting", json=payload)
print(response.text)
```

NOTE: More info about [cron](https://docs.oracle.com/cd/E12058_01/doc/doc.1014/e12030/cron_expressions.htm).

## Upload file

We support different video and audio formats.
Here is sample code to upload file and process meeting:

```
file_path = "PATH_TO_FILE"
id = str(uuid.uuid4())
file_size = os.path.getsize(file_path)
chunk_size = 20 * 1024 * 1024  # 20 MB chunk size
total_chunks = math.ceil(file_size / chunk_size)
with open(file_path, 'rb') as file:
    chunk_number = 0
    while True:
        chunk = file.read(chunk_size)
        if not chunk:
            break  # Reached EOF

        # Construct the request parameters
        data = {
            'api_key': API_KEY,
            'id': id,
            'chunk_number': chunk_number,
            'chunk_total': total_chunks,
            'filename': os.path.basename(file_path),
            'localTime': '2024-04-25T15:30:00+03:00',  # Local DateTime
            'webhook_url': 'https://example.com/mymeet-webhook',  # optional: get notified when the report is ready, see Webhooks below
            'webhook_secret': 'YOUR_WEBHOOK_SECRET_16_128',        # optional: sign notifications
        }

        # Send the chunk as part of the request
        files = {'file': chunk}
        response = requests.post("https://backend.mymeet.ai/api/video", data=data, files=files)
        response.raise_for_status()

        print(response.text)

        chunk_number += 1
```

## Webhooks

Instead of polling `GET /api/meeting/status`, pass an optional `webhook_url`
(plus an optional `webhook_secret`, 16-128 chars) when creating a meeting via
`POST /api/record-meeting` or `POST /api/video`. When processing finishes,
mymeet sends a POST notification to your URL and you fetch the report with
`GET /api/video/report` as usual.

A minimal receiver example (FastAPI) is available at
[`examples/webhook_receiver.py`](examples/webhook_receiver.py).

### Step 0 — prepare an endpoint

Expose an HTTPS endpoint on a public address that accepts `POST` with a JSON
body and responds `2xx` quickly (under 10s). Private/internal addresses
(`localhost`, `10.x`, `192.168.x`, cloud metadata, docker hostnames) are
rejected with `400`. Minimal FastAPI receiver
(`pip install fastapi uvicorn`, run: `uvicorn webhook_receiver:app`):

```python
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
```

### Step 1 — pass the URL when creating a meeting

See the `webhook_url` / `webhook_secret` fields in the [Record online-meeting](#record-online-meeting)
and [Upload file](#upload-file) samples above.

### Step 2 — receive notifications

Two events are sent:

`meeting.completed` — the report is ready:

```
POST {webhook_url}
Content-Type: application/json
User-Agent: mymeet-webhook/1.0
X-Mymeet-Event: meeting.completed
X-Mymeet-Delivery: 0b0e9a3e-8b0e-4a52-9c8e-2f6f3f1c2d4e
X-Mymeet-Timestamp: 1783425600
X-Mymeet-Signature: sha256=<hex>   (only when webhook_secret is set)

{"event": "meeting.completed", "meeting_id": "...",
 "timestamp": "2026-07-07T12:00:00Z",
 "data": {"title": "Daily sync", "is_transcript_empty": false,
          "report_url": "https://backend.mymeet.ai/api/video/report?meeting_id=..."}}
```

`meeting.failed` — the bot could not record the meeting, or processing
failed. Sent with the same headers as `meeting.completed`. `data` contains
a short `reason` string: the recording-failure reason reported by the bot
when there is one (the same value `GET /api/meeting/status` shows for such
meetings), or a generic `Recording failed` / `Processing failed` /
`Limit is reached` (the workspace ran out of minutes mid-processing):

```
{"event": "meeting.failed", "meeting_id": "...",
 "timestamp": "2026-07-07T12:00:00Z",
 "data": {"reason": "Recording failed"}}
```

### Step 3 — verify the signature (when you set `webhook_secret`)

`X-Mymeet-Signature = "sha256=" + hex(HMAC_SHA256(webhook_secret,
"{X-Mymeet-Timestamp}.{raw_request_body}"))` — see the receiver above; always
compare with `hmac.compare_digest` and reject stale timestamps.

### Step 4 — fetch the report

On `meeting.completed`, call the `report_url` from the payload (it is
`GET /api/video/report?meeting_id=...`) with your API key.

### Delivery, retries & idempotency

Timeout 10s; any `2xx` counts as delivered. On connection errors, timeouts,
`5xx`, `408` or `429` mymeet retries up to 5 times (~1m, 5m, 15m, 1h, 3h, with
jitter); other `4xx` are not retried. Delivery is **at-least-once**: after a
manual restart of a failed meeting you may receive `meeting.failed` and later
`meeting.completed` — deduplicate by `meeting_id` + `event`. For `cron`
schedules every firing produces its own meeting and sends its own notification
with that meeting's `meeting_id`; deleting the schedule stops the
notifications.

## Get meeting list DEPRECATED!!! Gives only old meetings. Use approach bellow

```
params = {
    'api_key': API_KEY,
    'page': 0,
    'perPage': 10
}
response = requests.get("https://backend.mymeet.ai/api/storage/list", params=params)
print(response.text)
```

## Use this istead
## Get meeting list
```
params = {
    'api_key': API_KEY,
    'page': 0,
    'perPage': 10
}
response = requests.get("https://backend.mymeet.ai/api/workspaces/active/all-meetings", params=params)
print(response.text)
```

## Get meeting status

```
params = {
    'api_key': API_KEY,
    'meeting_id': "MEETING_ID"
}
response = requests.get("https://backend.mymeet.ai/api/meeting/status", params=params)
print(response.text)
```

## Get meeting JSON

```
params = {
    'api_key': API_KEY,
    'meeting_id': "MEETING_ID"
}
response = requests.get("https://backend.mymeet.ai/api/video/report", params=params)
print(response.text)
```

## Download followup

```
type = 'pdf'  # Available values : pdf, md, json, docx
params = {
    'api_key': API_KEY,
    'meeting_id': "MEETING_ID",
    'format': type
}
response = requests.get("https://backend.mymeet.ai/api/storage/download", params=params)
if response.status_code == 200:
    # Save file
    with open(f'downloaded_file.{type}', 'wb') as file:
        file.write(response.content)
    print("File downloaded successfully")
else:
    print("Failed to download file:", response.text)
```

## Generate new template

```
url = URL + '/api/generate-new-template'

data = {
    'api_key': API_KEY,
    'meeting_id': 'MEETING_ID',
    'template_name': 'default-meeting',
}

response = requests.post(url, data=data)
print(response.text)
```

## Clear transcript

```
url = URL + '/api/clear-transcript'

data = {
    'api_key': API_KEY,
    'meeting_id': 'MEETING_ID'
}

response = requests.post(url, data=data)
print(response.text)
```

## Undo clear transcript

```
url = URL + '/api/undo-clear-transcript'

data = {
    'api_key': API_KEY,
    'meeting_id': 'MEETING_ID'
}

response = requests.post(url, data=data)
print(response.text)
```

## Rename meeting

```
url = URL + '/api/meeting'

data = {
    'api_key': API_KEY,
    'meetingId': 'MEETING_ID',
    'newName': 'New Meeting Title'
}

response = requests.put(url, data=data)
print(response.text)
```

## Update meeting summary

```
meeting_id = 'MEETING_ID'
url = f'{URL}/api/meeting/{meeting_id}/summary'

data = {
    'api_key': API_KEY,
    'templateName': TemplateType.DEFAULT.value,
    'entityName': EntityType.SUMMARY.value,
    'newSummaryText': 'Updated summary text for the meeting'
}

response = requests.put(url, data=data)
print(response.text)
```
