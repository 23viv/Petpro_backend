from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError

from Petpro_backend.sqldatabase import get_db          # your DB session dependency
from Petpro_backend.models.user_model import User
from Petpro_backend.routes.Auth.auth_schema import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, UserOut
from Petpro_backend.env import auth
from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).parent / "env" / ".env"
load_dotenv(env_path)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_EXPIRE_MIN = os.getenv("ACCESS_EXPIRE_MIN")
REFRESH_EXPIRE_DAYS = os.getenv("REFRESH_EXPIRE_DAYS")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

def hashpassword(password:str) -> str: # Used to create a hash password for database
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool: # Used to verfiy pasword
    return pwd_context.verify(plain, hashed)

def create_token(user_id: int, role: str, token_type: str, expires_delta: timedelta) -> str: # Used to create session JWT TOKEN
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": token_type,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if token is None:
        raise error
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise error
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise error

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise error
    return user 

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hashpassword(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_token(user.id, user.role, "access", timedelta(minutes=ACCESS_EXPIRE_MIN))
    refresh_token = create_token(user.id, user.role, "refresh", timedelta(days=REFRESH_EXPIRE_DAYS))

    user.current_refresh_token = refresh_token   # save it so we can check/revoke it later
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        claims = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if claims.get("type") != "refresh":
            raise JWTError()
        user_id = int(claims.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.current_refresh_token != payload.refresh_token:
        # doesn't match what's saved -> already logged out / revoked / stolen token
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    new_access = create_token(user.id, user.role, "access", timedelta(minutes=ACCESS_EXPIRE_MIN))
    new_refresh = create_token(user.id, user.role, "refresh", timedelta(days=REFRESH_EXPIRE_DAYS))
    user.current_refresh_token = new_refresh   # rotate it
    db.commit()

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)
@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.current_refresh_token = None   # wipes it -> /refresh will reject old tokens now
    db.commit()
    return {"message": "Logged out successfully"}


# ---------- ME ----------
@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user