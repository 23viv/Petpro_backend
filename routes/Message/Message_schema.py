from pydantic import BaseModel
from datetime import datetime


class ChatRequest(BaseModel):
    """The user's message to the vet agent."""
    content: str


class ChatTurn(BaseModel):
    """A single message turn — either from the user or the AI vet."""
    id: str
    role: str        # "user" or "assistant"
    content: str
    timestamp: datetime


class ChatResponse(BaseModel):
    """Returned after a chat call — contains the user turn and the AI vet reply."""
    user_turn: ChatTurn
    ai_turn: ChatTurn
