# Pre-requirements
1) Register account on https://app.mymeet.ai/
2) Go to Settings https://app.mymeet.ai/settings
3) You will see section with your unique API key and Docs button
![изображение](https://github.com/MyMeetAI/API-Docs/assets/23313519/7b72261c-b4d3-462e-a6cf-1412df19b786)
4) You can try some requests from [Swagger UI](https://backend.mymeet.ai/docs/)

# API methods
Example code on Python [here](https://github.com/MyMeetAI/API-Docs/blob/main/test_api.py).
## Record online-meeting
Now we support recording meeting from Google Meet, Zoom, Yandex.Telemost and SberJazz.
Here is sample code to record your online meeting and process after it finished:
```
payload = {
    'api_key': API_KEY,
    'link': 'https://meet.google.com/zyj-qrmk-gvo',
    # UTC DateTime of meeting in cron format. To record NOW meeting leave it empty
    'cron': '30 12 25 4 *',
    'local_date_time': '2024-04-25T15:30:00+03:00',  # Local DateTime of meeting
    'title': 'Daily sync',
    'source': 'gmeet'  # [gmeet, zoom, yandextelemost, sberjazz]
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
        }

        # Send the chunk as part of the request
        files = {'file': chunk}
        response = requests.post("https://backend.mymeet.ai/api/video", data=data, files=files)
        response.raise_for_status()

        print(response.text)

        chunk_number += 1
```

## Get meeting list
```
params = {
    'api_key': API_KEY,
    'page': 0,
    'perPage': 10
}
response = requests.get("https://backend.mymeet.ai/api/storage/list", params=params)
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
