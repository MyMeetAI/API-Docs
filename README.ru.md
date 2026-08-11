# mymeet.ai API

[English](README.md) | **Русский**

Официальная документация и примеры кода публичного API [mymeet.ai](https://mymeet.ai):
отправляйте бота записывать онлайн-встречи, загружайте аудио/видео файлы и получайте
AI-отчёты, транскрипты и фоллоу-апы.

- 📘 Полный интерактивный справочник API: https://backend.mymeet.ai/docs/
- 🐍 Python-примеры для каждого эндпоинта: [`test_api.py`](test_api.py)
- 🔔 Пример приёмника вебхуков: [`examples/webhook_receiver.py`](examples/webhook_receiver.py)

## С чего начать

1. Зарегистрируйте аккаунт на https://app.mymeet.ai/
2. Получите (или перевыпустите) API-ключ в [настройках аккаунта](https://app.mymeet.ai/ru/settings/api-key)
   («Настройки API → API Ключ») — ключ работает с воркспейсом, который вы там выберете.
3. API работает на платных тарифах: на Free запросы отклоняются с
   `403 API key is not available on the free plan`. Админ воркспейса также
   может запретить API-доступ для конкретного места.
4. Изучайте и пробуйте запросы в интерактивном справочнике: https://backend.mymeet.ai/docs/

## Аутентификация

Передавайте API-ключ в HTTP-заголовке `X-API-KEY` в **каждом** запросе:

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

> ⚠️ Заголовок `X-API-KEY` — единственный поддерживаемый способ передачи ключа.
> Передача через query-параметр или поле body `api_key` — легаси-механизм,
> который **не работает** с ключами актуального формата и возвращает
> `401 Unauthorized`.

## MCP-сервер

- https://github.com/MyMeetAI/mymeet-mcp-server
- https://mcp.mymeet.ai

## Эндпоинты

| Метод | Эндпоинт | Назначение |
|---|---|---|
| POST | [`/api/record-meeting`](#запись-онлайн-встречи) | Отправить бота записать онлайн-встречу |
| POST | [`/api/video`](#загрузка-файла) | Загрузить аудио/видео файл |
| GET | [`/api/workspaces/active/all-meetings`](#список-встреч) | Список встреч воркспейса |
| GET | [`/api/meeting/status`](#статус-встречи) | Статус встречи (одной или пачкой) |
| GET | [`/api/video/report`](#отчёт-по-встрече-json) | Полный отчёт по встрече в JSON |
| DELETE | [`/api/video/report`](#удаление-встречи) | Удалить встречу |
| GET | [`/api/storage/download`](#скачать-фоллоу-ап) | Скачать фоллоу-ап (pdf / md / json / docx) |
| POST | [`/api/generate-new-template`](#применить-другой-шаблон) | Применить другой шаблон отчёта к встрече |
| POST | [`/api/clear-transcript`](#очистить-транскрипт) | Очистить транскрипт встречи |
| POST | [`/api/undo-clear-transcript`](#восстановить-транскрипт) | Восстановить очищенный транскрипт |
| PUT | [`/api/meeting`](#переименовать-встречу) | Переименовать встречу |
| PUT | [`/api/meeting/{meetingId}/summary`](#изменить-блок-отчёта) | Изменить блок summary в отчёте |

## Запись онлайн-встречи

`POST /api/record-meeting`

Поддерживаемые платформы (`source`): `gmeet`, `zoom`, `yandextelemost`, `sberjazz`,
`trueconf`, `konturtalk`, `msteams`, `jitsi`, `mtslink`, `lark`.

```python
payload = {
    'link': 'https://meet.google.com/zyj-qrmk-gvo',
    'meeting_password': '',                          # опционально
    'local_date_time': '2026-04-25T15:30:00+03:00',  # локальное время встречи
    'title': 'Daily sync',
    'source': 'gmeet',
    'template_name': 'default-meeting',              # см. раздел «Шаблоны»
    # Запись по расписанию — UTC cron, только числовые one-shot значения
    # ('минута час день месяц *', без '*'/списков в первых четырёх полях,
    # не дальше 3 месяцев вперёд). Уберите поле, чтобы записать прямо сейчас:
    # 'cron': '30 12 25 4 *',
    # 'participants': 'a@example.com, b@example.com', # опционально: получатели фоллоу-апа
    'webhook_url': 'https://example.com/mymeet-webhook',  # опционально, см. «Вебхуки»
    'webhook_secret': 'YOUR_WEBHOOK_SECRET_16_128',       # опционально, см. «Вебхуки»
}
response = requests.post("https://backend.mymeet.ai/api/record-meeting",
                         json=payload, headers=headers)
print(response.text)
```

Ответы: `200` OK, `401` не авторизован, `402` закончились минуты,
`409` встреча уже запланирована.

## Загрузка файла

`POST /api/video`

Поддерживаются распространённые видео- и аудиоформаты. Файл загружается
чанками (нумерация с нуля), после которых отправляется **один пустой
финализирующий маркер** — `chunk_total` включает этот маркер. Ответ на
финализацию возвращает `meeting_id`.

```python
import math, os, uuid

file_path = "PATH_TO_FILE"
file_id = str(uuid.uuid4())
file_name = os.path.basename(file_path)
file_size = os.path.getsize(file_path)
chunk_size = 20 * 1024 * 1024  # 20 МБ на чанк
data_chunks = max(1, math.ceil(file_size / chunk_size))

common = {
    'id': file_id,
    'chunk_total': data_chunks + 1,   # + один пустой финализирующий маркер
    'filename': file_name,
    'template_name': 'default-meeting',              # см. раздел «Шаблоны»
    'localTime': '2026-04-25T15:30:00+03:00',        # опционально
    'title': 'Meeting Upload',                       # опционально
    'speakers_number': 0,                            # опционально, 0 = авто
    # Опциональные поля для ретраев и проверки целостности:
    # 'upload_session_id': str(uuid.uuid4()),  # новое значение на каждую попытку загрузки
    # 'expected_file_size': file_size,
    # 'expected_sha256': '<sha256-файла>',
    'webhook_url': 'https://example.com/mymeet-webhook',  # опционально, см. «Вебхуки»
    'webhook_secret': 'YOUR_WEBHOOK_SECRET_16_128',       # опционально, см. «Вебхуки»
}

with open(file_path, 'rb') as f:
    for chunk_number in range(data_chunks):  # чанки с данными, нумерация с нуля
        chunk = f.read(chunk_size)
        data = dict(common, chunk_number=chunk_number)
        files = {'file': (file_name, chunk, 'application/octet-stream')}
        response = requests.post("https://backend.mymeet.ai/api/video",
                                 data=data, files=files, headers=headers)
        response.raise_for_status()
        print(f"Чанк {chunk_number + 1}/{data_chunks} загружен")

# Пустой финализирующий маркер: сервер проверяет загрузку и возвращает meeting_id
data = dict(common, chunk_number=data_chunks)
files = {'file': (file_name, b'', 'application/octet-stream')}
response = requests.post("https://backend.mymeet.ai/api/video",
                         data=data, files=files, headers=headers)
print(response.json())  # {"meeting_id": ..., "user_id": ...}
```

Примечания:

- Загрузка одним запросом — `chunk_number=0` с `chunk_total=1`.
  Загрузки, где данные идут в последнем запросе (`chunk_total` = число чанков
  с данными, без пустого маркера), тоже поддерживаются.
- Для надёжных ретраев сохраняйте `id` неизменным для записи и генерируйте
  новый `upload_session_id` на каждую полную попытку загрузки.
- Поля `expected_file_size` / `expected_sha256` включают сквозную проверку
  целостности до создания встречи.

## Вебхуки

Вместо поллинга `GET /api/meeting/status` передайте опциональный `webhook_url`
(плюс опциональный `webhook_secret`, 16–128 символов) при создании встречи
через `POST /api/record-meeting` или `POST /api/video`. Когда обработка
завершится, mymeet отправит POST-уведомление на ваш URL, и вы заберёте отчёт
через `GET /api/video/report` как обычно.

Минимальный пример приёмника (FastAPI):
[`examples/webhook_receiver.py`](examples/webhook_receiver.py).

### Шаг 0 — подготовьте эндпоинт

Поднимите HTTPS-эндпоинт на публичном адресе, который принимает `POST` с
JSON-телом и быстро (до 10 с) отвечает `2xx`. Приватные/внутренние адреса
(`localhost`, `10.x`, `192.168.x`, cloud metadata, docker-хосты) отклоняются
с `400`. Минимальный приёмник на FastAPI
(`pip install fastapi uvicorn`, запуск: `uvicorn webhook_receiver:app`):

```python
import hashlib, hmac, time
from fastapi import FastAPI, Request, Response

app = FastAPI()
SECRET = "YOUR_WEBHOOK_SECRET"  # то же значение, что вы передали в webhook_secret

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
    if abs(time.time() - int(ts)) > 300:  # анти-replay: отклоняем метки старше 5 минут
        return Response("stale timestamp", status_code=401)
    event = await request.json()
    print(event["event"], event["meeting_id"], event["data"])
    return Response(status_code=200)
```

### Шаг 1 — передайте URL при создании встречи

См. поля `webhook_url` / `webhook_secret` в примерах
[записи встречи](#запись-онлайн-встречи) и [загрузки файла](#загрузка-файла) выше.

Также можно задать дефолтный Webhook URL в настройках API-интеграции — он
используется, когда `webhook_url` в запросе не передан; явное значение в
запросе имеет приоритет.

### Шаг 2 — принимайте уведомления

Отправляются два события:

`meeting.completed` — отчёт готов:

```
POST {webhook_url}
Content-Type: application/json
User-Agent: mymeet-webhook/1.0
X-Mymeet-Event: meeting.completed
X-Mymeet-Delivery: 0b0e9a3e-8b0e-4a52-9c8e-2f6f3f1c2d4e
X-Mymeet-Timestamp: 1783425600
X-Mymeet-Signature: sha256=<hex>   (только при заданном webhook_secret)

{"event": "meeting.completed", "meeting_id": "...",
 "timestamp": "2026-07-07T12:00:00Z",
 "data": {"title": "Daily sync", "is_transcript_empty": false,
          "report_url": "https://backend.mymeet.ai/api/video/report?meeting_id=..."}}
```

`meeting.failed` — бот не смог записать встречу или обработка упала.
Отправляется с теми же заголовками, что и `meeting.completed`. В `data` —
короткая строка `reason`: причина неудачной записи от бота, если она есть
(то же значение показывает `GET /api/meeting/status` для таких встреч), либо
общая `Recording failed` / `Processing failed` / `Limit is reached`
(в воркспейсе закончились минуты в процессе обработки):

```
{"event": "meeting.failed", "meeting_id": "...",
 "timestamp": "2026-07-07T12:00:00Z",
 "data": {"reason": "Recording failed"}}
```

### Шаг 3 — проверяйте подпись (если задан `webhook_secret`)

`X-Mymeet-Signature = "sha256=" + hex(HMAC_SHA256(webhook_secret,
"{X-Mymeet-Timestamp}.{raw_request_body}"))` — см. приёмник выше; всегда
сравнивайте через `hmac.compare_digest` и отклоняйте устаревшие метки времени.

### Шаг 4 — заберите отчёт

На `meeting.completed` вызовите `report_url` из payload (это
`GET /api/video/report?meeting_id=...`) со своим API-ключом.

### Доставка, ретраи и идемпотентность

Таймаут 10 с; любой `2xx` считается доставкой. При ошибках соединения,
таймаутах, `5xx`, `408` и `429` mymeet повторяет до 5 раз (~1м, 5м, 15м, 1ч,
3ч, с джиттером); остальные `4xx` не ретраятся. Доставка —
**at-least-once**: после ручного перезапуска упавшей встречи вы можете
получить `meeting.failed`, а затем `meeting.completed` — дедуплицируйте по
`X-Mymeet-Delivery` (уникален для каждого уведомления). Для `cron`-расписаний
каждое срабатывание записывает встречу и шлёт своё уведомление; вся серия
делит `meeting_id` расписания (тот, что вернул запрос на планирование),
отчёт каждого срабатывания замещает предыдущий.

## Список встреч

`GET /api/workspaces/active/all-meetings`

Возвращает постраничный список встреч воркспейса.

```python
params = {
    'page': 0,      # индекс страницы, с 0
    'perPage': 10,  # встреч на страницу
}
response = requests.get("https://backend.mymeet.ai/api/workspaces/active/all-meetings",
                        params=params, headers=headers)
print(response.text)
```

## Статус встречи

`GET /api/meeting/status`

Передайте либо `meeting_id` (одна встреча, ответ — plain text), либо
`meeting_ids` (до 100 id через запятую, ответ — JSON) — если переданы оба,
приоритет у `meeting_ids`.

```python
# Одна встреча (ответ — plain text)
params = {'meeting_id': "MEETING_ID"}
response = requests.get("https://backend.mymeet.ai/api/meeting/status",
                        params=params, headers=headers)
print(response.text)

# Пачкой (ответ — JSON)
params = {'meeting_ids': "MEETING_ID_1,MEETING_ID_2"}
response = requests.get("https://backend.mymeet.ai/api/meeting/status",
                        params=params, headers=headers)
print(response.json())
```

## Отчёт по встрече (JSON)

`GET /api/video/report`

Возвращает полный отчёт по встрече (транскрипт, спикеры, главы, шаблоны)
в формате JSON.

```python
params = {'meeting_id': "MEETING_ID"}
response = requests.get("https://backend.mymeet.ai/api/video/report",
                        params=params, headers=headers)
print(response.json())
```

## Удаление встречи

`DELETE /api/video/report`

```python
params = {'meeting_id': "MEETING_ID"}
response = requests.delete("https://backend.mymeet.ai/api/video/report",
                           params=params, headers=headers)
print(response.status_code)
```

## Скачать фоллоу-ап

`GET /api/storage/download`

```python
file_format = 'pdf'  # доступные значения: pdf, md, json, docx
params = {
    'meeting_id': "MEETING_ID",
    'format': file_format,
    'timezone': 'UTC',                    # опционально
    # 'template_name': 'default-meeting', # опционально
}
response = requests.get("https://backend.mymeet.ai/api/storage/download",
                        params=params, headers=headers)
if response.status_code == 200:
    with open(f'downloaded_file.{file_format}', 'wb') as file:
        file.write(response.content)
    print("Файл скачан")
else:
    print("Не удалось скачать файл:", response.text)
```

## Применить другой шаблон

`POST /api/generate-new-template`

Применяет другой шаблон отчёта к уже обработанной встрече. В ответе есть
`created_template_id` — используйте его как `templateId` в
[изменении блока отчёта](#изменить-блок-отчёта).

```python
payload = {
    'meeting_id': 'MEETING_ID',
    'template_name': 'sales-meeting',  # см. раздел «Шаблоны»
}
response = requests.post("https://backend.mymeet.ai/api/generate-new-template",
                         json=payload, headers=headers)
print(response.json())  # {"followup": {...}, "created_template_id": "..."}
```

## Очистить транскрипт

`POST /api/clear-transcript`

```python
payload = {'meeting_id': 'MEETING_ID'}
response = requests.post("https://backend.mymeet.ai/api/clear-transcript",
                         json=payload, headers=headers)
print(response.status_code)
```

## Восстановить транскрипт

`POST /api/undo-clear-transcript`

```python
payload = {'meeting_id': 'MEETING_ID'}
response = requests.post("https://backend.mymeet.ai/api/undo-clear-transcript",
                         json=payload, headers=headers)
print(response.status_code)
```

## Переименовать встречу

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

## Изменить блок отчёта

`PUT /api/meeting/{meetingId}/summary`

`templateId` — уникальный id применённого экземпляра шаблона: возьмите его из
`created_template_id` в ответе [применения шаблона](#применить-другой-шаблон)
или из поля `followup_v2.templates[].id` в [отчёте по встрече](#отчёт-по-встрече-json).

```python
meeting_id = 'MEETING_ID'
payload = {
    'templateId': 'TEMPLATE_ID',
    'entityName': 'summary',  # см. раздел «Сущности»
    'newSummaryText': 'Обновлённый текст summary',
}
response = requests.put(f"https://backend.mymeet.ai/api/meeting/{meeting_id}/summary",
                        json=payload, headers=headers)
print(response.status_code)
```

## Шаблоны

Значения `template_name` — шаблон определяет структуру и стиль отчёта:

`default-meeting`, `sales-meeting`, `sales-coaching`, `hr-interview`,
`research-interview`, `team-sync`, `article`, `lecture-notes`, `one-to-one`,
`protocol`, `medicine`

## Сущности

Значения `entityName`, доступные в шаблонах:

`summary`, `summary_agenda`, `sales_general`, `sales_coach`, `hr_summary`,
`questions_and_answers`, `research_insights`, `team_sync_agenda`,
`summary_by_speaker`, `workshop-double`, `seo-article-double`, `one_to_one`,
`med-anamnesis`, `protocol`, `template-recommendation`
