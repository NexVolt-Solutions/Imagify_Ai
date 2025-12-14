import logging
import asyncio
from fastapi import HTTPException
from fastapi_mail import FastMail, MessageSchema

from app.core.email_config import MAIL_CONFIG

fm = FastMail(MAIL_CONFIG)
logger = logging.getLogger("email")


# ---------------------------
# Internal Helper
# ---------------------------
async def _send_email(subject: str, to_email: str, html: str, retries: int = 2) -> None:
    """
    Send an HTML email with retry logic and structured logging.
    """
    message = MessageSchema(
        subject=subject,
        recipients=[to_email],
        body=html,
        subtype="html",
    )

    for attempt in range(retries + 1):
        try:
            await fm.send_message(message)
            return
        except Exception as e:
            logger.error(
                f"[Email Error] Attempt {attempt + 1} failed for {to_email}: {e}"
            )

            if attempt == retries:
                raise HTTPException(500, "Failed to send email")

            await asyncio.sleep(1)  # small delay before retry


# ---------------------------
# HTML Template Builder
# ---------------------------
def _build_html(title: str, message: str, code: int) -> str:
    """
    Build a consistent HTML email template.
    """
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #6A0DAD;">{title}</h2>
        <p>Hello,</p>
        <p>{message}</p>
        <p style="text-align: center; font-size: 24px; font-weight: bold; color: #6A0DAD;">
          {code}
        </p>
        <p>This code will expire in 15 minutes.</p>
        <p>If this wasn't you, you can safely ignore this email.</p>
        <br>
        <p>Thanks,<br>AI-Wallpaper Team</p>
      </body>
    </html>
    """


# ---------------------------
# Verification Email
# ---------------------------
async def send_verification_code_email(to_email: str, code: int) -> None:
    subject = "Verify your AI-Wallpaper account"
    html = _build_html(
        title="Welcome to AI-Wallpaper!",
        message="Your verification code is:",
        code=code,
    )
    await _send_email(subject, to_email, html)


# ---------------------------
# Password Reset Email
# ---------------------------
async def send_password_reset_code_email(to_email: str, code: int) -> None:
    subject = "Reset your AI-Wallpaper password"
    html = _build_html(
        title="Password Reset Request",
        message="Your password reset code is:",
        code=code,
    )
    await _send_email(subject, to_email, html)

