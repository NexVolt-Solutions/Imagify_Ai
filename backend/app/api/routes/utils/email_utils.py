import logging
import asyncio
import httpx
from fastapi import HTTPException, Request
from fastapi_mail import FastMail, MessageSchema
from user_agents import parse

from app.core.email_config import MAIL_CONFIG

fm = FastMail(MAIL_CONFIG)
logger = logging.getLogger("email")


# ============================================================
# DEVICE + IP + LOCATION HELPERS
# ============================================================

def extract_device_info(request: Request) -> tuple[str, str]:
    """
    Extract readable device name and IP address from request.
    """
    # User-Agent parsing
    ua_string = request.headers.get("user-agent", "")
    user_agent = parse(ua_string)

    device = (
        f"{user_agent.os.family} {user_agent.os.version_string} — "
        f"{user_agent.browser.family} {user_agent.browser.version_string}"
    )

    # Real IP extraction (supports proxies)
    ip = request.headers.get("x-forwarded-for", request.client.host)

    return device, ip

async def get_location_from_ip(ip: str) -> str:
    """
    Fetch city and country from IP using ipwho.is (free, no token).
    Returns a readable location string.
    """
    url = f"https://ipwho.is/{ip}"

    try:
        async with httpx.AsyncClient(timeout=3) as client:
            res = await client.get(url)
            data = res.json()

        if not data.get("success"):
            return "Unknown location"

        city = data.get("city")
        country = data.get("country")

        if city and country:
            return f"{city}, {country}"
        if country:
            return country

        return "Unknown location"

    except Exception:
        return "Unknown location"


# ============================================================
# INTERNAL EMAIL SENDER
# ============================================================

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

    for attempt in range(1, retries + 2):
        try:
            await fm.send_message(message)
            logger.info(f"[Email Sent] {subject} → {to_email}")
            return

        except Exception as e:
            logger.error(f"[Email Error] Attempt {attempt} failed for {to_email}: {e}")

            if attempt > retries:
                raise HTTPException(500, "Failed to send email")

            await asyncio.sleep(1)


# ============================================================
# HTML TEMPLATE BUILDER
# ============================================================

