import requests
import os
import uuid
import math

API_KEY = "YOUR_API_KEY"  # See https://app.mymeet.ai/settings
URL = "https://backend.mymeet.ai"


def record_meeting():
    payload = {
        'api_key': API_KEY,
        'link': 'https://meet.google.com/zyj-qrmk-gvo',
        # UTC DateTime of meeting in cron format. To record NOW meeting leave it empty
        'cron': '30 12 25 4 *',
        'local_date_time': '2024-04-25T15:30:00+03:00',  # Local DateTime of meeting
        'title': 'Daily sync',
        'source': 'gmeet'  # [gmeet, zoom, yandextelemost, sberjazz]
    }
    response = requests.post(URL + "/api/record-meeting", json=payload)
    print(response.text)


def upload_file():
    file_path = "PATH_TO_FILE"
    id = str(uuid.uuid4())
    file_size = os.path.getsize(file_path)
    total_chunks = math.ceil(file_size / chunk_size)
    with open(file_path, 'rb') as file:
        chunk_size = 20 * 1024 * 1024  # 20 MB chunk size
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
            }

            # Send the chunk as part of the request
            files = {'file': chunk}
            response = requests.post(
                URL + "/api/video", data=data, files=files)
            response.raise_for_status()

            print(response.text)

            chunk_number += 1


def get_meetings_list():
    params = {
        'api_key': API_KEY,
        'page': 0,
        'perPage': 10
    }
    response = requests.get(URL + "/api/storage/list", params=params)
    print(response.text)


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
    params = {
        'api_key': API_KEY,
        'meeting_id': "MEETING_ID",
        'format': type
    }
    response = requests.get(URL + "/api/storage/download", params=params)
    if response.status_code == 200:
        # Save file
        with open(f'downloaded_file.{type}', 'wb') as file:
            file.write(response.content)
        print("File downloaded successfully")
    else:
        print("Failed to download file:", response.text)
