from pydantic import BaseModel

class AgentChatResponse(BaseModel):
    audio_url: str
    detail: str = None  # Optional field for error details