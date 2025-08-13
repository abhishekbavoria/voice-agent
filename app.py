chat_sessions = {}
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import shutil
import time
import os
import assemblyai as aai
from dotenv import load_dotenv
from google import generativeai as genai
from fastapi import Path

load_dotenv()

# Environment keys
MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not ASSEMBLYAI_API_KEY:
    raise ValueError("ASSEMBLYAI_API_KEY not found in environment")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment")

# AssemblyAI
aai.settings.api_key = ASSEMBLYAI_API_KEY
transcriber = aai.Transcriber()

# Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.5-flash")


# FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # CORS: development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
os.makedirs("uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Root route
@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Generate audio from text
class TextInput(BaseModel):
    text: str

@app.post("/generate-audio")
def generate_audio(data: TextInput):
    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": data.text,
        "voiceId": "en-US-natalie",
        "format": "MP3"
    }
    try:
        response = requests.post("https://api.murf.ai/v1/speech/generate", json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return {"audio_url": result.get("audioFile", "No URL returned")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Audio upload endpoint (optional helper)
@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    try:
        file_location = f"uploads/{int(time.time() * 1000)}-{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_location)

        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file_size
        }

    except Exception as e:
        return {"error": str(e)}


# Transcription only
@app.post("/transcribe/file")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        audio_data = await file.read()
        transcript = transcriber.transcribe(audio_data)
        return {"transcript": transcript.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# Echo Bot (Murf TTS after transcription)
@app.post("/tts/echo")
async def tts_echo(file: UploadFile = File(...)):
    try:
        audio_data = await file.read()

        transcript = transcriber.transcribe(audio_data)

        headers = {
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "text": transcript.text,
            "voiceId": "en-US-natalie",
            "format": "MP3"
        }

        murf_response = requests.post(
            "https://api.murf.ai/v1/speech/generate",
            headers=headers,
            json=payload
        )
        murf_response.raise_for_status()
        murf_data = murf_response.json()

        return {
            "audio_url": murf_data.get("audioFile", ""),
            "transcript": transcript.text
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/llm/query")
async def llm_query(file: UploadFile = File(...)):
    try:
        start_total = time.time()

        # Step 1: Transcription timing
        start = time.time()
        audio_data = await file.read()
        transcript = transcriber.transcribe(audio_data)
        user_text = transcript.text
        end = time.time()
        print(f"Transcription took {end - start:.2f} seconds")

        # Step 2: Gemini LLM timing
        start = time.time()
        gemini_response = model.generate_content(user_text)
        ai_response = gemini_response.text
        end = time.time()
        print(f"Gemini LLM response took {end - start:.2f} seconds")

        # Step 3: Murf TTS timing
        start = time.time()
        trimmed_text = ai_response[:3000]
        headers = {
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "text": trimmed_text,
            "voiceId": "en-US-natalie",
            "format": "MP3"
        }
        murf_response = requests.post("https://api.murf.ai/v1/speech/generate", headers=headers, json=payload)
        murf_response.raise_for_status()
        murf_data = murf_response.json()
        end = time.time()
        print(f"Murf TTS generation took {end - start:.2f} seconds")

        end_total = time.time()
        print(f"Total llm/query processing took {end_total - start_total:.2f} seconds")

        return {
            "transcript": user_text,
            "llm_response": ai_response,
            "audio_url": murf_data.get("audioFile", "")
        }

    except Exception as e:
        print(f"Error in llm/query: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "transcript": locals().get("user_text", ""),
                "llm_response": "I'm having trouble connecting right now.",
                "audio_url": generate_fallback_audio(),
                "detail": str(e)
            }
        )

    

@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str = Path(...), file: UploadFile = File(...)):
    try:
        start_time = time.time()

        # Step 1: Transcribe audio
        audio_data = await file.read()
        transcript = transcriber.transcribe(audio_data)
        user_input = transcript.text
        print(f"Transcript: {user_input}")

        # Step 2: Initialize or get chat history
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        # Step 3: Append user's message to history
        chat_sessions[session_id].append({"role": "user", "text": user_input})

        # Step 4: Create prompt with chat history
        history_prompt = "\n".join(
            f"{msg['role'].capitalize()}: {msg['text']}" for msg in chat_sessions[session_id]
        )

        # Step 5: Call Gemini
        gemini_start = time.time()
        response = model.generate_content(history_prompt)
        ai_response = response.text.strip()
        print(f"Gemini response: {ai_response}")
        print(f"Gemini response time: {time.time() - gemini_start:.2f} sec")

        # Step 6: Append AI response to history
        chat_sessions[session_id].append({"role": "assistant", "text": ai_response})

        # Step 7: Call Murf TTS
        murf_start = time.time()
        trimmed_response = ai_response[:3000]
        murf_payload = {
            "text": trimmed_response,
            "voiceId": "en-US-natalie",
            "format": "MP3"
        }
        murf_headers = {
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json"
        }

        murf_response = requests.post("https://api.murf.ai/v1/speech/generate", json=murf_payload, headers=murf_headers)
        murf_response.raise_for_status()
        audio_url = murf_response.json().get("audioFile", "")
        print(f"Murf TTS time: {time.time() - murf_start:.2f} sec")

        # Final response
        print(f"Total time: {time.time() - start_time:.2f} sec")
        return {
            "transcript": user_input,
            "llm_response": ai_response,
            "audio_url": audio_url
        }

    except Exception as e:
        print(f"Error in /agent/chat: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "transcript": locals().get("user_input", ""),
                "llm_response": "I'm having trouble connecting right now.",
                "audio_url": generate_fallback_audio(),
                "detail": str(e)
            }
        )

    
def generate_fallback_audio():
    return "/static/fallback.mp3"
