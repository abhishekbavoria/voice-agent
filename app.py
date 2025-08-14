chat_sessions = {}
from fastapi import FastAPI, Request, UploadFile, File, Path
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import requests
import time
import os
import assemblyai as aai
from dotenv import load_dotenv
from google import generativeai as genai

# Load environment variables
load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not ASSEMBLYAI_API_KEY:
    raise ValueError("ASSEMBLYAI_API_KEY not found in environment")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment")

# Configure APIs
aai.settings.api_key = ASSEMBLYAI_API_KEY
transcriber = aai.Transcriber()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.5-flash")

# FastAPI app
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with allowed domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files & templates
os.makedirs("uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Serve index HTML
@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Main conversational agent endpoint
@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str = Path(...), file: UploadFile = File(...)):
    try:
        start_time = time.time()

        # Step 1: Transcribe Audio
        audio_data = await file.read()
        transcript = transcriber.transcribe(audio_data)
        user_input = transcript.text
        print(f"User said: {user_input}")

        # Step 2: Manage session history
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        chat_sessions[session_id].append({"role": "user", "text": user_input})

        # Step 3: Build conversation prompt
        history_prompt = "\n".join(
            f"{msg['role'].capitalize()}: {msg['text']}" 
            for msg in chat_sessions[session_id]
        )

        # Step 4: Get AI response (Gemini)
        gemini_start = time.time()
        response = model.generate_content(history_prompt)
        ai_response = response.text.strip()
        print(f"AI replied: {ai_response}")
        print(f"Gemini processing time: {time.time() - gemini_start:.2f}s")

        # Step 5: Save AI reply in history
        chat_sessions[session_id].append({"role": "assistant", "text": ai_response})

        # Step 6: Convert AI text to audio (Murf)
        murf_payload = {
            "text": ai_response[:3000],  # Murf character limit
            "voiceId": "en-US-natalie",
            "format": "MP3"
        }
        murf_headers = {
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json"
        }
        murf_response = requests.post(
            "https://api.murf.ai/v1/speech/generate",
            json=murf_payload,
            headers=murf_headers
        )
        murf_response.raise_for_status()
        audio_url = murf_response.json().get("audioFile", "")

        print(f"Total agent processing time: {time.time() - start_time:.2f}s")

        return {
            "audio_url": audio_url
        }

    except Exception as e:
        print(f"Error in /agent/chat: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "audio_url": generate_fallback_audio(),
                "detail": str(e)
            }
        )

# Fallback audio for errors
def generate_fallback_audio():
    return "/static/fallback.mp3"
