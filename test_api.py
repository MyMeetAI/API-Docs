from enum import Enum
import time
import requests
import os
import uuid
import math

API_KEY = "YOUR_API_KEY"  # See https://app.mymeet.ai/settings
URL = "https://backend.mymeet.ai"


class TemplateType(Enum):
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


def record_meeting():
    url = URL + "/api/record-meeting"

    payload = {
        'api_key': API_KEY,
        'link': 'https://meet.google.com/zyj-qrmk-gvo',
        'meeting_password': '',  # Meeting password (optional)
        # UTC DateTime of meeting in cron format. To record NOW meeting leave it empty
        'cron': '30 12 25 4 *',
        'local_date_time': '2024-04-25T15:30:00+03:00',  # Local DateTime of meeting
        'title': 'Daily sync',
        'source': 'gmeet',  # [gmeet, zoom, yandextelemost, sberjazz]
        "template_name": TemplateType.DEFAULT.value,
    }

    response = requests.post(url, json=payload)
    print(response.text)


def upload_file():
    file_path = "PATH_TO_FILE"
    id = str(uuid.uuid4())
    file_size = os.path.getsize(file_path)
    chunk_size = 20 * 1024 * 1024  # 20 MB chunk size
    total_chunks = math.ceil(file_size / chunk_size)
    template_name = TemplateType.DEFAULT.value,
    speakers_number = 2
    meeting_id = "MEETING_ID"
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
                'template_name': template_name,
                'speakers_number': speakers_number,
                'meeting_id': meeting_id
            }

            # Send the chunk as part of the request
            files = {'file': chunk}
            response = requests.post(
                URL + "/api/video", data=data, files=files)
            response.raise_for_status()

            print(response.text)

            chunk_number += 1


def get_meeting_status():
    params = {
        'api_key': API_KEY,
        'meeting_id': "MEETING_ID"
    }
    response = requests.get(URL + "/api/meeting/status", params=params)
    print(response.text)


def get_meeting_json():
    params = {
        'api_key': API_KEY,
        'meeting_id': "MEETING_ID"
    }
    response = requests.get(URL + "/api/video/report", params=params)
    print(response.text)


def download_meeting():
    type = 'pdf'  # Available values : pdf, md, json, docx
    system_timezone = time.tzname[0]
    params = {
        'api_key': API_KEY,
        'meeting_id': "MEETING_ID",
        'format': type,
        'template_name': TemplateType.DEFAULT.value,
        'timezone': system_timezone
    }
    response = requests.get(URL + "/api/storage/download", params=params)
    if response.status_code == 200:
        # Save file
        with open(f'downloaded_file.{type}', 'wb') as file:
            file.write(response.content)
        print("File downloaded successfully")
    else:
        print("Failed to download file:", response.text)


def generate_new_template():
    url = URL + '/api/generate-new-template'

    data = {
        'api_key': API_KEY,
        'meeting_id': 'MEETING_ID',
        'template_name': TemplateType.DEFAULT.value,
    }

    response = requests.post(url, data=data)
    print(response.text)


def clear_transcript():
    url = URL + '/api/clear-transcript'

    data = {
        'api_key': API_KEY,
        'meeting_id': 'MEETING_ID'
    }

    response = requests.post(url, data=data)
    print(response.text)


def undo_clear_transcript():
    url = URL + '/api/undo-clear-transcript'

    data = {
        'api_key': API_KEY,
        'meeting_id': 'MEETING_ID'
    }

    response = requests.post(url, data=data)
    print(response.text)


def rename_meeting():
    url = URL + '/api/meeting'

    data = {
        'api_key': API_KEY,
        'meetingId': 'MEETING_ID',
        'newName': 'New Meeting Title'
    }

    response = requests.put(url, data=data)
    print(response.text)


def update_meeting_summary():
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

