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
import dotenv

