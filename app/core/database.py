from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

print(">>> USING DB:", settings.DATABASE_URI)

# ---------------------------
# SQLAlchemy Engine (AWS‑Ready)
# ---------------------------
engine = create_engine(
    settings.DATABASE_URI,
    echo=False,
    pool_pre_ping=True,          # Prevent stale connections on RDS
    pool_size=10,                # Base connection pool
    max_overflow=20,             # Extra connections allowed
    pool_recycle=1800,           # Recycle connections every 30 minutes
)


# ---------------------------
# Session Factory
# ---------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ---------------------------
# Base Class for ORM Models
# ---------------------------
Base = declarative_base()


# ---------------------------
# Dependency: Get DB Session
# ---------------------------
def get_db():
    """
    FastAPI dependency that yields a database session.
    Ensures the session is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

