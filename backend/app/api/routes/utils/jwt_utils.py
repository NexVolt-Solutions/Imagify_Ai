from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from uuid import uuid4

from app.core.config import settings


# ---------------------------
# Config
# ---------------------------
SECRET = settings.JWT_SECRET
ALGORITHM = settings.JWT_ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------------------------
# Internal Helpers
# ---------------------------
def _create_token(data: dict, expires_minutes: int) -> str:
    """Create a JWT with an expiration timestamp."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    """Decode and validate a JWT, raising proper HTTP errors."""
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# ---------------------------
# Email Verification Token (15 minutes)
# ---------------------------
def create_email_verification_token(data: dict) -> str:
    return _create_token(data, expires_minutes=15)


def decode_email_verification_token(token: str) -> dict:
    return _decode_token(token)


# ---------------------------
# Reset Password Token (15 minutes)
# ---------------------------
def create_reset_password_token(data: dict) -> str:
    return _create_token(data, expires_minutes=15)


def decode_reset_password_token(token: str) -> dict:
    return _decode_token(token)


# ---------------------------
# Access Token (short-lived)
# ---------------------------
def create_access_token(data: dict) -> str:
    return _create_token(
        data,
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


def decode_access_token(token: str) -> dict:
    return _decode_token(token)


# ---------------------------
# Refresh Token (opaque UUID)
# ---------------------------
def create_refresh_token() -> str:
    """Generate a secure opaque refresh token."""
    return str(uuid4())


def get_refresh_expiry() -> datetime:
    """Return UTC expiry timestamp for refresh token."""
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


# ---------------------------
# Current User Dependency
# ---------------------------
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Extract and validate the current user from JWT access token.
    Returns a dict containing the user's email (sub).
    """
    payload = _decode_token(token)
    email = payload.get("sub")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    return {"sub": email}

