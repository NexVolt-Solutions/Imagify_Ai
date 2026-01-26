from pydantic import BaseSettings, EmailStr
from typing import Optional
from dotenv import load_dotenv



ENV_PATH = "/home/ubuntu/Imagify_Ai_backend/backend/.env"
load_dotenv(ENV_PATH)


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    Ensures strict validation for email fields.
    """

    # ---------------------------
    # Database
    # ---------------------------
    DATABASE_URI: str

    # ---------------------------
    # JWT
    # ---------------------------
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # ---------------------------
    # Google OAuth
    # ---------------------------
    GOOGLE_CLIENT_ID: str

    # ---------------------------
    # Email (Gmail SMTP or AWS SES SMTP)
    # ---------------------------
    MAIL_USERNAME: EmailStr
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr
    MAIL_FROM_NAME: str = "AI-Wallpaper App"
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False

    # ---------------------------
    # AWS S3 + CloudFront
    # ---------------------------
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "ap-southeast-1"
    AWS_S3_BUCKET: str
    AWS_S3_BASE_URL: Optional[str] = None
    CLOUDFRONT_DOMAIN: str | None = None

    # ---------------------------
    # Replicate API Key
    # ---------------------------
    REPLICATE_API_TOKEN: str

    # ---------------------------
    # App
    # ---------------------------
    APP_ENV: str = "development"
    FRONTEND_URL: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

