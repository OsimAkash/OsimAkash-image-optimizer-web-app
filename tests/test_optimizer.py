"""Tests for the optimization engine (spec: compression, metadata, savings, fallback)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from core.analyzer import analyze_image
from core.optimizer import (
    OptimizationSettings,
    calculate_savings,
    optimize_image,
    recommend_settings,
)


def test_compression_reduces_size(photo_jpeg_bytes):
    settings = OptimizationSettings(mode="Custom", quality=60, output_format="original")
    result = optimize_image(photo_jpeg_bytes, settings, filename="photo.jpg")
    assert result.status == "success"
    assert result.optimized_size < result.original_size
    assert 0 < result.saved_percent < 100
    assert result.output_format == "JPEG"
    assert result.data


def test_convert_jpeg_to_webp(photo_jpeg_bytes):
    settings = OptimizationSettings(mode="Custom", quality=80, output_format="webp")
    result = optimize_image(photo_jpeg_bytes, settings, filename="photo.jpg")
    assert result.status == "success"
    assert result.output_format == "WebP"
    assert result.output_filename.endswith(".webp")


def test_transparent_png_to_jpeg_gets_white_background(transparent_png_bytes):
    settings = OptimizationSettings(mode="Custom", quality=85, output_format="jpeg")
    result = optimize_image(transparent_png_bytes, settings, filename="icon.png")
    assert result.status == "success"
    assert result.background_applied
    image = Image.open(io.BytesIO(result.data))
    assert image.mode == "RGB"
    # a fully transparent corner composites onto pure white
    assert image.getpixel((0, 0)) == (255, 255, 255)


def test_transparent_png_stays_transparent_as_webp(transparent_png_bytes):
    settings = OptimizationSettings(mode="Custom", quality=85, output_format="webp")
    result = optimize_image(transparent_png_bytes, settings, filename="icon.png")
    assert result.status == "success"
    image = Image.open(io.BytesIO(result.data))
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0       # background stays transparent
    assert image.getpixel((150, 150))[3] == 255  # circle interior stays opaque


def test_metadata_removed_by_default(photo_jpeg_with_exif):
    settings = OptimizationSettings(mode="Custom", quality=85, output_format="original")
    result = optimize_image(photo_jpeg_with_exif, settings, filename="photo.jpg")
    assert result.status == "success"
    assert result.metadata_removed
    exif = Image.open(io.BytesIO(result.data)).getexif()
    assert not exif  # Make/Model are gone


def test_metadata_preserved_when_requested(photo_jpeg_with_exif):
    settings = OptimizationSettings(
        mode="Custom", quality=85, output_format="original", remove_metadata=False
    )
    result = optimize_image(photo_jpeg_with_exif, settings, filename="photo.jpg")
    assert result.status == "success"
    exif = Image.open(io.BytesIO(result.data)).getexif()
    assert exif.get(271) == "OptiPicTest"


def test_resize_percentage_applied(photo_jpeg_bytes):
    settings = OptimizationSettings(
        mode="Custom", quality=80, output_format="original",
        resize_mode="percent", resize_value=50,
    )
    result = optimize_image(photo_jpeg_bytes, settings, filename="photo.jpg")
    assert result.status == "success"
    assert (result.new_width, result.new_height) == (400, 300)


def test_already_optimized_file_falls_back_to_original(photo_jpeg_bytes):
    """Same format + no resize + a bigger output must return the original bytes."""
    # quality 100 on an already-tiny source usually re-encodes larger
    settings = OptimizationSettings(mode="Custom", quality=100, output_format="original",
                                    remove_metadata=False)
    result = optimize_image(photo_jpeg_bytes, settings, filename="photo.jpg")
    assert result.status == "success"
    if result.optimized_size >= result.original_size:
        assert result.data == photo_jpeg_bytes
        assert "original file kept" in result.note


def test_corrupted_image_fails_gracefully():
    result = optimize_image(b"definitely not an image", OptimizationSettings(), filename="x.jpg")
    assert result.status == "failed"
    assert result.error
    assert "Traceback" not in result.error


def test_calculate_savings_values():
    assert calculate_savings(1000, 250) == 75.0
    assert calculate_savings(1000, 1000) == 0.0
    assert calculate_savings(0, 10) == 0.0
    assert calculate_savings(100, 150) == -50.0


def test_mode_quality_mapping():
    assert OptimizationSettings(mode="Maximum Compression").effective_quality == 60
    assert OptimizationSettings(mode="Balanced").effective_quality == 80
    assert OptimizationSettings(mode="High Quality").effective_quality == 92
    assert OptimizationSettings(mode="Custom", quality=73).effective_quality == 73


def test_recommend_settings_rules(photo_jpeg_bytes, transparent_png_bytes):
    big_jpeg = analyze_image(photo_jpeg_bytes)
    settings, reason = recommend_settings(big_jpeg)
    assert reason
    assert 10 <= settings.effective_quality <= 100

    transparent = analyze_image(transparent_png_bytes)
    settings, reason = recommend_settings(transparent)
    assert settings.output_format in ("original", "webp", "png")
