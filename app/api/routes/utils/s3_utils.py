import boto3
import mimetypes
from uuid import uuid4
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings


# ---------------------------
# S3 Client
# ---------------------------
s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)


# ---------------------------
# Build Public URL (S3 or CloudFront)
# ---------------------------
def _build_s3_url(key: str) -> str:
    """
    Build a public URL for the uploaded file.
    Uses CloudFront if configured, otherwise S3.
    """
    if settings.CLOUDFRONT_DOMAIN:
        return f"https://{settings.CLOUDFRONT_DOMAIN}/{key}"

    return f"https://{settings.AWS_S3_BUCKET}.s3.amazonaws.com/{key}"


# ---------------------------
# Internal Upload Helper
# ---------------------------
def _upload_to_s3(folder: str, file_bytes: bytes, filename: str) -> str:
    """
    Upload a file to S3 inside a specific folder.
    Automatically detects MIME type and generates a safe unique key.
    """

    # Generate a safe unique key (ignore original filename)
    extension = filename.split(".")[-1].lower() if "." in filename else "bin"
    key = f"{folder}/{uuid4()}.{extension}"

    # Auto-detect MIME type
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = "application/octet-stream"

    try:
        s3_client.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"S3 upload failed: {str(e)}")

    return _build_s3_url(key)


# ---------------------------
# Upload Profile Image
# ---------------------------
def upload_profile_image_to_s3(file_bytes: bytes, filename: str) -> str:
    """
    Upload a profile image to S3.
    """
    return _upload_to_s3("profile_pics", file_bytes, filename)


# ---------------------------
# Upload Wallpaper Image
# ---------------------------
def upload_wallpaper_to_s3(file_bytes: bytes, filename: str) -> str:
    """
    Upload a wallpaper image to S3.
    """
    return _upload_to_s3("wallpapers", file_bytes, filename)
