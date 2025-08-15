import os
import time
import logging

from fastapi import FastAPI, Request, UploadFile, File, Path
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from schemas import AgentChatResponse
from services.stt import transcribe_audio
from services.llm import get_ai_reply
from services.tts import synthesize_audio

load_dotenv()

app = FastAPI()
logger = logging.getLogger("voice_agent")
logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, use allowed origins only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

chat_sessions = {}

@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/agent/chat/{session_id}", response_model=AgentChatResponse)
async def agent_chat(session_id: str = Path(...), file: UploadFile = File(...)):
    try:
        start_time = time.time()
        audio_data = await file.read()
        user_input = transcribe_audio(audio_data)
        logger.info(f"User said: {user_input}")

        # Manage session history
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        chat_sessions[session_id].append({"role": "user", "text": user_input})

        # AI reply
        ai_response = get_ai_reply(chat_sessions[session_id])
        logger.info(f"AI replied: {ai_response}")
        chat_sessions[session_id].append({"role": "assistant", "text": ai_response})

        # TTS
        audio_url = synthesize_audio(ai_response)
        logger.info(f"Generated voice at {audio_url}. Total time: {time.time()-start_time:.2f}s")

        return AgentChatResponse(audio_url=audio_url)

    except Exception as e:
        logger.error(f"Error in /agent/chat: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"audio_url": generate_fallback_audio(), "detail": str(e)}
        )

def generate_fallback_audio():
    return "/static/fallback.mp3"
