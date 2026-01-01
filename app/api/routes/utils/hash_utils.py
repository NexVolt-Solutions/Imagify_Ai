from passlib.context import CryptContext
from typing import Optional


# ---------------------------
# Password Hashing Configuration
# ---------------------------
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Strong, safe default
)


# ---------------------------
# Hash Password
# ---------------------------
def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    Raises ValueError for invalid input.
    """
    if not isinstance(password, str) or not password.strip():
        raise ValueError("Password must be a non-empty string")

    return pwd_context.hash(password)


# ---------------------------
# Verify Password
# ---------------------------
def verify_password(plain: str, hashed: Optional[str]) -> bool:
    """
    Verify a plain-text password against a hashed password.
    Returns True if valid, False otherwise.
    """
    if not hashed or not isinstance(plain, str) or not plain:
        return False

    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        # Handles corrupted hashes or unexpected formats
        return False


# ---------------------------
# Optional: Password Strength Check
# ---------------------------
def is_password_strong(password: str) -> bool:
    """
    Optional helper to check password strength.
    Not enforced automatically — used only if needed.
    """
    if not isinstance(password, str):
        return False

    if len(password) < 8:
        return False

    # Must contain at least one letter and one number
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)

    return has_letter and has_number

