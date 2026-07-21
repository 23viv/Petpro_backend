from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sqldatabase import get_db
from models.user_model import User
from models.pet_model import Pet
from routes.Auth.auth_routes import get_current_user
from routes.Pets.Pets_schema import CreatePetRequest, PetOut

router = APIRouter(prefix="/pets", tags=["pets"])


@router.post("/", response_model=PetOut, status_code=201)
def create_pet(
    payload: CreatePetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pet = Pet(owner_id=current_user.id, **payload.model_dump())
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return pet


@router.get("/", response_model=list[PetOut])
def list_my_pets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Pet).filter(Pet.owner_id == current_user.id).all()


@router.get("/{pet_id}", response_model=PetOut)
def get_pet(pet_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.owner_id == current_user.id).first()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


@router.delete("/{pet_id}")
def delete_pet(pet_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.owner_id == current_user.id).first()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    db.delete(pet)
    db.commit()
    return {"message": "Pet deleted"}