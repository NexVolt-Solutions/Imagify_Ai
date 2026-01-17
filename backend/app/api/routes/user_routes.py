from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.models import User
from app.core.database import get_db
from app.api.routes.utils import hash_utils, jwt_utils, email_utils
from app.api.routes.utils.s3_utils import upload_profile_image_to_s3
from app.schemas import (
    MessageResponse,
    UpdatePasswordSchema,
    UserProfileResponse,
    UpdateProfileSchema,
    UpdateFullProfileSchema,
)

router = APIRouter(prefix="/users", tags=["Users"])


# ---------------------------
# Ensure user is active
# ---------------------------
def ensure_user_active(user: User):
    if not user.is_active:
        raise HTTPException(403, "Account is disabled")

# ---------------------------
# Get User Profile
# ---------------------------
@router.get("/{user_id}", response_model=UserProfileResponse, summary="Get user profile")
def get_user_profile(
    user_id: str,
    current_user: User = Depends(jwt_utils.get_current_user),
    db: Session = Depends(get_db),
):
    # Ensure the authenticated user is requesting their own profile
    if str(current_user.id) != user_id:
        raise HTTPException(403, "Unauthorized access")

    # Fetch the user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    ensure_user_active(user)

    return UserProfileResponse.from_orm(user)

# ---------------------------
# Update Username + Profile Picture
# ---------------------------
@router.patch(
    "/{user_id}/profile",
    response_model=MessageResponse,
    summary="Update username and/or profile picture",
)
async def update_full_profile(
    user_id: str,
    payload: UpdateFullProfileSchema = Depends(),
    profile_image: UploadFile = File(None),
    current_user: User = Depends(jwt_utils.get_current_user),
    db: Session = Depends(get_db),
):
    if str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ensure_user_active(user)

    updated = False

    # Update Username
    if payload.username:
        new_username = payload.username.strip()

        if len(new_username) < 3:
            raise HTTPException(
                status_code=400,
                detail="Username must be at least 3 characters long",
            )

        if (
            db.query(User)
            .filter(User.username == new_username, User.id != user.id)
            .first()
        ):
            raise HTTPException(
                status_code=400,
                detail="Username already taken",
            )

        user.username = new_username
        updated = True

    # Update Profile Picture
    if profile_image:
        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/jpg"}

        if profile_image.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only JPEG, PNG, JPG, and WEBP allowed.",
            )

        file_bytes = await profile_image.read()
        image_url = upload_profile_image_to_s3(
            file_bytes,
            profile_image.filename,
        )

        user.profile_image_url = image_url
        updated = True

    if not updated:
        raise HTTPException(
            status_code=400,
            detail="No changes provided",
        )

    db.commit()
    db.refresh(user)

    return {"message": "Profile updated successfully"}


# ---------------------------
# Update Password 
# ---------------------------
@router.put("/{user_id}/password", response_model=MessageResponse, summary="Update password")
def update_password(
    user_id: str,
    payload: UpdatePasswordSchema,
    background_tasks: BackgroundTasks,  
    current_user: User = Depends(jwt_utils.get_current_user),
    db: Session = Depends(get_db),
):
    if str(current_user.id) != user_id:
        raise HTTPException(403, "Unauthorized access")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    ensure_user_active(user)

    if not hash_utils.verify_password(payload.old_password, user.hashed_password):
        raise HTTPException(400, "Old password is incorrect")

    user.hashed_password = hash_utils.hash_password(payload.password)
    db.commit()

    background_tasks.add_task(
        email_utils.send_password_changed_notification,
        user.email,
    )

    return {"message": "Password updated successfully"}


# ---------------------------
# Delete User Account
# ---------------------------
@router.delete("/{user_id}", response_model=MessageResponse, summary="Delete user account")
def delete_user_account(
    user_id: str,
    background_tasks: BackgroundTasks,  
    current_user: User = Depends(jwt_utils.get_current_user),
    db: Session = Depends(get_db),
):
    if str(current_user.id) != user_id:
        raise HTTPException(403, "Unauthorized access")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    ensure_user_active(user)

    background_tasks.add_task(
        email_utils.send_account_deleted_notification,
        user.email,
    )

    db.delete(user)
    db.commit()

    return {"message": "Account deleted successfully"}

