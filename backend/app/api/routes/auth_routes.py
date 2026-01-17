from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    BackgroundTasks,
    File,
    UploadFile,
    Request,
)
from sqlalchemy.orm import Session
import random
from datetime import datetime, timedelta, timezone

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.schemas import (
    SignupSchema,
    LoginSchema,
    ForgotPasswordSchema,
    MessageResponse,
    CodeVerifySchema,
    GoogleAuthSchema,
    TokenResponse,
    SignupForm,
    UpdatePasswordSchema,
    ResetPasswordSchema,
    ResendCodeSchema,
)
from app.models import User, AuthProviderEnum, RefreshToken
from app.core.database import get_db
from app.api.routes.utils import hash_utils, jwt_utils, email_utils
from app.api.routes.utils.auth_utils import (
    get_user_by_email,
    ensure_local_account,
    validate_verification_code,
    validate_reset_code,
)
from app.api.routes.utils.s3_utils import upload_profile_image_to_s3
from app.core.config import settings
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Auth"])


# ---------------------------
# Ensure user is active
# ---------------------------
def ensure_user_active(user: User):
    if not user.is_active:
        raise HTTPException(403, "Account is disabled")


# ---------------------------
# Register Endpoint
# ---------------------------
@router.post("/register", response_model=MessageResponse)
async def register_user(
    background_tasks: BackgroundTasks,
    form_data: SignupSchema = Depends(SignupForm),
    profile_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    username = form_data.username.strip()
    email = form_data.email.lower().strip()

    existing_user = db.query(User).filter(User.email == email).first()

    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(400, "Email already registered and verified")
        else:
            # User exists but not verified → refresh OTP
            new_code = random.randint(100000, 999999)
            existing_user.verification_code = new_code
            existing_user.verification_expires_at = datetime.utcnow() + timedelta(minutes=15)
            db.commit()

            background_tasks.add_task(
                email_utils.send_verification_code_email, existing_user.email, new_code
            )
            return {"message": "A new verification code has been sent to your email"}


    image_url = None
    if profile_image is not None:
        file_bytes = await profile_image.read()
        image_url = upload_profile_image_to_s3(file_bytes, profile_image.filename)
    else:
        # Optional: set a default placeholder image
        image_url = "https://your-bucket.s3.region.amazonaws.com/profile_pics/default.png"

    hashed_password = hash_utils.hash_password(form_data.password)
    code = random.randint(100000, 999999)

    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        is_verified=False,
        provider=AuthProviderEnum.LOCAL,
        verification_code=code,
        verification_expires_at=datetime.utcnow() + timedelta(minutes=15),
        profile_image_url=image_url,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    background_tasks.add_task(
        email_utils.send_verification_code_email, new_user.email, code
    )

    return {"message": "User registered successfully. Please check your email for the 6-digit code."}


# ---------------------------
# Verify Email
# ---------------------------
@router.post("/verify", response_model=MessageResponse)
def verify_email(payload: CodeVerifySchema, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(
            User.verification_code == payload.code,
            User.verification_expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    if user.is_verified:
        return {"message": "Email already verified"}

    user.is_verified = True
    user.verification_code = None
    user.verification_expires_at = None
    db.commit()

    return {"message": "Email verified successfully"}



# ---------------------------
# Resend Verification Code
# ---------------------------
@router.post("/resend-code", response_model=MessageResponse)
def resend_verification_code(
    payload: ResendCodeSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or user.is_verified:
        raise HTTPException(400, "No pending verification found")

    new_code = random.randint(100000, 999999)
    user.verification_code = new_code
    user.verification_expires_at = datetime.utcnow() + timedelta(minutes=15)
    db.commit()

    background_tasks.add_task(
        email_utils.send_verification_code_email, user.email, new_code
    )

    return {"message": "A new verification code has been sent to your email"}


# ---------------------------
# Login Endpoint
# ---------------------------
@router.post("/login", response_model=TokenResponse)
def login_user(
    payload: LoginSchema,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, payload.email)
    ensure_local_account(user)
    ensure_user_active(user)

    if not user.hashed_password or not hash_utils.verify_password(
        payload.password, user.hashed_password
    ):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    ip = request.client.host if request.client else "Unknown IP"
    device = request.headers.get("user-agent", "Unknown Device")

    background_tasks.add_task(
        email_utils.send_login_alert_email,
        user.email,
        ip,
        device,
    )

    is_new_device = (
        getattr(user, "last_login_ip", None) != ip
        or getattr(user, "last_login_device", None) != device
    )
    if is_new_device:
        background_tasks.add_task(
            email_utils.send_new_device_notification,
            user.email,
            device,
            ip,
        )

    # Update login info
    user.last_login_ip = ip
    user.last_login_device = device
    user.last_login_at = datetime.utcnow()

    # Include both user_id and sub/email in JWT payload
    access_token = jwt_utils.create_access_token({
        "sub": user.email,
        "user_id": str(user.id),
        "email": user.email
    })

    refresh_value = jwt_utils.create_refresh_token()
    expires_at = jwt_utils.get_refresh_expiry()

    existing = db.query(RefreshToken).filter(RefreshToken.user_id == user.id).first()
    if existing:
        existing.token = refresh_value
        existing.expires_at = expires_at
    else:
        db.add(
            RefreshToken(user_id=user.id, token=refresh_value, expires_at=expires_at)
        )

    db.commit()

    return TokenResponse(
        user_id=str(user.id),
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_value
    )


# ---------------------------
# Refresh Token
# ---------------------------
@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    rt = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if not rt:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if rt.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Expired refresh token")

    user = db.query(User).filter(User.id == rt.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ensure_user_active(user)

    new_access = jwt_utils.create_access_token({
        "sub": user.email,
        "user_id": str(user.id),
        "email": user.email
    })

    return TokenResponse(
        user_id=str(user.id),
        access_token=new_access,
        token_type="bearer",
        refresh_token=refresh_token
    )


# ---------------------------
# Forgot Password
# ---------------------------
@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    background_tasks: BackgroundTasks,
    payload: ForgotPasswordSchema,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, payload.email)
    ensure_local_account(user)
    ensure_user_active(user)

    reset_code = random.randint(100000, 999999)
    user.reset_code = reset_code
    user.reset_expires_at = datetime.utcnow() + timedelta(minutes=15)
    user.reset_verified = False
    db.commit()

    background_tasks.add_task(
        email_utils.send_password_reset_code_email, user.email, reset_code
    )

    return {"message": "Password reset code sent to your email"}


# ---------------------------
# Verify Forgot Password OTP
# ---------------------------
@router.post("/verify-forgot-otp", response_model=MessageResponse)
def verify_forgot_password_otp(
    payload: CodeVerifySchema,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.reset_code == payload.code).first()

    if not user:
        raise HTTPException(400, "Invalid or expired OTP")

    ensure_local_account(user)
    ensure_user_active(user)

    validate_reset_code(user, payload.code)

    user.reset_verified = True
    db.commit()

    return {"message": "OTP verified successfully. You can now set a new password."}


# ---------------------------
# Set New Password
# ---------------------------
@router.post("/set-new-password", response_model=MessageResponse)
def set_new_password(
    payload: ResetPasswordSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.reset_verified.is_(True)).first()

    if not user:
        raise HTTPException(
            400,
            "OTP verification required before setting a new password",
        )

    ensure_local_account(user)
    ensure_user_active(user)

    user.hashed_password = hash_utils.hash_password(payload.password)

    user.reset_verified = False
    user.reset_code = None
    user.reset_expires_at = None

    rt = db.query(RefreshToken).filter(RefreshToken.user_id == user.id).first()
    if rt:
        db.delete(rt)

    db.commit()

    background_tasks.add_task(
        email_utils.send_password_changed_notification,
        user.email,
    )

    return {"message": "Password updated successfully. You can now log in."}


# ---------------------------
# Reset Password (Logged-in User)
# ---------------------------
@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: UpdatePasswordSchema,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(jwt_utils.get_current_user),
    db: Session = Depends(get_db),
):
    ensure_local_account(current_user)
    ensure_user_active(current_user)

    if not hash_utils.verify_password(
        payload.old_password, current_user.hashed_password
    ):
        raise HTTPException(400, "Current password is incorrect")

    current_user.hashed_password = hash_utils.hash_password(payload.password)
    db.commit()

    background_tasks.add_task(
        email_utils.send_password_changed_notification,
        current_user.email,
    )

    return {"message": "Password reset successfully"}
# ---------------------------
# Google Sign-In
# ---------------------------
@router.post("/google", response_model=TokenResponse)
def google_sign_in(payload: GoogleAuthSchema, db: Session = Depends(get_db)):
    try:
        # Verify Google ID token
        idinfo = id_token.verify_oauth2_token(
            payload.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )

        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise HTTPException(status_code=400, detail="Invalid issuer")

        email = (idinfo.get("email") or "").lower().strip()
        if not email:
            raise HTTPException(status_code=400, detail="Google token missing email")

        # Google unique identifier
        google_sub = idinfo.get("sub")
        google_picture = idinfo.get("picture")

        user = db.query(User).filter(User.email == email).first()

        # Prevent mixing providers
        if user and user.provider != AuthProviderEnum.GOOGLE:
            raise HTTPException(
                status_code=400,
                detail="This email is registered with password. Please use standard login.",
            )

        if not user:
            # Generate unique username
            base_username = (payload.name or email.split("@")[0]).strip()
            candidate = base_username or "user"
            suffix = 1

            while db.query(User).filter(User.username == candidate).first():
                candidate = f"{base_username}_{suffix}"
                suffix += 1

            user = User(
                username=candidate,
                email=email,
                hashed_password=None,
                is_verified=True,
                is_active=True,
                provider=AuthProviderEnum.GOOGLE,
                profile_image_url=google_picture or payload.picture,
                google_sub=google_sub,
                google_picture=google_picture,
                last_google_id_token=payload.id_token,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update Google fields if already exists
            user.google_sub = google_sub
            user.google_picture = google_picture
            user.last_google_id_token = payload.id_token
            ensure_user_active(user)
            db.commit()

        # Issue JWTs with user_id included
        access_token = jwt_utils.create_access_token({
            "user_id": str(user.id),
            "email": user.email
        })
        refresh_value = jwt_utils.create_refresh_token()
        expires_at = jwt_utils.get_refresh_expiry()

        existing = db.query(RefreshToken).filter(RefreshToken.user_id == user.id).first()
        if existing:
            existing.token = refresh_value
            existing.expires_at = expires_at
        else:
            db.add(
                RefreshToken(
                    user_id=user.id,
                    token=refresh_value,
                    expires_at=expires_at,
                )
            )

        db.commit()

        # Corrected return block
        return TokenResponse(
            user_id=str(user.id),
            access_token=access_token,
            refresh_token=refresh_value
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")

# ---------------------------
# Sign Out
# ---------------------------
@router.post("/sign-out", response_model=MessageResponse)
def logout_user(refresh_token: str, db: Session = Depends(get_db)):
    rt = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if rt:
        db.delete(rt)
        db.commit()

    return {"message": "Signed out successfully"}

