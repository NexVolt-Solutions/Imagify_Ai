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


# ============================================================
# PASSWORD MIXIN (Shared Validation)
# ============================================================
class PasswordMixin(BaseModel):
    password: constr(min_length=8, max_length=72)
    confirm_password: constr(min_length=8, max_length=72)

    @validator("password")
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
        if values.get("password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values

# ============================================================
# SIGNUP
# ============================================================
class SignupSchema(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    password: constr(min_length=8, max_length=72)
    confirm_password: constr(min_length=8, max_length=72)

    @validator("password")
    def validate_password(cls, value: str):
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one number")
        return value

    @root_validator
    def passwords_match(cls, values):
        if values.get("password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}


def SignupForm(
    username: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    profile_image: Optional[UploadFile] = File(None)
) -> SignupSchema:

    if len(username.strip()) < 3:
        raise RequestValidationError([{
            "loc": ["username"],
            "msg": "Username must be at least 3 characters long",
            "type": "value_error",
        }])

    # Only validate if file is actually uploaded
    if profile_image is not None and profile_image.content_type not in ALLOWED_IMAGE_TYPES:
        raise RequestValidationError([{
            "loc": ["profile_image"],
            "msg": "Invalid file type. Only JPEG, PNG, JPG, and WEBP images are allowed.",
            "type": "value_error.file_type",
        }])

    return SignupSchema(
        username=username,
        email=email,
        password=password,
        confirm_password=confirm_password,
    )


# ============================================================
# AUTH / LOGIN / OTP
# ============================================================

# ---------------------------
# Verify Email Schema
# ---------------------------
class CodeVerifySchema(BaseModel):
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
# Resend Code Schema
# ---------------------------
class ResendCodeSchema(BaseModel):
    email: EmailStr


# ============================================================
# PASSWORD UPDATE
# ============================================================
class ResetPasswordSchema(PasswordMixin):
    """Used for /set-new-password after OTP verification."""
    pass


class UpdatePasswordSchema(BaseModel):
    old_password: str
    password: constr(min_length=8, max_length=72)
    confirm_password: constr(min_length=8, max_length=72)

    @validator("old_password")
    def validate_old_password(cls, v):
        if not v.strip():
            raise ValueError("Old password cannot be empty")
        return v

    @validator("password")
    def validate_password_strength(cls, value: str):
        if not any(c.isalpha() for c in value):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one number")
        return value

    @root_validator
    def passwords_match(cls, values):
        if values.get("password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values
# ============================================================
# PROFILE UPDATE (USERNAME ONLY — IMAGE VIA UploadFile)
# ============================================================
class UpdateProfileSchema(BaseModel):
    username: Optional[constr(min_length=3, max_length=50)] = None


# ============================================================
# FULL PROFILE UPDATE (USERNAME ONLY — IMAGE VIA UploadFile)
# Used in: update_full_profile()
# ============================================================
class UpdateFullProfileSchema(BaseModel):
    username: Optional[constr(min_length=3, max_length=50)] = None


# ============================================================
# UPDATE PASSWORD SCHEMA
# Used in: update_password()
# ============================================================
class UpdatePasswordSchema(BaseModel):
    old_password: constr(min_length=6)
    password: constr(min_length=6)


# ============================================================
# GENERIC RESPONSE
# ============================================================
class MessageResponse(BaseModel):
    message: str


# ============================================================
# USER PROFILE RESPONSE
# ============================================================
class UserProfileResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    is_verified: bool
    is_active: bool
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ============================================================
# GOOGLE AUTH
# ============================================================
class GoogleAuthSchema(BaseModel):
    id_token: str
    name: Optional[str] = None
    picture: Optional[str] = None

    sub: Optional[str] = None
    email: Optional[str] = None


# ============================================================
# TOKEN RESPONSE
# ============================================================
class TokenResponse(BaseModel):
    user_id: str
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


# ============================================================
# WALLPAPER SCHEMAS
# ============================================================
class WallpaperCreateSchema(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=350)
    size: str
    style: str

    @validator("prompt")
    def validate_prompt(cls, v):
        text = v.strip()
        if not text:
            raise ValueError("Prompt cannot be empty")
        if len(text) < 3:
            raise ValueError("Prompt must be at least 3 characters long")
        if len(text) > 350:
            raise ValueError("Prompt is too long. Please keep it under 350 characters.")
        return text


class WallpaperResponseSchema(BaseModel):
    id: UUID
    prompt: str
    size: str
    style: str
    image_url: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True


class WallpaperListSchema(BaseModel):
    wallpapers: List[WallpaperResponseSchema]


class WallpaperDeleteResponse(BaseModel):
    message: str
    deleted_wallpaper: Optional[WallpaperResponseSchema] = None


# ============================================================
# AI SUGGESTION
# ============================================================
from pydantic import BaseModel, validator

class AISuggestionSchema(BaseModel):
    prompt: str

    @validator("prompt")
    def validate_prompt(cls, v):
        if not v or not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v.strip()


class AISuggestionResponse(BaseModel):
    suggestion: str

    @validator("suggestion")
    def validate_suggestion_length(cls, v):
        if len(v) > 345:
            return v[:345].rstrip()
        return v


