"""Pictures for emails: an admin uploads one, it is stored in a public Supabase
Storage bucket, and the image block points at its URL.

Mail clients fetch images from the open web, so the file must be public and
stable — hence a public bucket rather than anything behind the API. The upload is
checked (a real PNG / JPEG / GIF / WebP, under :data:`MAX_BYTES`) and a large
still image is scaled down to :data:`MAX_WIDTH`, since an email shows it at most
600px wide and a heavy picture is a slow, clipped email. Animated GIFs are kept
as they are.
"""

from __future__ import annotations

import io
import uuid

import requests
from django.conf import settings
from django.utils import timezone

from accounts.supabase_admin import is_configured

BUCKET = "email-images"
MAX_BYTES = 5 * 1024 * 1024
#: Twice the email's width, so the picture stays sharp on a high-density screen.
MAX_WIDTH = 1200
_FORMATS = {"PNG": ("png", "image/png"), "JPEG": ("jpg", "image/jpeg"), "GIF": ("gif", "image/gif"), "WEBP": ("webp", "image/webp")}
_TIMEOUT = 20


class ImageError(Exception):
    """Why an upload was refused, worded for the admin."""


def _prepare(data: bytes) -> tuple[bytes, str, str]:
    """Check an upload and shrink a large still image: ``(bytes, ext, type)``."""
    from PIL import Image, UnidentifiedImageError

    if len(data) > MAX_BYTES:
        raise ImageError(f"That file is over {MAX_BYTES // (1024 * 1024)} MB.")
    try:
        image = Image.open(io.BytesIO(data))
        image.verify()  # a truncated or disguised file fails here
        image = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ImageError("That isn't a picture we can use (PNG, JPEG, GIF or WebP).") from exc
    fmt = image.format
    if fmt not in _FORMATS:
        raise ImageError("Use a PNG, JPEG, GIF or WebP picture.")
    ext, content_type = _FORMATS[fmt]
    if image.width > MAX_WIDTH and not getattr(image, "is_animated", False):
        height = round(image.height * MAX_WIDTH / image.width)
        image = image.resize((MAX_WIDTH, height), Image.LANCZOS)
        out = io.BytesIO()
        if fmt == "JPEG":
            image.convert("RGB").save(out, "JPEG", quality=85, optimize=True)
        else:
            image.save(out, fmt)
        data = out.getvalue()
    return data, ext, content_type


def _storage(path: str) -> str:
    return f"{settings.SUPABASE_URL.strip().rstrip('/')}/storage/v1/{path}"


def _headers(**extra) -> dict:
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}", **extra}


def _create_bucket() -> None:
    """Make the public bucket (idempotent — "already exists" is fine)."""
    resp = requests.post(
        _storage("bucket"),
        json={"id": BUCKET, "name": BUCKET, "public": True},
        headers=_headers(),
        timeout=_TIMEOUT,
    )
    if resp.status_code >= 400 and "exist" not in resp.text.lower():
        resp.raise_for_status()


def public_url(path: str) -> str:
    return _storage(f"object/public/{BUCKET}/{path}")


def upload(data: bytes) -> str:
    """Store an uploaded picture and return its public URL."""
    if not is_configured():
        raise ImageError("Image uploads need Supabase storage, which isn't configured on this server.")
    body, ext, content_type = _prepare(data)
    path = f"{timezone.now():%Y/%m}/{uuid.uuid4().hex}.{ext}"

    def put() -> requests.Response:
        return requests.post(
            _storage(f"object/{BUCKET}/{path}"),
            data=body,
            headers=_headers(**{"Content-Type": content_type, "Cache-Control": "max-age=31536000"}),
            timeout=_TIMEOUT,
        )

    resp = put()
    if resp.status_code in (400, 404) and "bucket" in resp.text.lower():
        _create_bucket()  # the first upload on a new project makes the bucket
        resp = put()
    resp.raise_for_status()
    return public_url(path)
