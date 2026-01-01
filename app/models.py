import uuid
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Enum,
    Integer, UniqueConstraint, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


# ---------------------------
# Enums
# ---------------------------

class WallpaperStatusEnum(PyEnum):
    PENDING = "pending"
    PREPARING = "preparing"
    RENDERING = "rendering"
    RETRYING = "retrying"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


class AuthProviderEnum(PyEnum):
    LOCAL = "local"
    GOOGLE = "google"


# ---------------------------
# User Model
# ---------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)

    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    provider = Column(
        Enum(AuthProviderEnum, name="authproviderenum"),
        default=AuthProviderEnum.LOCAL,
        nullable=False
    )

    # Email verification
    verification_code = Column(Integer, nullable=True)
    verification_expires_at = Column(DateTime, nullable=True)

    # Forgot password reset
    reset_code = Column(Integer, nullable=True)
    reset_expires_at = Column(DateTime, nullable=True)
    reset_verified = Column(Boolean, default=False)

    # Profile image
    profile_image_url = Column(String(255), nullable=True)

    # NEW: Login tracking
    last_login_ip = Column(String(100), nullable=True)
    last_login_device = Column(String(255), nullable=True)

    # NEW: Google Sign-In tracking
    last_google_id_token = Column(Text, nullable=True)
    google_sub = Column(String(255), nullable=True)
    google_picture = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    wallpapers = relationship(
        "Wallpaper",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    refresh_token = relationship(
        "RefreshToken",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.email}>"


# ---------------------------
# Wallpaper Model
# ---------------------------

class Wallpaper(Base):
    __tablename__ = "wallpapers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    prompt = Column(String(350), nullable=False)
    size = Column(String(20), nullable=True)
    style = Column(String(50), nullable=True)

    image_url = Column(String(255), nullable=True)

    status = Column(
        Enum(WallpaperStatusEnum, name="wallpaperstatusenum"),
        default=WallpaperStatusEnum.PENDING,
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="wallpapers")

    def __repr__(self):
        return f"<Wallpaper {self.id} status={self.status.value}>"


# ---------------------------
# Refresh Token Model
# ---------------------------

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="refresh_token")

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_refresh_user"),
    )

    def __repr__(self):
        return f"<RefreshToken user={self.user_id}>"
