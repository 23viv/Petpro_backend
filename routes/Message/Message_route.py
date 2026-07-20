from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from bson import ObjectId

from routes.Auth.auth_routes import get_current_user
from routes.Message.Message_schema import ChatRequest, ChatTurn, ChatResponse
from mongodatabase import get_messages_collection
from models.user_model import User
from Agent.vet_agent import run_vet_agent

router = APIRouter(prefix="/messages", tags=["Vet Chat"])


# ─── helpers ─────────────────────────────────────────────────────────────────

def _to_turn(doc: dict) -> ChatTurn:
    return ChatTurn(
        id=str(doc["_id"]),
        role=doc["role"],
        content=doc["content"],
        timestamp=doc["timestamp"],
    )

def _load_history(user_id: int, collection) -> list[dict]:
    """Return all past turns as plain dicts for the agent."""
    return [
        {"role": d["role"], "content": d["content"]}
        for d in collection.find({"user_id": user_id}).sort("timestamp", 1)
    ]


# ─── POST /messages/chat — send a message, get AI vet reply ──────────────────

@router.post("/chat", response_model=ChatResponse, status_code=201)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Send a message to Dr. Paws (the AI vet).
    The full conversation history is automatically included for context.
    """
    collection = get_messages_collection()

    # 1. Save the user's message
    user_doc = {
        "user_id":   current_user.id,
        "role":      "user",
        "content":   payload.content,
        "timestamp": datetime.now(timezone.utc),
    }
    user_doc["_id"] = collection.insert_one(user_doc).inserted_id

    # 2. Load history BEFORE this turn (so the agent doesn't see the just-saved message)
    history = _load_history(current_user.id, collection)[:-1]

    # 3. Run the vet agent
    try:
        ai_text = run_vet_agent(
            user_message=payload.content,
            conversation_history=history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vet agent error: {str(e)}")

    # 4. Save the agent's reply
    ai_doc = {
        "user_id":   current_user.id,
        "role":      "assistant",
        "content":   ai_text,
        "timestamp": datetime.now(timezone.utc),
    }
    ai_doc["_id"] = collection.insert_one(ai_doc).inserted_id

    return ChatResponse(user_turn=_to_turn(user_doc), ai_turn=_to_turn(ai_doc))


# ─── GET /messages/history — fetch full conversation ─────────────────────────

@router.get("/history", response_model=list[ChatTurn])
def get_history(current_user: User = Depends(get_current_user)):
    """Return the complete chat history with Dr. Paws, oldest first."""
    collection = get_messages_collection()
    return [_to_turn(d) for d in collection.find({"user_id": current_user.id}).sort("timestamp", 1)]


# ─── DELETE /messages/history — wipe all history ─────────────────────────────

@router.delete("/history")
def clear_history(current_user: User = Depends(get_current_user)):
    """Clear the entire conversation history for the current user."""
    collection = get_messages_collection()
    result = collection.delete_many({"user_id": current_user.id})
    return {"deleted": result.deleted_count}


# ─── DELETE /messages/{id} — delete one turn ────────────────────────────────

@router.delete("/{message_id}")
def delete_message(message_id: str, current_user: User = Depends(get_current_user)):
    """Delete a single message by its MongoDB ObjectId."""
    try:
        obj_id = ObjectId(message_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid message ID")

    collection = get_messages_collection()
    doc = collection.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Message not found")
    if doc["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not your message")

    collection.delete_one({"_id": obj_id})
    return {"deleted": message_id}
