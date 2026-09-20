"""Upload validation for OptiPic.

Every uploaded file is checked against:

* an empty-file guard,
* the extension whitelist,
* the configurable maximum file size,
* the declared MIME type (when the browser provides one),
* the *actual* image content decoded by Pillow (never trust the filename),
* image dimension limits that protect against decompression bombs.

The functions never raise on bad input — they always return a
:class:`ValidationResult` carrying a user-friendly message.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from utils.file_utils import format_bytes

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"}

# Formats Pillow may report when decoding the *content* (MPO is a JPEG variant).
ALLOWED_CONTENT_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "TIFF", "MPO"}

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/jpg", "image/pjpeg", "image/png", "image/webp",
    "image/bmp", "image/x-ms-bmp", "image/tiff", "image/tif", "image/x-tiff",
}

# Browsers sometimes send application/octet-stream — the content check decides then.
_REJECTED_MIME_PREFIXES = ("video/", "audio/", "text/", "application/zip")

DEFAULT_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
DEFAULT_MAX_PIXELS = 60_000_000           # ~60 megapixels

# Extension -> set of content formats that legitimately match it.
_EXTENSION_FORMATS = {
    "jpg": {"JPEG", "MPO"}, "jpeg": {"JPEG", "MPO"}, "png": {"PNG"},
    "webp": {"WEBP"}, "bmp": {"BMP"}, "tif": {"TIFF"}, "tiff": {"TIFF"},
}


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating one uploaded file."""

    ok: bool
    message: str = ""          # user-friendly error (empty when ok)
    data: bytes = b""          # raw bytes when ok
    content_format: str = ""   # format detected from the bytes, e.g. "PNG"
    note: str = ""             # non-fatal observation, e.g. extension mismatch


def validate_upload(
    file_like,
    *,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> ValidationResult:
    """Validate an uploaded file object (Streamlit ``UploadedFile``-like)."""
    filename = getattr(file_like, "name", "") or ""
    mime = (getattr(file_like, "type", "") or "").lower()

    try:
        data = file_like.getvalue() if hasattr(file_like, "getvalue") else bytes(file_like.read())
    except (OSError, MemoryError):
        return ValidationResult(False, "The file could not be read. Please try again.")

    if not data:
        return ValidationResult(False, "The file is empty.")

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        return ValidationResult(False, "Unsupported image format.")

    if len(data) > max_file_size:
        return ValidationResult(
            False, f"File exceeds the allowed size (max {format_bytes(max_file_size)} per image)."
        )

    if mime and mime.startswith(_REJECTED_MIME_PREFIXES):
        return ValidationResult(False, "Unsupported image format.")

    try:
        with Image.open(io.BytesIO(data)) as probe:
            content_format = (probe.format or "").upper()
            probe.verify()  # cheap structural integrity check of headers/checksums
    except Image.DecompressionBombError:
        return ValidationResult(False, "Image dimensions are too large to process safely.")
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        logger.info("Rejected %s: unreadable image content (%s)", filename, exc)
        return ValidationResult(False, "Unable to read this image. The file may be corrupted.")

    if content_format not in ALLOWED_CONTENT_FORMATS:
        return ValidationResult(False, "The file content is not a supported image format.")

    # Fully decode once so truncated or corrupt payloads fail here, not mid-optimization.
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            image.load()
    except Image.DecompressionBombError:
        return ValidationResult(False, "Image dimensions are too large to process safely.")
    except (OSError, ValueError, MemoryError) as exc:
        logger.info("Rejected %s: decode failed (%s)", filename, exc)
        return ValidationResult(False, "Unable to read this image. The file may be corrupted.")

    if width * height > max_pixels:
        return ValidationResult(
            False,
            f"Image dimensions are too large (limit is about {max_pixels // 1_000_000} megapixels).",
        )

    note = ""
    if extension and content_format not in _EXTENSION_FORMATS.get(extension, set()):
        note = "Extension does not match the actual image content — the real format is used."

    return ValidationResult(True, data=data, content_format=content_format, note=note)
