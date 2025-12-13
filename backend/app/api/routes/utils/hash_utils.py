from passlib.context import CryptContext
from typing import Optional

# ---------------------------
# Password Hashing Configuration
# ---------------------------
# bcrypt__rounds can be made configurable via environment variable if needed.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


# ---------------------------
# Hash Password
# ---------------------------
def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    Returns the hashed password string.
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
    if not hashed or not isinstance(plain, str):
        return False

    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        # Covers corrupted hashes or unexpected formats
        return False


# ---------------------------
# Optional: Password Strength Check
# ---------------------------
def is_password_strong(password: str) -> bool:
    """
    Optional helper to check password strength.
    Not enforced automatically — used only if you want it.
    """
    if len(password) < 8:
        return False
    if password.isdigit() or password.isalpha():
        return False
    return True

