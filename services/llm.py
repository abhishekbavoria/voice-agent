import os
from dotenv import load_dotenv
from google import generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="gemini-2.5-flash")

def get_ai_reply(history: list) -> str:
    history_prompt = "\n".join(
        f"{msg['role'].capitalize()}: {msg['text']}" 
        for msg in history
    )
    response = model.generate_content(history_prompt)
    return response.text.strip()
