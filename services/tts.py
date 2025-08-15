import os
import requests
from dotenv import load_dotenv

load_dotenv()
MURF_API_KEY = os.getenv("MURF_API_KEY")

def synthesize_audio(text: str) -> str:
    payload = {
        "text": text[:3000],  # Murf character limit
        "voiceId": "en-US-natalie",
        "format": "MP3"
    }
    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(
        "https://api.murf.ai/v1/speech/generate",
        json=payload,
        headers=headers
    )
    response.raise_for_status()
    return response.json().get("audioFile", "")
