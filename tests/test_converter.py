"""Tests for format conversion (spec: converter page conversions + failure handling)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from core.converter import convert_image


def test_jpeg_to_png(photo_jpeg_bytes):
    result = convert_image(photo_jpeg_bytes, "png", filename="photo.jpg")
    assert result.status == "success"
    assert result.output_format == "PNG"
    assert result.output_filename == "photo.png"
    assert Image.open(io.BytesIO(result.data)).format == "PNG"


def test_png_to_jpeg(opaque_png_bytes):
    result = convert_image(opaque_png_bytes, "jpeg", filename="shot.png")
    assert result.status == "success"
    assert Image.open(io.BytesIO(result.data)).mode == "RGB"


def test_webp_to_jpeg(webp_bytes):
    result = convert_image(webp_bytes, "jpeg", filename="pic.webp")
    assert result.status == "success"
    assert result.output_format == "JPEG"


def test_bmp_to_webp(bmp_bytes):
    result = convert_image(bmp_bytes, "webp", filename="pic.bmp")
    assert result.status == "success"
    assert result.output_format == "WebP"


def test_tiff_to_png(tiff_bytes):
    result = convert_image(tiff_bytes, "png", filename="scan.tiff")
    assert result.status == "success"
    assert result.output_format == "PNG"


def test_transparent_png_to_jpeg_notes_background(transparent_png_bytes):
    result = convert_image(transparent_png_bytes, "jpeg", filename="icon.png")
    assert result.status == "success"
    assert result.background_applied
    assert "white" in result.note.lower()
    assert Image.open(io.BytesIO(result.data)).mode == "RGB"


def test_quality_affects_jpeg_size(photo_jpeg_bytes):
    low = convert_image(photo_jpeg_bytes, "jpeg", quality=25)
    high = convert_image(photo_jpeg_bytes, "jpeg", quality=95)
    assert low.optimized_size < high.optimized_size


def test_invalid_data_fails_gracefully():
    result = convert_image(b"nope", "png", filename="bad.png")
    assert result.status == "failed"
    assert result.error
