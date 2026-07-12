from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqldatabase import Base  

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    role = Column(String(50), default="user", nullable=False)   # "user" or "admin"
    is_active = Column(Boolean, default=True)

    # used so /auth/logout can invalidate a refresh token
    current_refresh_token = Column(String(512), nullable=True)

    created_at = Column(DateTime, server_default=func.now())