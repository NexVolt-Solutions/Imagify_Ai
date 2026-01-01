from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import replicate
import requests

from app.models import Wallpaper, WallpaperStatusEnum, User
from app.core.database import get_db
from app.api.routes.utils import jwt_utils
from app.api.routes.utils.s3_utils import upload_wallpaper_to_s3
from app.schemas import (
    WallpaperCreateSchema,
    WallpaperResponseSchema,
    WallpaperListSchema,
    WallpaperDeleteResponse,
    AISuggestionSchema,
    AISuggestionResponse,
)
from app.core.config import settings

router = APIRouter(prefix="/wallpapers", tags=["Wallpapers"])

replicate_client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)

SIZE_MAP = {
    "1:1": (1024, 1024),
    "2:3 Portrait": (832, 1216),
    "2:3 Landscape": (1216, 832),
}
STYLE_SUFFIXES = {
    "Colorful": ", vibrant colors, sharp focus, crisp details, professional lighting",
    "3D Render": ", high-quality CGI, realistic materials, sharp textures, clean lighting",
    "Photorealistic": ", photorealistic, natural lighting, realistic textures, DSLR-style depth",
    "Illustration": ", digital illustration, clean linework, professional concept art",
    "Oil Painting": ", oil painting style, detailed brushstrokes, fine art quality",
    "Watercolor": ", watercolor painting, soft gradients, paper texture, artistic clarity",
    "Cyberpunk": ", neon lighting, futuristic cityscape, sharp details",
    "Fantasy": ", epic fantasy art, magical lighting, cinematic atmosphere",
    "Anime": ", anime style, clean line art, vibrant colors, smooth shading",
    "Cartoon": ", cartoon style, bold outlines, playful look",
    "Chibi": ", chibi style, cute proportions, pastel colors",
    "Steampunk": ", brass machinery, intricate details, dramatic lighting",
    "Pixel Art": ", pixelated retro style, sharp edges, 8-bit look",
    "Low Poly": ", simplified geometry, polygonal shapes, clean lighting",
    "Isometric": ", isometric perspective, sharp details, game-style rendering",
    "Minimalist": ", clean composition, flat colors, simple shapes",
    "Synthwave": ", neon retro style, glowing grids, 1980s futuristic vibe",
    "Retro Futurism": ", vintage sci-fi look, bold colors, futuristic machines",
    "Solarpunk": ", eco-futuristic style, lush greenery, sustainable cityscapes",
    "Concept Art": ", professional concept art, cinematic composition, sharp details",
    "Digital Painting": ", digital painting style, smooth brushwork, layered textures",
    "Game Art": ", stylized game concept, sharp focus, vibrant atmosphere"
}


# ---------------------------
# Background Task: Generate Wallpaper
# ---------------------------
def generate_wallpaper_image(
    wallpaper_id: str,
    prompt: str,
    size: str,
    style: str,
    db_session_factory,
):
    db: Session = db_session_factory()

    wallpaper = db.query(Wallpaper).filter(Wallpaper.id == wallpaper_id).first()
    if not wallpaper:
        return

    try:
        width, height = SIZE_MAP.get(size, (1024, 1024))
        style_suffix = STYLE_SUFFIXES.get(style, "")
        final_prompt = f"{prompt}{style_suffix}"

        output = replicate_client.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": final_prompt,
                "width": width,
                "height": height,
                "num_outputs": 1,
                "guidance": 3.5,
                "num_inference_steps": 4,
            },
        )

        if not output or not isinstance(output, list):
            wallpaper.status = WallpaperStatusEnum.FAILED
            db.commit()
            return

        file_obj = output[0]

        if isinstance(file_obj, str):
            image_bytes = requests.get(file_obj).content
        else:
            image_bytes = file_obj.read()

        filename = f"{uuid4()}.webp"
        image_url = upload_wallpaper_to_s3(image_bytes, filename)

        wallpaper.image_url = image_url
        wallpaper.ai_model = "black-forest-labs/flux-schnell"
        wallpaper.status = WallpaperStatusEnum.COMPLETED
        db.commit()

    except Exception:
        wallpaper.status = WallpaperStatusEnum.FAILED
        db.commit()

    finally:
        db.close()


# ---------------------------
# AI Suggestion
# ---------------------------
@router.post("/suggest", response_model=AISuggestionResponse)
def suggest_prompt(
    payload: AISuggestionSchema,
    token: dict = Depends(jwt_utils.get_current_user),
):
    system_prompt = (
        "You enhance short prompts for image generation. "
        "Rewrite the user's prompt to be more detailed, vivid, and descriptive. "
        "Keep it short (1–2 sentences). Do not add styles unless the user mentions them."
    )

    response = replicate_client.run(
        "meta/meta-llama-3-70b-instruct",
        input={
            "prompt": f"{system_prompt}\nUser prompt: {payload.prompt}\nEnhanced prompt:",
            "temperature": 0.6,
            "max_tokens": 120,
        },
    )

    enhanced = "".join(response).strip()
    return AISuggestionResponse(suggestion=enhanced)


