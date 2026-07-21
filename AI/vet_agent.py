"""
vet_agent.py
────────────
AI Vet chatbot — Dr. Paws — powered by LangChain + OpenRouter (ChatOpenRouter).

Public interface
────────────────
    run_vet_agent(
        user_message         : str,
        conversation_history : list[dict],
        user_context         : dict,
    ) -> str

    conversation_history — last 4 turns (sliced by the caller):
        [{"role": "user"|"assistant", "content": "..."}]

    user_context — owner + pet info injected into the system prompt:
        {
            "owner_name"  : str,
            "pet_name"    : str,
            "pet_type"    : str,   # "dog" | "cat"
            "breed"       : str | None,
        }

Environment variables (in env/.env)
────────────────────────────────────
    OPENROUTER_API_KEY   — your OpenRouter API key  (required)
    VET_MODEL            — model slug (default: anthropic/claude-sonnet-4-5)
"""

import os
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# ── Load env ──────────────────────────────────────────────────────────────────
env_path = Path(__file__).parent.parent / "env" / ".env"
load_dotenv(env_path)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL              = os.getenv("VET_MODEL", "anthropic/claude-sonnet-4-5")

# ── System prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt(user_context: Dict) -> str:
    """
    Build a personalised system prompt that tells Dr. Paws who it is talking to
    and what pet(s) the owner has.
    """
    owner_name = user_context.get("owner_name") or "the owner"
    pet_name   = user_context.get("pet_name")   or "the pet"
    pet_type   = user_context.get("pet_type")   or "pet"
    breed      = user_context.get("breed")

    breed_line = f"Breed: {breed}" if breed else "Breed: Unknown / Mixed"

    return f"""\
You are Dr. Paws, a warm, knowledgeable, and friendly AI veterinarian assistant
created by PetPro.

── Owner & Pet Context ──────────────────────────────────────────────────────
Owner's name : {owner_name}
Pet's name   : {pet_name}
Species      : {pet_type}
{breed_line}
─────────────────────────────────────────────────────────────────────────────

Use this context naturally in your responses — address the owner by name when
appropriate and refer to their pet by name. Tailor all advice to the specific
species and breed mentioned above.

Your role:
- Provide helpful, accurate, and compassionate pet care advice.
- Answer questions about symptoms, behaviour, nutrition, grooming, vaccinations,
  and general pet wellness.
- When a symptom could be serious, always recommend visiting a real vet in person.
- Keep replies concise and easy to understand (avoid overly clinical jargon).
- If you are unsure, say so honestly and advise a professional vet consultation.

You are NOT a replacement for a licensed veterinarian. Always make this clear
when discussing health concerns.

Tone: caring, calm, encouraging — like a knowledgeable friend who happens to be a vet.
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_messages(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    user_context: Dict,
) -> list:
    """
    Assemble the LangChain message list:
      [SystemMessage] + [last 4 history turns] + [new HumanMessage]

    Only the last 4 turns of history are included (2 user + 2 AI),
    keeping token usage low while preserving short-term memory.
    """
    messages = [SystemMessage(content=_build_system_prompt(user_context))]

    # Slice to last 4 turns (caller may pass more; we enforce the limit here)
    recent_history = conversation_history[-4:]

    for turn in recent_history:
        role    = turn.get("role", "")
        content = turn.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_message))
    return messages


def _get_model() -> ChatOpenRouter:
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. "
            "Add it to Petpro_backend/env/.env and restart the server."
        )
    return ChatOpenRouter(
        model=MODEL,
        temperature=0.7,
        max_tokens=1024,
        max_retries=2,
    )


# ── Public function ────────────────────────────────────────────────────────────

def run_vet_agent(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    user_context: Optional[Dict] = None,
) -> str:
    """
    Send a message to Dr. Paws and get a personalised reply.

    Parameters
    ----------
    user_message : str
        The pet owner's latest message.
    conversation_history : list[dict]
        Recent turns — list of {"role": ..., "content": ...} dicts.
        Only the last 4 are used (enforced internally).
    user_context : dict, optional
        Owner + pet info: owner_name, pet_name, pet_type, breed.
        Pass None or {} if unavailable — Dr. Paws will still work generically.

    Returns
    -------
    str
        Dr. Paws' plain-text reply.

    Raises
    ------
    RuntimeError
        If the OpenRouter API call fails.
    """
    model    = _get_model()
    messages = _build_messages(
        user_message,
        conversation_history,
        user_context or {},
    )

    try:
        response = model.invoke(messages)
    except Exception as exc:
        raise RuntimeError(f"OpenRouter API call failed: {exc}") from exc

    return response.content or ""
