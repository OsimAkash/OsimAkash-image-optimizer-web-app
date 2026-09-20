"""Tests for upload validation (spec: image validation + invalid image handling)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from utils.file_utils import sanitize_filename
from utils.validators import validate_upload


def test_valid_jpeg_passes(fake_upload_cls, photo_jpeg_bytes):
    result = validate_upload(fake_upload_cls("photo.jpg", photo_jpeg_bytes, "image/jpeg"))
    assert result.ok
    assert result.content_format == "JPEG"
    assert result.data == photo_jpeg_bytes


def test_unsupported_extension_rejected(fake_upload_cls, photo_jpeg_bytes):
    result = validate_upload(fake_upload_cls("payload.exe", photo_jpeg_bytes))
    assert not result.ok
    assert "Unsupported image format" in result.message


def test_empty_file_rejected(fake_upload_cls):
    result = validate_upload(fake_upload_cls("empty.png", b""))
    assert not result.ok
    assert "empty" in result.message.lower()


def test_oversized_file_rejected(fake_upload_cls, photo_jpeg_bytes):
    result = validate_upload(
        fake_upload_cls("big.jpg", photo_jpeg_bytes), max_file_size=10
    )
    assert not result.ok
    assert "exceeds the allowed size" in result.message


def test_corrupted_image_rejected(fake_upload_cls):
    garbage = b"\xff\xd8\xff\xe0not-actually-a-jpeg" + b"\x00" * 256
    result = validate_upload(fake_upload_cls("broken.jpg", garbage, "image/jpeg"))
    assert not result.ok
    assert "Unable to read this image" in result.message


def test_renamed_content_is_detected(fake_upload_cls, opaque_png_bytes):
    """A PNG renamed to .jpg must still be accepted — and the note must flag it."""
    result = validate_upload(fake_upload_cls("actually-png.jpg", opaque_png_bytes, "image/jpeg"))
    assert result.ok
    assert result.content_format == "PNG"
    assert result.note


def test_non_image_content_with_image_extension_rejected(fake_upload_cls):
    result = validate_upload(fake_upload_cls("fake.png", b"just text, not an image"))
    assert not result.ok


def test_video_mime_rejected(fake_upload_cls, photo_jpeg_bytes):
    result = validate_upload(fake_upload_cls("clip.jpg", photo_jpeg_bytes, "video/mp4"))
    assert not result.ok
    assert "Unsupported image format" in result.message


def test_oversized_dimensions_rejected(fake_upload_cls):
    big = Image.new("RGB", (1200, 1200), (200, 10, 10))
    buffer = io.BytesIO()
    big.save(buffer, format="PNG")
    result = validate_upload(fake_upload_cls("big.png", buffer.getvalue()), max_pixels=500_000)
    assert not result.ok
    assert "too large" in result.message


def test_sanitize_filename_strips_paths_and_dots():
    assert sanitize_filename("../../etc/passwd.png") == "passwd.png"
    assert sanitize_filename("..\\..\\evil.JPG") == "evil.jpg"
    assert sanitize_filename("") == "image"
    assert sanitize_filename("...") == "image"
    assert sanitize_filename("my holiday photo (2024).png") == "my holiday photo (2024).png"


def test_sanitize_filename_caps_length():
    long_name = "x" * 300 + ".jpg"
    sanitized = sanitize_filename(long_name)
    assert len(sanitized) < 80
    assert sanitized.endswith(".jpg")
