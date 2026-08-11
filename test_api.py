"""Python snippets for the mymeet.ai public API.

Full interactive reference: https://backend.mymeet.ai/docs/

Authentication: pass your API key in the X-API-KEY header on every request.
Get (or regenerate) your key in your account settings:
https://app.mymeet.ai/settings/api-key — the key works with the workspace
selected there, on paid plans only (Free -> 403).
"""
from enum import Enum
import math
import os
import uuid

import requests

API_KEY = "YOUR_API_KEY"  # https://app.mymeet.ai/settings/api-key
URL = "https://backend.mymeet.ai"
HEADERS = {"X-API-KEY": API_KEY}


class TemplateType(Enum):
    """template_name values — the template defines the report structure."""

    DEFAULT = "default-meeting"
    SALES = "sales-meeting"
    SALES_COACHING = "sales-coaching"
    HR = "hr-interview"
    RESEARCH = "research-interview"
    TEAM = "team-sync"
    ARTICLE = "article"
    LECTURE = "lecture-notes"
    ONE_TO_ONE = "one-to-one"
    PROTOCOL = "protocol"
    MEDICINE = "medicine"


class EntityType(Enum):
    """entityName values available in templates."""

    SUMMARY = "summary"
    SUMMARY_AGENDA = "summary_agenda"
    SALES_GENERAL = "sales_general"
    SALES_COACH = "sales_coach"
    HR_SUMMARY = "hr_summary"
    QUESTIONS_AND_ANSWERS = "questions_and_answers"
    RESEARCH_INSIGHTS = "research_insights"
    TEAM_SYNC_AGENDA = "team_sync_agenda"
    SUMMARY_BY_SPEAKER = "summary_by_speaker"
    WORKSHOP_DOUBLE = "workshop-double"
    SEO_ARTICLE_DOUBLE = "seo-article-double"
    ONE_TO_ONE = "one_to_one"
    MED_ANAMNESIS = "med-anamnesis"
    PROTOCOL = "protocol"
    TEMPLATE_RECOMMENDATION = "template-recommendation"


def record_meeting():
    """POST /api/record-meeting — send a bot to record an online meeting."""
    payload = {
        'link': 'https://meet.google.com/zyj-qrmk-gvo',
        'meeting_password': '',                          # optional
        'local_date_time': '2026-04-25T15:30:00+03:00',  # local datetime of the meeting
        'title': 'Daily sync',
        # gmeet, zoom, yandextelemost, sberjazz, trueconf, konturtalk,
        # msteams, jitsi, mtslink, lark
        'source': 'gmeet',
        'template_name': TemplateType.DEFAULT.value,
        # Schedule for later — UTC cron, numeric one-shot values only
        # ('minute hour day month *', at most 3 months ahead).
        # Omit to record right now:
        # 'cron': '30 12 25 4 *',
        # 'participants': 'a@example.com, b@example.com',  # optional: followup recipients
        # Optional webhooks (see README — Webhooks):
        # 'webhook_url': 'https://example.com/mymeet-webhook',
        # 'webhook_secret': 'YOUR_WEBHOOK_SECRET_16_128',
    }

    response = requests.post(URL + "/api/record-meeting", json=payload, headers=HEADERS)
    print(response.text)


def upload_file():
    """POST /api/video — upload a file in data chunks + one empty finalize marker."""
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
        'template_name': TemplateType.DEFAULT.value,
        'localTime': '2026-04-25T15:30:00+03:00',        # optional
        'title': 'Meeting Upload',                       # optional
        'speakers_number': 0,                            # optional, 0 = auto
        # Optional retry/integrity fields:
        # 'upload_session_id': str(uuid.uuid4()),  # new value per full upload attempt
        # 'expected_file_size': file_size,
        # 'expected_sha256': '<sha256-of-the-file>',
        # Optional webhooks (see README — Webhooks):
        # 'webhook_url': 'https://example.com/mymeet-webhook',
        # 'webhook_secret': 'YOUR_WEBHOOK_SECRET_16_128',
    }

    with open(file_path, 'rb') as f:
        for chunk_number in range(data_chunks):  # zero-based data chunks
            chunk = f.read(chunk_size)
            data = dict(common, chunk_number=chunk_number)
            files = {'file': (file_name, chunk, 'application/octet-stream')}
            response = requests.post(URL + "/api/video", data=data, files=files, headers=HEADERS)
            response.raise_for_status()
            print(f"Chunk {chunk_number + 1}/{data_chunks} uploaded")

    # Empty finalize marker: the server validates the upload and returns meeting_id
    data = dict(common, chunk_number=data_chunks)
    files = {'file': (file_name, b'', 'application/octet-stream')}
    response = requests.post(URL + "/api/video", data=data, files=files, headers=HEADERS)
    print(response.json())  # {"meeting_id": ..., "user_id": ...}


