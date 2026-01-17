from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.config import settings
from app.core.database import get_db
from app.models import User


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
    """
    Create a JWT with an expiration timestamp.
    Uses UTC naive datetime to avoid timezone comparison issues.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    """
    Decode and validate a JWT, raising proper HTTP errors.
    """
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
# Access Token
# ---------------------------
def create_access_token(data: dict) -> str:
    """
    Create a short-lived access token.
    """
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
    """
    Generate a secure opaque refresh token.
    """
    return str(uuid4())


def get_refresh_expiry() -> datetime:
    """
    Return UTC expiry timestamp for refresh token.
    """
    return datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
# ---------------------------
# Current User Dependency
# ---------------------------
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate the current user from JWT access token.
    Returns the actual User model instance.
    """
    payload = _decode_token(token)

    # Accept either 'user_id' or 'sub' as identifier
    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token: missing user_id",
        )

    # Fetch user by ID
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Ensure account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user
