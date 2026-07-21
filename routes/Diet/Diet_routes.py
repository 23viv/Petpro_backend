"""
Diet_routes.py
──────────────
Meal & Diet Planner endpoints.

All routes are JWT-protected via get_current_user.
Diet plans are stored in MongoDB (collection: diet_plans), keyed on user_id + pet_id.

Endpoints
─────────
  POST   /diet/generate          — generate (or regenerate) a plan for a pet
  GET    /diet/{pet_id}          — retrieve the saved plan for a pet
  PUT    /diet/{pet_id}/regenerate — force-regenerate a fresh plan
  DELETE /diet/{pet_id}          — delete the saved plan for a pet
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from mongodatabase import get_diet_collection
from models.pet_model import Pet
from models.user_model import User
from routes.Auth.auth_routes import get_current_user
from routes.Diet.Diet_schema import DietPlanOut, GeneratePlanRequest, MealItem, MealPlan
from sqldatabase import get_db
from AI.diet_agent import run_diet_agent

router = APIRouter(prefix="/diet", tags=["Diet Planner"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_pet_for_user(pet_id: int, user_id: int, db: Session) -> Pet:
    """Load a pet that belongs to the current user, or raise 404."""
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.owner_id == user_id).first()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


def _doc_to_out(doc: dict) -> DietPlanOut:
    """Convert a MongoDB document into a DietPlanOut response model."""
    raw_plan = doc["plan"]

    # Build MealItem objects for each meal slot
    meals = {
        slot: MealItem(**data)
        for slot, data in raw_plan["meals"].items()
    }

    plan = MealPlan(
        summary=raw_plan["summary"],
        daily_calories=raw_plan["daily_calories"],
        meals=meals,
        foods_to_avoid=raw_plan["foods_to_avoid"],
        vet_tip=raw_plan["vet_tip"],
    )

    return DietPlanOut(
        id=str(doc["_id"]),
        pet_id=doc["pet_id"],
        pet_name=doc["pet_name"],
        generated_at=doc["generated_at"],
        plan=plan,
    )


def _run_and_save(
    pet: Pet,
    weight_kg: float | None,
    health_notes: str | None,
    user_id: int,
    collection,
) -> DietPlanOut:
    """
    Build pet_details, call the diet agent, upsert the result into MongoDB,
    and return a DietPlanOut.
    """
    # Resolve age from pet model
    age_years = None
    if pet.date_of_birth:
        from datetime import date
        today = date.today()
        age_years = today.year - pet.date_of_birth.year
        if (today.month, today.day) < (pet.date_of_birth.month, pet.date_of_birth.day):
            age_years -= 1
    elif pet.approximate_age_years is not None:
        age_years = pet.approximate_age_years

    pet_details = {
        "name":         pet.name,
        "pet_type":     pet.pet_type,
        "breed":        pet.breed,
        "age_years":    age_years,
        "weight_kg":    weight_kg,
        "health_notes": health_notes,
    }

    # Call the AI agent
    try:
        plan_dict = run_diet_agent(pet_details)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    now = datetime.now(timezone.utc)

    # Upsert: replace any existing plan for this user+pet
    collection.update_one(
        {"user_id": user_id, "pet_id": pet.id},
        {
            "$set": {
                "user_id":      user_id,
                "pet_id":       pet.id,
                "pet_name":     pet.name,
                "generated_at": now,
                "plan":         plan_dict,
            }
        },
        upsert=True,
    )

    saved = collection.find_one({"user_id": user_id, "pet_id": pet.id})
    return _doc_to_out(saved)


# ── POST /diet/generate ───────────────────────────────────────────────────────

@router.post("/generate", response_model=DietPlanOut, status_code=201)
def generate_plan(
    payload: GeneratePlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate an AI-powered meal plan for one of the current user's pets.
    If a plan already exists for this pet it will be overwritten.
    """
    pet = _fetch_pet_for_user(payload.pet_id, current_user.id, db)
    collection = get_diet_collection()
    return _run_and_save(pet, payload.weight_kg, payload.health_notes, current_user.id, collection)


# ── GET /diet/{pet_id} ────────────────────────────────────────────────────────

@router.get("/{pet_id}", response_model=DietPlanOut)
def get_plan(
    pet_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the saved diet plan for a pet. Returns 404 if none exists yet."""
    # Verify the pet belongs to this user
    _fetch_pet_for_user(pet_id, current_user.id, db)

    collection = get_diet_collection()
    doc = collection.find_one({"user_id": current_user.id, "pet_id": pet_id})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="No diet plan found for this pet. Call POST /diet/generate first.",
        )
    return _doc_to_out(doc)


# ── PUT /diet/{pet_id}/regenerate ─────────────────────────────────────────────

@router.put("/{pet_id}/regenerate", response_model=DietPlanOut)
def regenerate_plan(
    pet_id: int,
    payload: GeneratePlanRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Force-regenerate a fresh AI meal plan for a pet.
    Optionally pass a new weight_kg / health_notes to update inputs.
    """
    pet = _fetch_pet_for_user(pet_id, current_user.id, db)
    collection = get_diet_collection()

    weight_kg    = payload.weight_kg    if payload else None
    health_notes = payload.health_notes if payload else None

    return _run_and_save(pet, weight_kg, health_notes, current_user.id, collection)


# ── DELETE /diet/{pet_id} ─────────────────────────────────────────────────────

@router.delete("/{pet_id}")
def delete_plan(
    pet_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete the saved diet plan for a pet."""
    _fetch_pet_for_user(pet_id, current_user.id, db)

    collection = get_diet_collection()
    result = collection.delete_one({"user_id": current_user.id, "pet_id": pet_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No diet plan found for this pet.")

    return {"message": f"Diet plan for pet {pet_id} deleted successfully."}
