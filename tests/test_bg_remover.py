"""Tests for the Background Remover core engine."""

from __future__ import annotations

import io
from PIL import Image

from core.bg_remover import remove_background, has_ai_remover


def test_remove_background_transparent_mode(transparent_png_bytes):
    result = remove_background(
        transparent_png_bytes,
        mode="transparent",
        output_format="png",
        filename="test.png",
    )
    assert result.status == "success"
    assert result.output_format == "PNG"
    assert len(result.data) > 0
    assert result.new_width == 300
    assert result.new_height == 300

    # Ensure output has alpha transparency
    with Image.open(io.BytesIO(result.data)) as img:
        assert img.mode == "RGBA"
        assert "A" in img.getbands()


def test_remove_background_solid_color_mode(photo_jpeg_bytes):
    result = remove_background(
        photo_jpeg_bytes,
        mode="color",
        bg_color="#FFFFFF",
        output_format="jpeg",
        filename="photo.jpg",
    )
    assert result.status == "success"
    assert len(result.data) > 0
    assert result.new_width == 800
    assert result.new_height == 600

    with Image.open(io.BytesIO(result.data)) as img:
        assert img.mode == "RGB"


def test_remove_background_webp_export(opaque_png_bytes):
    result = remove_background(
        opaque_png_bytes,
        mode="transparent",
        output_format="webp",
        filename="opaque.png",
    )
    assert result.status == "success"
    assert result.output_format == "WEBP"
    assert len(result.data) > 0


def test_remove_background_corrupted_data():
    result = remove_background(
        b"not_an_image_data",
        filename="corrupt.png",
    )
    assert result.status == "failed"
    assert "Failed" in result.error or len(result.error) > 0
