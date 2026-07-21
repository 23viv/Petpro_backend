from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from bson import ObjectId
from sqlalchemy.orm import Session

from routes.Auth.auth_routes import get_current_user
from routes.Message.Message_schema import ChatRequest, ChatTurn, ChatResponse
from mongodatabase import get_messages_collection
from models.user_model import User
from models.pet_model import Pet
from sqldatabase import get_db
from AI.vet_agent import run_vet_agent

router = APIRouter(prefix="/messages", tags=["Vet Chat"])


# ─── helpers ─────────────────────────────────────────────────────────────────

def _to_turn(doc: dict) -> ChatTurn:
    return ChatTurn(
        id=str(doc["_id"]),
        role=doc["role"],
        content=doc["content"],
        timestamp=doc["timestamp"],
    )

def _load_history(user_id: int, collection) -> list:
    """Return all past turns as plain dicts, ordered oldest-first."""
    return [
        {"role": d["role"], "content": d["content"]}
        for d in collection.find({"user_id": user_id}).sort("timestamp", 1)
    ]


def _get_user_context(user: User, db: Session) -> dict:
    """
    Build the context dict passed to the vet agent so Dr. Paws knows
    the owner's name and their primary pet's details.
    Falls back gracefully if the user has no registered pets.
    """
    pet = db.query(Pet).filter(Pet.owner_id == user.id).first()
    return {
        "owner_name": user.full_name or "there",
        "pet_name":   pet.name      if pet else None,
        "pet_type":   pet.pet_type  if pet else None,
        "breed":      pet.breed     if pet else None,
    }


# ─── POST /messages/chat — send a message, get AI vet reply ──────────────────

@router.post("/chat", response_model=ChatResponse, status_code=201)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a message to Dr. Paws (the AI vet).
    Only the last 4 history turns are sent to the model (2 user + 2 AI),
    keeping token usage low while preserving short-term memory.
    The agent is also given the owner's name and their pet's name/breed.
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

    # 2. Load history BEFORE this turn, then slice to the last 4 turns
    full_history = _load_history(current_user.id, collection)[:-1]
    recent_history = full_history[-4:]   # last 4 turns = 2 user + 2 AI

    # 3. Build owner + pet context for Dr. Paws
    user_context = _get_user_context(current_user, db)

    # 4. Run the vet agent
    try:
        ai_text = run_vet_agent(
            user_message=payload.content,
            conversation_history=recent_history,
            user_context=user_context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vet agent error: {str(e)}")

    # 5. Save the agent's reply
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
