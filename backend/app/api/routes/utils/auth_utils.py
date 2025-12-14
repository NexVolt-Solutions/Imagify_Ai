from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import User, AuthProviderEnum


# ---------------------------
# Fetch User by Email
# ---------------------------
def get_user_by_email(db: Session, email: str) -> User:
    email = email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user


# ---------------------------
# Ensure Account is Local (Password-Based)
# ---------------------------
def ensure_local_account(user: User) -> None:
    if user.provider != AuthProviderEnum.LOCAL:
        raise HTTPException(
            400,
            "This account uses Google Sign-In and does not have a password.",
        )


# ---------------------------
# Ensure User is Active
# ---------------------------
def ensure_user_active(user: User) -> None:
    if not user.is_active:
        raise HTTPException(403, "Account is disabled")


# ---------------------------
# Ensure Email is Verified
# ---------------------------
def ensure_verified(user: User) -> None:
    if not user.is_verified:
        raise HTTPException(403, "Email not verified")


# ---------------------------
# Verification Code Validation
# ---------------------------
def validate_verification_code(user: User, code: int) -> None:
    if (
        user.verification_code != code
        or not user.verification_expires_at
        or datetime.utcnow() > user.verification_expires_at
    ):
        raise HTTPException(400, "Invalid or expired verification code")


# ---------------------------
# Reset Code Validation
# ---------------------------
def validate_reset_code(user: User, code: int) -> None:
    if (
        user.reset_code != code
        or not user.reset_expires_at
        or datetime.utcnow() > user.reset_expires_at
    ):
        raise HTTPException(400, "Invalid or expired reset code")

