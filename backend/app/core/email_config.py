from fastapi_mail import ConnectionConfig
from app.core.config import settings

"""
Email configuration for FastAPI-Mail.
Supports both Gmail SMTP and AWS SES SMTP depending on .env values.
"""

MAIL_CONFIG = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,

    # SMTP server settings (Gmail or SES)
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,

    # TLS / SSL settings
    MAIL_STARTTLS=settings.MAIL_TLS,
    MAIL_SSL_TLS=settings.MAIL_SSL,

    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

