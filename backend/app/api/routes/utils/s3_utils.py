import boto3
from uuid import uuid4
from app.core.config import settings

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)

def _build_s3_url(key: str) -> str:
    if settings.CLOUDFRONT_DOMAIN:
        return f"https://{settings.CLOUDFRONT_DOMAIN}/{key}"
    return f"https://{settings.AWS_S3_BUCKET}.s3.amazonaws.com/{key}"


def upload_profile_image_to_s3(file_bytes: bytes, filename: str) -> str:
    key = f"profile_pics/{uuid4()}_{filename}"

    s3_client.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType="image/jpeg",
        ACL="public-read",
    )

    return _build_s3_url(key)


def upload_wallpaper_to_s3(file_bytes: bytes, filename: str) -> str:
    key = f"wallpapers/{uuid4()}_{filename}"

    s3_client.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType="image/webp",
        ACL="public-read",
    )

    return _build_s3_url(key)

