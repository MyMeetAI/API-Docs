# mymeet.ai API

**English** | [Русский](README.ru.md)

Official documentation and code samples for the [mymeet.ai](https://mymeet.ai) public API:
send a bot to record online meetings, upload audio/video files, and fetch AI-generated
reports, transcripts and followups.

- 📘 Full interactive API reference: https://backend.mymeet.ai/docs/
- 🐍 Python snippets for every endpoint: [`test_api.py`](test_api.py)
- 🔔 Webhook receiver example: [`examples/webhook_receiver.py`](examples/webhook_receiver.py)

## Getting started

1. Register an account at https://app.mymeet.ai/
2. Get (or regenerate) your API key in your [account settings](https://app.mymeet.ai/settings/api-key)
   (Settings → API Key) — the key works with the workspace you select there.
3. The API works on paid plans: on the Free plan requests are rejected with
   `403 API key is not available on the free plan`. A workspace admin can also
   disable API access for a specific seat.
4. Explore and try requests in the interactive reference: https://backend.mymeet.ai/docs/

## Authentication

Send your API key in the `X-API-KEY` HTTP header on **every** request:

```python
import requests

API_KEY = "YOUR_API_KEY"
headers = {"X-API-KEY": API_KEY}

response = requests.get(
    "https://backend.mymeet.ai/api/meeting/status",
    params={"meeting_id": "MEETING_ID"},
    headers=headers,
)
print(response.text)
```

> ⚠️ The `X-API-KEY` header is the only supported way to pass the key.
> Passing it as an `api_key` query parameter or body field is a legacy
> mechanism that does **not** work with current-format keys and returns
> `401 Unauthorized`.

## MCP server

- https://github.com/MyMeetAI/mymeet-mcp-server
- https://mcp.mymeet.ai

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | [`/api/record-meeting`](#record-online-meeting) | Send a bot to record an online meeting |
| POST | [`/api/video`](#upload-file) | Upload an audio/video file |
| GET | [`/api/workspaces/active/all-meetings`](#get-meeting-list) | List meetings in the workspace |
| GET | [`/api/meeting/status`](#get-meeting-status) | Meeting status (single or batch) |
| GET | [`/api/video/report`](#get-meeting-json) | Full meeting report as JSON |
| DELETE | [`/api/video/report`](#delete-meeting) | Delete a meeting |
| GET | [`/api/storage/download`](#download-followup) | Download the followup (pdf / md / json / docx) |
| POST | [`/api/generate-new-template`](#generate-new-template) | Apply another report template to a meeting |
| POST | [`/api/clear-transcript`](#clear-transcript) | Clear the meeting transcript |
| POST | [`/api/undo-clear-transcript`](#undo-clear-transcript) | Restore a cleared transcript |
| PUT | [`/api/meeting`](#rename-meeting) | Rename a meeting |
| PUT | [`/api/meeting/{meetingId}/summary`](#update-meeting-summary) | Edit a summary block of the report |
| GET / POST | [`/api/workspaces/active/tags`](#meeting-tags) | Tag catalogue of the workspace |
| PUT / DELETE | [`/api/workspaces/active/meetings/{meetingId}/tags/{tagId}`](#meeting-tags) | Attach / detach a tag on a meeting |
| GET | [`/api/workspaces/active/meetings/search`](#meeting-tags) | Filter meetings by tag, title, source, author or date |

## Record online-meeting

`POST /api/record-meeting`

Supported platforms (`source`): `gmeet`, `zoom`, `yandextelemost`, `sberjazz`,
`trueconf`, `konturtalk`, `msteams`, `jitsi`, `mtslink`, `lark`.

```python
payload = {
    'link': 'https://meet.google.com/zyj-qrmk-gvo',
    'meeting_password': '',                          # optional
    'local_date_time': '2026-04-25T15:30:00+03:00',  # local datetime of the meeting
    'title': 'Daily sync',
    'source': 'gmeet',
    'template_name': 'default-meeting',              # see Templates below
    # Schedule for later — UTC cron, numeric one-shot values only
    # ('minute hour day month *', no '*'/lists in the first four fields,
    # at most 3 months ahead). Omit to record right now:
    # 'cron': '30 12 25 4 *',
    # 'participants': 'a@example.com, b@example.com', # optional: followup recipients
    'webhook_url': 'https://example.com/mymeet-webhook',  # optional, see Webhooks
    'webhook_secret': 'YOUR_WEBHOOK_SECRET_16_128',       # optional, see Webhooks
}
response = requests.post("https://backend.mymeet.ai/api/record-meeting",
                         json=payload, headers=headers)
print(response.text)
```

Responses: `200` OK, `401` unauthorized, `402` minutes limit is over,
`409` meeting already scheduled.

## Upload file

`POST /api/video`

We support the common video and audio formats. Upload the file in zero-based
data chunks, then send **one empty finalize marker** — `chunk_total` includes
that marker. The finalize response returns the `meeting_id`.

```python
import math, os, uuid

file_path = "PATH_TO_FILE"
file_id = str(uuid.uuid4())
file_name = os.path.basename(file_path)
file_size = os.path.getsize(file_path)
chunk_size = 20 * 1024 * 1024  # 20 MB per data chunk
data_chunks = max(1, math.ceil(file_size / chunk_size))

common = {
    'id': file_id,
    'chunk_total': data_chunks + 1,   # + one empty finalize marker
    'filename': file_name,
    'template_name': 'default-meeting',              # see Templates below
    'localTime': '2026-04-25T15:30:00+03:00',        # optional
    'title': 'Meeting Upload',                       # optional
    'speakers_number': 0,                            # optional, 0 = auto
    # Optional retry/integrity fields:
    # 'upload_session_id': str(uuid.uuid4()),  # new value per full upload attempt
    # 'expected_file_size': file_size,
    # 'expected_sha256': '<sha256-of-the-file>',
    'webhook_url': 'https://example.com/mymeet-webhook',  # optional, see Webhooks
    'webhook_secret': 'YOUR_WEBHOOK_SECRET_16_128',       # optional, see Webhooks
}

with open(file_path, 'rb') as f:
    for chunk_number in range(data_chunks):  # zero-based data chunks
        chunk = f.read(chunk_size)
        data = dict(common, chunk_number=chunk_number)
        files = {'file': (file_name, chunk, 'application/octet-stream')}
        response = requests.post("https://backend.mymeet.ai/api/video",
                                 data=data, files=files, headers=headers)
        response.raise_for_status()
        print(f"Chunk {chunk_number + 1}/{data_chunks} uploaded")

# Empty finalize marker: the server validates the upload and returns meeting_id
data = dict(common, chunk_number=data_chunks)
files = {'file': (file_name, b'', 'application/octet-stream')}
response = requests.post("https://backend.mymeet.ai/api/video",
                         data=data, files=files, headers=headers)
print(response.json())  # {"meeting_id": ..., "user_id": ...}
```

Notes:

- A single-request upload is `chunk_number=0` with `chunk_total=1`.
  Uploads that send data in the final request (`chunk_total` = number of data
  chunks, no empty marker) are also supported.
- For reliable retries keep `id` stable for the recording and generate a new
  `upload_session_id` for every full upload attempt.
- Supplying `expected_file_size` / `expected_sha256` enables end-to-end
  integrity validation before a meeting is created.

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

You can also set a default Webhook URL in your API integration settings — it
is used whenever `webhook_url` is omitted in the request; an explicit value in
the request takes priority.

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
`meeting.completed` — deduplicate by `X-Mymeet-Delivery` (unique per
notification). For `cron` schedules every firing records a meeting and sends
its own notification; the whole series shares the schedule's `meeting_id`
(the one returned by the scheduling request), each firing's report replacing
the previous one.

## Get meeting list

`GET /api/workspaces/active/all-meetings`

Returns a paginated list of meetings for the authenticated workspace.

```python
params = {
    'page': 0,      # page index, starts from 0
    'perPage': 10,  # meetings per page
}
response = requests.get("https://backend.mymeet.ai/api/workspaces/active/all-meetings",
                        params=params, headers=headers)
print(response.text)
```

## Get meeting status

`GET /api/meeting/status`

Pass either `meeting_id` (single meeting, plain-text response) or
`meeting_ids` (up to 100 comma-separated ids, JSON response) — when both are
present, `meeting_ids` wins.

```python
# Single meeting (plain-text response)
params = {'meeting_id': "MEETING_ID"}
response = requests.get("https://backend.mymeet.ai/api/meeting/status",
                        params=params, headers=headers)
print(response.text)

# Batch (JSON response)
params = {'meeting_ids': "MEETING_ID_1,MEETING_ID_2"}
response = requests.get("https://backend.mymeet.ai/api/meeting/status",
                        params=params, headers=headers)
print(response.json())
```

## Get meeting JSON

`GET /api/video/report`

Returns the full meeting report (transcript, speakers, chapters, templates)
as JSON.

```python
params = {'meeting_id': "MEETING_ID"}
response = requests.get("https://backend.mymeet.ai/api/video/report",
                        params=params, headers=headers)
print(response.json())
```

## Delete meeting

`DELETE /api/video/report`

```python
params = {'meeting_id': "MEETING_ID"}
response = requests.delete("https://backend.mymeet.ai/api/video/report",
                           params=params, headers=headers)
print(response.status_code)
```

## Download followup

`GET /api/storage/download`

```python
file_format = 'pdf'  # available values: pdf, md, json, docx
params = {
    'meeting_id': "MEETING_ID",
    'format': file_format,
    'timezone': 'UTC',                    # optional
    # 'template_name': 'default-meeting', # optional
    # 'include_report': 'false',          # optional: leave the AI report out
    # 'include_tasks': 'false',           # optional: leave the AI tasks block out
}
response = requests.get("https://backend.mymeet.ai/api/storage/download",
                        params=params, headers=headers)
if response.status_code == 200:
    with open(f'downloaded_file.{file_format}', 'wb') as file:
        file.write(response.content)
    print("File downloaded successfully")
else:
    print("Failed to download file:", response.text)
```

`include_report` and `include_tasks` (both default to `true`) are the same two
toggles as in the export dialog of the web app — "Add AI report" and "Add AI
tasks". Pass `false` to leave the AI report or the AI tasks block out of the
file; for `format=json` the tasks are removed from `followup_v2.templates` as
well. Any value other than `false` counts as `true`.

## Generate new template

`POST /api/generate-new-template`

Applies another report template to an already processed meeting. The response
includes `created_template_id` — use it as `templateId` in
[Update meeting summary](#update-meeting-summary).

```python
payload = {
    'meeting_id': 'MEETING_ID',
    'template_name': 'sales-meeting',  # see Templates below
}
response = requests.post("https://backend.mymeet.ai/api/generate-new-template",
                         json=payload, headers=headers)
print(response.json())  # {"followup": {...}, "created_template_id": "..."}
```

## Clear transcript

`POST /api/clear-transcript`

```python
payload = {'meeting_id': 'MEETING_ID'}
response = requests.post("https://backend.mymeet.ai/api/clear-transcript",
                         json=payload, headers=headers)
print(response.status_code)
```

## Undo clear transcript

`POST /api/undo-clear-transcript`

```python
payload = {'meeting_id': 'MEETING_ID'}
response = requests.post("https://backend.mymeet.ai/api/undo-clear-transcript",
                         json=payload, headers=headers)
print(response.status_code)
```

## Rename meeting

`PUT /api/meeting`

```python
payload = {
    'meetingId': 'MEETING_ID',
    'newName': 'New Meeting Title',
}
response = requests.put("https://backend.mymeet.ai/api/meeting",
                        json=payload, headers=headers)
print(response.status_code)
```

## Update meeting summary

`PUT /api/meeting/{meetingId}/summary`

`templateId` is the unique id of the applied template instance: take it from
`created_template_id` returned by [Generate new template](#generate-new-template),
or from the `followup_v2.templates[].id` field of the
[meeting report](#get-meeting-json).

```python
meeting_id = 'MEETING_ID'
payload = {
    'templateId': 'TEMPLATE_ID',
    'entityName': 'summary',  # see Entities below
    'newSummaryText': 'Updated summary text for the meeting',
}
response = requests.put(f"https://backend.mymeet.ai/api/meeting/{meeting_id}/summary",
                        json=payload, headers=headers)
print(response.status_code)
```

## Meeting tags

Tags are short labels (up to 24 characters, one of 8 colours) kept in a
per-workspace catalogue and attached to any number of meetings. The whole
workspace shares them: the web app and the API see the same tags. An
integration typically marks the meetings it has handled (`processed`,
`routed-to-crm`, `project-x`) and later filters by that tag, so you do not
need your own registry of processed meetings.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/workspaces/active/tags` | List the catalogue (cursor pagination: `perPage` ≤ 100, `cursor` = previous `nextCursor`) |
| POST | `/api/workspaces/active/tags` | Create a tag: `{"name": ..., "color": ...}` (`color` optional) |
| GET / PATCH / DELETE | `/api/workspaces/active/tags/{tagId}` | Read, rename / recolour, delete a tag |
| POST | `/api/workspaces/active/tags/{tagId}/restore` | Undo a deletion within 10 s (`{"deletionId": ...}` from the DELETE response) |
| GET | `/api/workspaces/active/meetings/{meetingId}/tags` | Tags of a meeting |
| POST | `/api/workspaces/active/meetings/{meetingId}/tags` | Create a tag and attach it in one call |
| PUT / DELETE | `/api/workspaces/active/meetings/{meetingId}/tags/{tagId}` | Attach / detach an existing tag (idempotent) |
| GET | `/api/workspaces/active/meetings/search?tagIds=ID1,ID2` | Meetings carrying **any** of the tags; also `q`, `scope=all\|my\|shared`, `sources`, `authors`, `dateFrom`, `dateTo`, `page`, `perPage` ≤ 50 |

Rules:

- Names are unique per workspace case-insensitively; a duplicate answers
  `409 TAG_NAME_EXISTS` — look the tag up in the catalogue instead. Colours:
  `blue`, `purple`, `orange`, `yellow`, `teal`, `green`, `red`, `grey`.
- Attaching and detaching require being an author of the meeting or a
  workspace owner/manager (`403 TAG_ACCESS_DENIED` otherwise). Any member of
  the workspace can create, rename or delete catalogue tags.
- Deleting a catalogue tag detaches it from every meeting.
- Errors are JSON `{"code": ..., "message": ..., "field": ...}`. Every
  mutation accepts an optional `mutationId` idempotency key: a repeat with the
  same key within 24 h returns the stored result instead of applying it twice.
- Meeting lists (`all-meetings`, `user-meetings`, `search`) and
  `GET /api/video/report` carry `tags` (the first two) and `tagsCount` for
  every meeting.

```python
BASE = "https://backend.mymeet.ai/api/workspaces/active"
meeting_id = "MEETING_ID"

# 1. Find the tag in the catalogue, create it when missing
response = requests.get(f"{BASE}/tags", params={'perPage': 100}, headers=headers)
by_name = {t['name'].casefold(): t['id'] for t in response.json()['tags']}
tag_id = by_name.get('processed')
if not tag_id:
    response = requests.post(f"{BASE}/tags",
                             json={'name': 'processed', 'color': 'green'}, headers=headers)
    tag_id = response.json()['tag']['id']

# 2. Attach it to the meeting (idempotent, safe to retry)
response = requests.put(f"{BASE}/meetings/{meeting_id}/tags/{tag_id}", headers=headers)
print(response.json())  # {"meetingId": ..., "tagId": ..., "assigned": true}

# 3. Later: meetings that carry the tag
response = requests.get(f"{BASE}/meetings/search",
                        params={'tagIds': tag_id, 'page': 0, 'perPage': 30}, headers=headers)
print(response.json()['total'])

# Detach
requests.delete(f"{BASE}/meetings/{meeting_id}/tags/{tag_id}", headers=headers)
```

## Templates

`template_name` values — the template defines the structure and style of the
report:

`default-meeting`, `sales-meeting`, `sales-coaching`, `hr-interview`,
`research-interview`, `team-sync`, `article`, `lecture-notes`, `one-to-one`,
`protocol`, `medicine`

## Entities

`entityName` values available in templates:

`summary`, `summary_agenda`, `sales_general`, `sales_coach`, `hr_summary`,
`questions_and_answers`, `research_insights`, `team_sync_agenda`,
`summary_by_speaker`, `workshop-double`, `seo-article-double`, `one_to_one`,
`med-anamnesis`, `protocol`, `template-recommendation`
