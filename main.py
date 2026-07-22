from fastapi import FastAPI, HTTPException 
from pydantic import BaseModel 
import httpx, jwt, time, json 
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

render_url = os.getenv('RENDER_URL')

TEAM_ID = os.getenv('TEAM_ID')
BUNDLE_ID = os.getenv('BUNDLE_ID')
KEY_ID = os.getenv('KEY_ID')
PRIVATE_KEY_PATH = os.getenv('PRIVATE_KEY_PATH')
PRIVATE_KEY = open(PRIVATE_KEY_PATH).read()
APNS_URL = os.getenv("APNS_URL")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN")
TOKENS_FILE = str(os.getenv('TOKENS_FILE'))

class DeviceRegistration(BaseModel):
    device_token: str 
    user_name: str 

class PersonDetected(BaseModel):
    person_name: str

class DetectionRequest(BaseModel):
    notification_type: str
    person_name: str
    confidence: float

class FaceEmbeddings(BaseModel): 
    face_embeddings: list[float]

class CLIPDescription(BaseModel): 
    known_unknown: str 
    sentence_description: str 
    

def generate_apns_token() -> str: 
    print(f'{TEAM_ID}, {PRIVATE_KEY}, {DEVICE_TOKEN}, {KEY_ID}')
    return jwt.encode(
        {'iss': TEAM_ID, 'iat': time.time()},
        PRIVATE_KEY, 
        algorithm = 'ES256',
        headers = {'kid': KEY_ID}
    )

def build_notification(detection: DetectionRequest) -> dict: 
    body = "URGENT - THERE IS SOMEONE DANGEROUS OUTSIDE"
    title = "John has arrived"
    confidence_pct = float(detection.confidence)
    detection_type = detection.notification_type 
    person_name = detection.person_name

    return {"aps": {
        "alert": {"title": title, "body": body},
        "sound": "default",
        "badge": 1,
        "mutable-content": 1
    }, 
    "detection_type": detection_type,
    "person_name": person_name, 
    "confidence": confidence_pct
    }

# can just do hard-coded prompts for each (start with VLM/move onto local CLIP)
# def build_notification(person_description: CLIPDescription) -> dict:
#     body = f'There is a {person_description.known_unknown} {person_description.sentence_description}'
#     title = 'Person outside'
#     return {'aps': {
#         'alert': {'title': title, 'body': body}, 
#         'sound': 'default', 
#         'badge': 1, 
#         'mutable-content': 1
#     }, 
#     'detection_type': detection_type, 
#     'person_name': person_name, 
#     'confidence'< }

def build_notification_face_rec(person_detected: PersonDetected) -> dict: 
    person_name = person_detected.person_name
    body = f'{person_name} has arrived'
    title = 'Family Member detected'
    return {
        'aps': {
            'alert': {'title': title, 'body': body},
            'sound': 'default',
            'badge': 1,
            'mutable-content': 1
        },
        'person_name': person_name
    }

async def send_push(token: str, payload: dict):
    apns_token = generate_apns_token()
    headers = {
        'authorization': f'bearer {apns_token}',
        'apns-topic': BUNDLE_ID, 
        'apns-push-type': 'alert',
        'apns-priority': '10', 
        'content-type': 'application/json'

    }
    async with httpx.AsyncClient(http2=True) as client: 
        response = await client.post(
            f'{APNS_URL}/3/device/{token}',
            headers = headers,
            content = json.dumps(payload)
        )
        print(response.status_code)
        print(response.text)
        return response


@app.post('/register')
async def retrieve_token(device: DeviceRegistration): 
    if device: 
        return {
            'device_token': device.device_token,
            'user_name': device.user_name}

def save_tokens(tokens: list[dict]) -> None: 
    with open(TOKENS_FILE, 'a', encoding='utf-8') as file:
        json.dump(tokens, file, indent = 2)


def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        return []
    with open(TOKENS_FILE, 'r', encoding='utf-8') as f: 
        try:
            return json.load(f)    
        except Exception as e: 
            print(f'Error when trying to open JSON: {e}')
            return []

@app.post(f'/detection')
async def handle_detection(detection: DetectionRequest):
    payload = build_notification(detection)
    print(f'built notification: {payload}')
    response = await send_push(DEVICE_TOKEN, payload)
    print(f'response: {response.text}')
    return {'apns_status': response.status_code, 'apns_body': response.text}

@app.post('/face_embeddings')
async def embed_face(face_embeddings: FaceEmbeddings):
    pass

@app.post('/person_description')
async def describe_person(person_description: PersonDescription): 
    if person_description: 
        person_status = person_description.known_unknown 
        sentence_description = person_description.sentence_description 
        return {'person_status': person_status, 'sentence_description': sentence_description}

@app.post('/facial_recognition_notification')
async def face_rec_notification(person_detected: PersonDetected):
    if person_detected:

        payload = build_notification_face_rec(person_detected)
        response = await send_push(DEVICE_TOKEN, payload)
        print(f'response: {response.text}')
        return {'apns_status': response.status_code, 'apns_body': response.text}

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    uvicorn.run('main:app', host='0.0.0.0', port=port, reload = False)