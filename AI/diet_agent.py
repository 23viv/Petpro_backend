"""
diet_agent.py
─────────────
AI-powered pet nutritionist using LangChain + OpenRouter (ChatOpenRouter).

Public interface
────────────────
    run_diet_agent(pet_details: dict) -> dict

    pet_details keys (all optional except pet_type):
        pet_type        str   "dog" | "cat"
        name            str   Pet's name
        breed           str   e.g. "Golden Retriever"
        age_years       int   Age in years
        weight_kg       float Body weight in kilograms
        health_notes    str   Allergies, conditions, dietary restrictions

Environment variables (in env/.env)
────────────────────────────────────
    OPENROUTER_API_KEY   — your OpenRouter API key  (required)
    DIET_MODEL           — model slug to use
                           (default: anthropic/claude-sonnet-4-5)
"""


import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import HumanMessage, SystemMessage

# ── Load env ──────────────────────────────────────────────────────────────────
env_path = Path(__file__).parent.parent / "env" / ".env"
load_dotenv(env_path)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL              = os.getenv("DIET_MODEL", "anthropic/claude-sonnet-4-5")

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are Dr. Nutri Paws, a certified pet nutritionist with 15+ years of experience
in canine and feline dietary science.

Your task is to create a personalised, vet-approved daily meal plan for a pet.

STRICT RULES:
1. Return ONLY valid JSON — no markdown, no prose, no code fences.
2. Adhere exactly to the schema below — every field is required.
3. Use realistic serving sizes and well-known, safe pet foods.
4. For the "foods_to_avoid" list include at least 3 items specific to the pet's
   species, breed, age, and any stated health conditions.
5. Keep the "vet_tip" practical, specific, and under 2 sentences.

JSON SCHEMA:
{
  "summary": "<1-2 sentence overview of the diet plan>",
  "daily_calories": <integer — total kcal/day>,
  "meals": {
    "breakfast": { "food": "<food name>", "amount": "<portion>", "notes": "<optional tip>" },
    "lunch":     { "food": "<food name>", "amount": "<portion>", "notes": "<optional tip>" },
    "dinner":    { "food": "<food name>", "amount": "<portion>", "notes": "<optional tip>" },
    "snacks":    { "food": "<food name>", "amount": "<portion>", "notes": "<optional tip>" }
  },
  "foods_to_avoid": ["<food1>", "<food2>", "<food3>"],
  "vet_tip": "<practical advice>"
}
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_human_message(pet: dict) -> str:
    """Turn the pet details dict into a natural-language prompt."""
    name         = pet.get("name", "the pet")
    pet_type     = pet.get("pet_type", "dog").lower()
    breed        = pet.get("breed") or "Mixed breed"
    age          = pet.get("age_years")
    weight       = pet.get("weight_kg")
    health_notes = pet.get("health_notes") or "None reported"

    age_str    = f"{age} year(s) old" if age is not None else "age unknown"
    weight_str = f"{weight} kg"       if weight is not None else "weight unknown"

    return (
        f"Pet name: {name}\n"
        f"Species: {pet_type}\n"
        f"Breed: {breed}\n"
        f"Age: {age_str}\n"
        f"Weight: {weight_str}\n"
        f"Health notes / dietary restrictions: {health_notes}\n\n"
        f"Please generate a complete daily meal plan for {name}."
    )


def _extract_json(raw: str) -> dict:
    """
    Extract JSON from the model response.
    Handles cases where the model wraps the JSON in markdown code fences.
    """
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response.")

    return json.loads(match.group())


def _get_model() -> ChatOpenRouter:
    """Build and return the ChatOpenRouter model instance."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. "
            "Add it to Petpro_backend/env/.env and restart the server."
        )
    return ChatOpenRouter(
        model=MODEL,
        temperature=0,
        max_tokens=1024,
        max_retries=2,
    )


# ── Public function ────────────────────────────────────────────────────────────

def run_diet_agent(pet_details: dict) -> dict:
    """
    Generate a personalised daily meal plan for a pet via OpenRouter.

    Parameters
    ----------
    pet_details : dict
        Keys: pet_type (required), name, breed, age_years, weight_kg, health_notes

    Returns
    -------
    dict
        Structured meal plan matching the JSON schema above.

    Raises
    ------
    RuntimeError
        If the API call fails or the response cannot be parsed as valid JSON.
    """
    model = _get_model()

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=_build_human_message(pet_details)),
    ]

    try:
        response = model.invoke(messages)
    except Exception as exc:
        raise RuntimeError(f"OpenRouter API call failed: {exc}") from exc

    raw_text = response.content or ""

    try:
        plan = _extract_json(raw_text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            f"Diet agent returned non-JSON response. "
            f"Raw output: {raw_text[:300]}"
        ) from exc

    return plan
