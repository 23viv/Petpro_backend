from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sqldatabase import get_db
from models.user_model import User
from routes.Auth.auth_routes import get_current_user, verify_password, hashpassword
from routes.User.user_schema import UserOut, UpdateProfileRequest, ChangePasswordRequest
from fastapi import Form, File, UploadFile
import cloudinary
import cloudinary.uploader
import dotenv
from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path(__file__).parent / "env" / ".env"
load_dotenv(env_path)
cloudinary.config(
    cloud_name=os.getenv("cloud_name"),
    api_key=os.getenv("api_key"),
    api_secret=os.getenv("api_secret"),
)

router = APIRouter(prefix="/user", tags=["user"])


# ---------- VIEW MY PROFILE ----------
@router.get("/me", response_model=UserOut)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


# ---------- UPDATE MY PROFILE ----------
@router.patch("/me", response_model=UserOut)
def update_my_profile(
    full_name: str | None = Form(None),
    email: str | None = Form(None),
    photo: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if email and email != current_user.email:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use")
        current_user.email = email

    if full_name is not None:
        current_user.full_name = full_name

    if photo is not None:
        result = cloudinary.uploader.upload(photo.file, folder="petpro/users")
        current_user.profile_photo_url = result["secure_url"]

    db.commit()
    db.refresh(current_user)
    return current_user

# ---------- CHANGE MY PASSWORD ----------
@router.post("/me/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    current_user.hashed_password = hashpassword(payload.new_password)
    current_user.current_refresh_token = None  # force re-login everywhere after password change
    db.commit()
    return {"message": "Password updated successfully. Please log in again."}


# ---------- DELETE MY OWN ACCOUNT ----------
@router.delete("/me")
def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted successfully"}


