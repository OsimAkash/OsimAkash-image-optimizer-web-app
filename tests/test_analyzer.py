"""Tests for image analysis, thumbnails and size estimation (spec: analysis + estimation)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from core.analyzer import analyze_image, estimate_output_size, make_thumbnail


def test_analyze_reports_metadata(photo_jpeg_bytes):
    info = analyze_image(photo_jpeg_bytes, filename="photo.jpg")
    assert info.format == "JPEG"
    assert (info.width, info.height) == (800, 600)
    assert info.mode == "RGB"
    assert info.size_bytes == len(photo_jpeg_bytes)
    assert not info.has_alpha
    assert info.megapixels == 0.48


def test_analyze_detects_transparency(transparent_png_bytes):
    info = analyze_image(transparent_png_bytes)
    assert info.format == "PNG"
    assert info.has_alpha


def test_make_thumbnail_is_small_and_valid(photo_jpeg_bytes):
    thumb = make_thumbnail(photo_jpeg_bytes, max_side=200)
    assert thumb
    image = Image.open(io.BytesIO(thumb))
    assert max(image.size) <= 200
    assert image.format in ("JPEG", "PNG")


def test_make_thumbnail_survives_garbage():
    assert make_thumbnail(b"junk") == b""


def test_estimate_returns_range_smaller_than_original(photo_jpeg_bytes):
    estimate = estimate_output_size(photo_jpeg_bytes, target_format="webp", quality=80)
    assert 0 < estimate.low_bytes <= estimate.high_bytes
    assert estimate.savings_low <= estimate.savings_high
    assert 0 <= estimate.savings_low
    assert estimate.note  # always labeled as an estimate
    # a well-compressed WebP should not exceed the source JPEG
    assert estimate.high_bytes < len(photo_jpeg_bytes)


def test_estimate_respects_resize(photo_jpeg_bytes):
    full = estimate_output_size(photo_jpeg_bytes, target_format="jpeg", quality=85)
    half = estimate_output_size(
        photo_jpeg_bytes, target_format="jpeg", quality=85, resize_mode="percent", resize_value=50
    )
    assert half.high_bytes < full.high_bytes


def test_estimate_handles_target_original(photo_jpeg_bytes):
    estimate = estimate_output_size(photo_jpeg_bytes, target_format="original", quality=80)
    assert estimate.low_bytes > 0


def test_estimate_survives_bad_input():
    estimate = estimate_output_size(b"junk", target_format="jpeg", quality=80)
    assert estimate.note == "Estimate unavailable for this image."