def _build_branded_html(
    title: str,
    subtitle: str,
    code_label: str,
    code,
    extra_note: str = "",
) -> str:
    """
    Build a branded HTML email for AI‑Wallpaper.
    """
    accent = "#6A0DAD"
    background = "#f4f3f8"
    card_bg = "#ffffff"
    text_color = "#333333"

    extra_note_html = (
        f"""
        <tr>
          <td style='padding-bottom:6px;'>
            <div style='font-size:13px;color:#777777;'>
              {extra_note}
            </div>
          </td>
        </tr>
        """
        if extra_note
        else ""
    )

    return f"""
    <html>
      <body style="margin:0;padding:0;background:{background};font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="padding:24px 0;">
          <tr>
            <td align="center">
              <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;">

                <!-- Brand header -->
                <tr>
                  <td align="center" style="padding:8px 0 16px 0;">
                    <span style="
                      display:inline-block;
                      font-size:22px;
                      font-weight:700;
                      color:{accent};
                      letter-spacing:0.03em;
                    ">
                      AI‑Wallpaper
                    </span>
                  </td>
                </tr>

                <!-- Card -->
                <tr>
                  <td>
                    <table width="100%" cellpadding="0" cellspacing="0" style="
                      background:{card_bg};
                      border-radius:16px;
                      padding:24px 24px 20px 24px;
                      box-shadow:0 10px 30px rgba(0,0,0,0.06);
                    ">

                      <tr>
                        <td style="padding-bottom:8px;">
                          <div style="font-size:20px;font-weight:600;color:{text_color};">
                            {title}
                          </div>
                        </td>
                      </tr>

                      <tr>
                        <td style="padding-bottom:16px;">
                          <div style="font-size:14px;color:#666666;">
                            {subtitle}
                          </div>
                        </td>
                      </tr>

                      <tr>
                        <td style="padding-bottom:8px;">
                          <div style="font-size:13px;color:#666666;">
                            {code_label}
                          </div>
                        </td>
                      </tr>

                      <tr>
                        <td align="center" style="padding:10px 0 18px 0;">
                          <span style="
                            display:inline-block;
                            padding:12px 28px;
                            font-size:22px;
                            font-weight:600;
                            color:#ffffff;
                            background:{accent};
                            border-radius:12px;
                          ">
                            {code}
                          </span>
                        </td>
                      </tr>

                      {extra_note_html}

                      <tr>
                        <td style="padding-top:12px;border-top:1px solid #eee;">
                          <div style="font-size:12px;color:#aaaaaa;margin-top:10px;">
                            Sent by <strong>AI‑Wallpaper</strong> · Beautiful AI‑generated wallpapers, on every device.
                          </div>
                        </td>
                      </tr>

                    </table>
                  </td>
                </tr>

                <tr>
                  <td align="center" style="padding-top:14px;">
                    <div style="font-size:11px;color:#aaaaaa;">
                      You’re receiving this email because you requested an action on your AI‑Wallpaper account.
                    </div>
                  </td>
                </tr>

              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


# ============================================================
# EMAIL TYPES
# ============================================================

async def send_verification_code_email(to_email: str, code: int) -> None:
    subject = "Verify your AI‑Wallpaper account"
    html = _build_branded_html(
        title="Confirm your email",
        subtitle="Welcome to AI‑Wallpaper! Use the code below to verify your email.",
        code_label="Your verification code:",
        code=code,
        extra_note="This code expires in 15 minutes.",
    )
    await _send_email(subject, to_email, html)


async def send_password_reset_code_email(to_email: str, code: int) -> None:
    subject = "Reset your AI‑Wallpaper password"
    html = _build_branded_html(
        title="Reset your password",
        subtitle="We received a request to reset your password.",
        code_label="Your reset code:",
        code=code,
        extra_note="If you didn’t request this, ignore this email.",
    )
    await _send_email(subject, to_email, html)


async def send_password_changed_notification(to_email: str) -> None:
    subject = "Your AI‑Wallpaper password was changed"
    html = _build_branded_html(
        title="Your password was updated",
        subtitle="Your password has been successfully changed.",
        code_label="Status:",
        code="✓",
        extra_note="If this wasn’t you, reset your password immediately.",
    )
    await _send_email(subject, to_email, html)


async def send_account_deleted_notification(to_email: str) -> None:
    subject = "Your AI‑Wallpaper account has been deleted"
    html = _build_branded_html(
        title="Your account was deleted",
        subtitle="Your AI‑Wallpaper account has been permanently removed.",
        code_label="Status:",
        code="✕",
        extra_note="If this wasn’t you, contact support immediately.",
    )
    await _send_email(subject, to_email, html)


# ============================================================
# LOGIN + NEW DEVICE EMAILS (WITH LOCATION)
# ============================================================

async def send_login_alert_email(to_email: str, ip: str, device: str) -> None:
    location = await get_location_from_ip(ip)

    subject = "New login to your AI‑Wallpaper account"
    html = _build_branded_html(
        title="New login detected",
        subtitle="We detected a login to your AI‑Wallpaper account.",
        code_label="Device:",
        code=device,
        extra_note=(
            f"IP Address: {ip}<br>"
            f"Location: {location}<br>"
            "If this wasn’t you, please reset your password immediately."
        ),
    )
    await _send_email(subject, to_email, html)


async def send_new_device_notification(to_email: str, device: str, ip: str) -> None:
    location = await get_location_from_ip(ip)

    subject = "New device added to your AI‑Wallpaper account"
    html = _build_branded_html(
        title="New device recognized",
        subtitle="A new device was used to access your AI‑Wallpaper account.",
        code_label="Device:",
        code=device,
        extra_note=(
            f"IP Address: {ip}<br>"
            f"Location: {location}<br>"
            "If this wasn’t you, please secure your account immediately."
        ),
    )
    await _send_email(subject, to_email, html)
