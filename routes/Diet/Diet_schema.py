from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


# ── Request ───────────────────────────────────────────────────────────────────

class GeneratePlanRequest(BaseModel):
    """Body sent by the client to generate a meal plan."""
    pet_id:        int
    weight_kg:     float | None = None   # override / supplement pet model weight
    health_notes:  str | None   = None   # allergies, conditions, restrictions


# ── Meal item ─────────────────────────────────────────────────────────────────

class MealItem(BaseModel):
    food:   str
    amount: str
    notes:  str | None = None


# ── Full plan (as returned by the AI) ────────────────────────────────────────

class MealPlan(BaseModel):
    summary:         str
    daily_calories:  int
    meals: dict[str, MealItem]   # keys: breakfast, lunch, dinner, snacks
    foods_to_avoid:  list[str]
    vet_tip:         str


# ── Response returned to the client ──────────────────────────────────────────

class DietPlanOut(BaseModel):
    """Full diet plan document as stored in MongoDB."""
    id:           str
    pet_id:       int
    pet_name:     str
    generated_at: datetime
    plan:         MealPlan