# ---------------------------
# Create Wallpaper
# ---------------------------
@router.post("/", response_model=WallpaperResponseSchema)
def create_wallpaper(
    background_tasks: BackgroundTasks,
    payload: WallpaperCreateSchema,
    token: dict = Depends(jwt_utils.get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == token["sub"]).first()
    if not user:
        raise HTTPException(404, "User not found")

    wallpaper = Wallpaper(
        user_id=user.id,
        prompt=payload.prompt,
        size=payload.size,
        style=payload.style,
        title=payload.title,
        ai_model=None,
        status=WallpaperStatusEnum.PENDING,
    )
    db.add(wallpaper)
    db.commit()
    db.refresh(wallpaper)

    background_tasks.add_task(
        generate_wallpaper_image,
        wallpaper.id,
        payload.prompt,
        payload.size,
        payload.style,
        get_db,
    )

    return wallpaper


# ---------------------------
# Recreate Wallpaper
# ---------------------------
@router.post("/{wallpaper_id}/recreate", response_model=WallpaperResponseSchema)
def recreate_wallpaper(
    background_tasks: BackgroundTasks,
    wallpaper_id: str,
    token: dict = Depends(jwt_utils.get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == token["sub"]).first()
    if not user:
        raise HTTPException(404, "User not found")

    original = db.query(Wallpaper).filter(Wallpaper.id == wallpaper_id).first()
    if not original or original.user_id != user.id:
        raise HTTPException(404, "Wallpaper not found")

    new_wallpaper = Wallpaper(
        user_id=user.id,
        prompt=original.prompt,
        size=original.size,
        style=original.style,
        title=original.title,
        ai_model=None,
        status=WallpaperStatusEnum.PENDING,
    )
    db.add(new_wallpaper)
    db.commit()
    db.refresh(new_wallpaper)

    background_tasks.add_task(
        generate_wallpaper_image,
        new_wallpaper.id,
        original.prompt,
        original.size,
        original.style,
        get_db,
    )

    return new_wallpaper


# ---------------------------
# List Wallpapers
# ---------------------------
@router.get("/", response_model=WallpaperListSchema)
def list_wallpapers(
    token: dict = Depends(jwt_utils.get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == token["sub"]).first()
    if not user:
        raise HTTPException(404, "User not found")

    wallpapers = (
        db.query(Wallpaper)
        .filter(Wallpaper.user_id == user.id)
        .order_by(Wallpaper.created_at.desc())
        .all()
    )

    return {"wallpapers": wallpapers}


# ---------------------------
# Delete Wallpaper
# ---------------------------
@router.delete("/{wallpaper_id}", response_model=WallpaperDeleteResponse)
def delete_wallpaper(
    wallpaper_id: str,
    token: dict = Depends(jwt_utils.get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == token["sub"]).first()
    if not user:
        raise HTTPException(404, "User not found")

    wallpaper = db.query(Wallpaper).filter(Wallpaper.id == wallpaper_id).first()
    if not wallpaper or wallpaper.user_id != user.id:
        raise HTTPException(404, "Wallpaper not found")

    deleted_info = WallpaperResponseSchema(
        id=wallpaper.id,
        prompt=wallpaper.prompt,
        size=wallpaper.size,
        style=wallpaper.style,
        title=wallpaper.title,
        ai_model=wallpaper.ai_model,
        thumbnail_url=wallpaper.thumbnail_url,
        image_url=wallpaper.image_url,
        created_at=wallpaper.created_at,
    )

    db.delete(wallpaper)
    db.commit()

    return {
        "message": "Wallpaper deleted successfully",
        "deleted_wallpaper": deleted_info,
    }


# ---------------------------
# Download Wallpaper
# ---------------------------
@router.get("/{wallpaper_id}/download", response_model=WallpaperResponseSchema)
def download_wallpaper(
    wallpaper_id: str,
    token: dict = Depends(jwt_utils.get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == token["sub"]).first()
    if not user:
        raise HTTPException(404, "User not found")

    wallpaper = db.query(Wallpaper).filter(Wallpaper.id == wallpaper_id).first()
    if not wallpaper or wallpaper.user_id != user.id:
        raise HTTPException(404, "Wallpaper not found")

    if not wallpaper.image_url:
        raise HTTPException(400, "Wallpaper image not generated yet")

    return WallpaperResponseSchema(
        id=wallpaper.id,
        prompt=wallpaper.prompt,
        size=wallpaper.size,
        style=wallpaper.style,
        title=wallpaper.title,
        ai_model=wallpaper.ai_model,
        thumbnail_url=wallpaper.thumbnail_url,
        image_url=wallpaper.image_url,
        created_at=wallpaper.created_at,
    )

