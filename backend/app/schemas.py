import re
from datetime import datetime
from fastapi import Form, File, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    conint,
    constr,
    validator,
    root_validator,
)
from typing import Optional, List
from uuid import UUID


# ---------------------------
# Shared Password Validation
# ---------------------------
class PasswordMixin(BaseModel):
    password: constr(min_length=8)
    confirm_password: str

    @validator("password", pre=True)
    def validate_password(cls, value: str):
        if not isinstance(value, str):
            raise ValueError("Password must be a string")

        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Password must contain at least one letter")

        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one number")

        return value

    @root_validator
    def passwords_match(cls, values):
        password = values.get("password")
        confirm_password = values.get("confirm_password")

        if password != confirm_password:
            raise ValueError("Passwords do not match")

        return values


# ---------------------------
# Signup Schema
# ---------------------------
class SignupSchema(PasswordMixin):
    username: constr(min_length=3, max_length=50)
    email: EmailStr


# Allowed image MIME types
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/jpg",
}


# ---------------------------
# Signup Form Dependency
# ---------------------------
def SignupForm(
    username: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    profile_image: UploadFile = File(...)
) -> SignupSchema:

    if len(username.strip()) < 3:
        raise RequestValidationError([
            {"loc": ["username"], "msg": "Username must be at least 3 characters long", "type": "value_error"}
        ])

    if profile_image.content_type not in ALLOWED_IMAGE_TYPES:
        raise RequestValidationError([
            {
                "loc": ["profile_image"],
                "msg": "Invalid file type. Only JPEG, PNG, JPG, and WEBP images are allowed.",
                "type": "value_error.file_type",
            }
        ])

    return SignupSchema(
        username=username,
        email=email,
        password=password,
        confirm_password=confirm_password,
    )


# ---------------------------
# Reset Password Schema
# ---------------------------
class ResetPasswordSchema(PasswordMixin):
    pass


# ---------------------------
# Reset Code Schema
# ---------------------------
class ResetCodeSchema(PasswordMixin):
    email: EmailStr
    code: conint(ge=100000, le=999999)


# ---------------------------
# Login Schema
# ---------------------------
class LoginSchema(BaseModel):
    email: EmailStr
    password: str

    @validator("password")
    def validate_password(cls, v):
        if not v.strip():
            raise ValueError("Password cannot be empty")
        return v


# ---------------------------
# Forgot Password Schema
# ---------------------------
class ForgotPasswordSchema(BaseModel):
    email: EmailStr


# ---------------------------
# Code Verification Schema
# ---------------------------
class CodeVerifySchema(BaseModel):
    email: EmailStr
    code: conint(ge=100000, le=999999)


# ---------------------------
# Resend Code Schema
# ---------------------------
class ResendCodeSchema(BaseModel):
    email: EmailStr


# ---------------------------
# Update Password Schema
# ---------------------------
class UpdatePasswordSchema(PasswordMixin):
    old_password: str

    @validator("old_password")
    def validate_old_password(cls, v):
        if not v.strip():
            raise ValueError("Old password cannot be empty")
        return v


# ---------------------------
# Update Profile Schema
# ---------------------------
class UpdateProfileSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[constr(regex=r"^\+?\d{7,15}$")] = None
    username: Optional[constr(min_length=3, max_length=50)] = None

    @root_validator
    def validate_at_least_one_field(cls, values):
        if not any(values.values()):
            raise ValueError("At least one field must be provided for update")
        return values


# ---------------------------
# Message Response Schema
# ---------------------------
class MessageResponse(BaseModel):
    message: str


# ---------------------------
# User Profile Response Schema
# ---------------------------
class UserProfileResponse(BaseModel):
    id: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    phone_number: Optional[str] = None
    is_verified: bool
    is_active: bool
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------
# Google Auth Schema
# ---------------------------
class GoogleAuthSchema(BaseModel):
    id_token: str
    name: Optional[str] = None
    picture: Optional[str] = None


# ---------------------------
# Token Response Schema
# ---------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


# ---------------------------
# Wallpaper Schemas
# ---------------------------
class WallpaperCreateSchema(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=350)
    size: str
    style: str
    title: Optional[str] = None
    ai_model: Optional[str] = None

    @validator("prompt")
    def validate_prompt_length(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Prompt must be at least 3 characters long")
        if len(v) > 300:
            raise ValueError("Prompt is too long. Please keep it under 350 characters.")
        return v


class WallpaperResponseSchema(BaseModel):
    id: UUID
    prompt: str
    size: str
    style: str
    title: Optional[str] = None
    ai_model: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime


class WallpaperListSchema(BaseModel):
    wallpapers: List[WallpaperResponseSchema]


class WallpaperDeleteResponse(BaseModel):
    message: str
    deleted_wallpaper: Optional[WallpaperResponseSchema] = None


class AISuggestionSchema(BaseModel):
    prompt: str

    @validator("prompt")
    def validate_prompt(cls, v):
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v


class AISuggestionResponse(BaseModel):
    suggestion: str

