from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: int
    full_name: str | None
    email: EmailStr
    profile_photo_url: str | None = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    profile_photo_url: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str