def get_meeting_list():
    """GET /api/workspaces/active/all-meetings — paginated meeting list."""
    params = {
        'page': 0,      # page index, starts from 0
        'perPage': 10,  # meetings per page
    }
    response = requests.get(URL + "/api/workspaces/active/all-meetings",
                            params=params, headers=HEADERS)
    print(response.text)


def get_meeting_status():
    """GET /api/meeting/status — single meeting (plain-text response)."""
    params = {
        'meeting_id': "MEETING_ID"
    }
    response = requests.get(URL + "/api/meeting/status", params=params, headers=HEADERS)
    print(response.text)


def get_meeting_status_batch():
    """GET /api/meeting/status — up to 100 comma-separated ids (JSON response)."""
    params = {
        'meeting_ids': "MEETING_ID_1,MEETING_ID_2"
    }
    response = requests.get(URL + "/api/meeting/status", params=params, headers=HEADERS)
    print(response.json())


def get_meeting_json():
    """GET /api/video/report — full meeting report as JSON."""
    params = {
        'meeting_id': "MEETING_ID"
    }
    response = requests.get(URL + "/api/video/report", params=params, headers=HEADERS)
    print(response.json())


def delete_meeting():
    """DELETE /api/video/report — delete a meeting."""
    params = {
        'meeting_id': "MEETING_ID"
    }
    response = requests.delete(URL + "/api/video/report", params=params, headers=HEADERS)
    print(response.status_code)


def download_meeting():
    """GET /api/storage/download — download the followup as pdf/md/json/docx."""
    file_format = 'pdf'  # available values: pdf, md, json, docx
    params = {
        'meeting_id': "MEETING_ID",
        'format': file_format,
        'timezone': 'UTC',                             # optional
        'template_name': TemplateType.DEFAULT.value,   # optional
    }
    response = requests.get(URL + "/api/storage/download", params=params, headers=HEADERS)
    if response.status_code == 200:
        with open(f'downloaded_file.{file_format}', 'wb') as file:
            file.write(response.content)
        print("File downloaded successfully")
    else:
        print("Failed to download file:", response.text)


def generate_new_template():
    """POST /api/generate-new-template — apply another template to a meeting.

    The response includes `created_template_id` — use it as `templateId`
    in update_meeting_summary().
    """
    payload = {
        'meeting_id': 'MEETING_ID',
        'template_name': TemplateType.SALES.value,
    }
    response = requests.post(URL + '/api/generate-new-template',
                             json=payload, headers=HEADERS)
    print(response.json())  # {"followup": {...}, "created_template_id": "..."}


def clear_transcript():
    """POST /api/clear-transcript — clear the meeting transcript."""
    payload = {
        'meeting_id': 'MEETING_ID'
    }
    response = requests.post(URL + '/api/clear-transcript', json=payload, headers=HEADERS)
    print(response.status_code)


def undo_clear_transcript():
    """POST /api/undo-clear-transcript — restore a cleared transcript."""
    payload = {
        'meeting_id': 'MEETING_ID'
    }
    response = requests.post(URL + '/api/undo-clear-transcript', json=payload, headers=HEADERS)
    print(response.status_code)


def rename_meeting():
    """PUT /api/meeting — rename a meeting."""
    payload = {
        'meetingId': 'MEETING_ID',
        'newName': 'New Meeting Title',
    }
    response = requests.put(URL + '/api/meeting', json=payload, headers=HEADERS)
    print(response.status_code)


def update_meeting_summary():
    """PUT /api/meeting/{meetingId}/summary — edit a summary block of the report.

    `templateId` is the unique id of the applied template instance: take it
    from `created_template_id` returned by generate_new_template(), or from
    the `followup_v2.templates[].id` field of the meeting report.
    """
    meeting_id = 'MEETING_ID'
    payload = {
        'templateId': 'TEMPLATE_ID',
        'entityName': EntityType.SUMMARY.value,
        'newSummaryText': 'Updated summary text for the meeting',
    }
    response = requests.put(f'{URL}/api/meeting/{meeting_id}/summary',
                            json=payload, headers=HEADERS)
    print(response.status_code)
