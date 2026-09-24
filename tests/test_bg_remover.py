"""Tests for the Background Remover core engine."""

from __future__ import annotations

import io
from PIL import Image

from core.bg_remover import (
    AI_MODELS,
    STUDIO_PALETTES,
    has_ai_remover,
    remove_background,
)


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
    assert len(result.original_thumb) > 0

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


def test_remove_background_bokeh_blur_mode(photo_jpeg_bytes):
    result = remove_background(
        photo_jpeg_bytes,
        mode="blur",
        blur_radius=20,
        output_format="jpeg",
        filename="portrait.jpg",
    )
    assert result.status == "success"
    assert len(result.data) > 0
    assert result.new_width == 800
    assert result.new_height == 600

    with Image.open(io.BytesIO(result.data)) as img:
        assert img.mode == "RGB"


def test_remove_background_custom_image_mode(photo_jpeg_bytes, opaque_png_bytes):
    result = remove_background(
        photo_jpeg_bytes,
        mode="custom_image",
        bg_image_data=opaque_png_bytes,
        output_format="png",
        filename="custom_composite.png",
    )
    assert result.status == "success"
    assert len(result.data) > 0
    assert result.new_width == 800
    assert result.new_height == 600


def test_remove_background_alpha_mask_mode(opaque_png_bytes):
    result = remove_background(
        opaque_png_bytes,
        mode="mask",
        output_format="png",
        filename="matte.png",
    )
    assert result.status == "success"
    assert len(result.data) > 0


def test_remove_background_chroma_keyer(opaque_png_bytes):
    result = remove_background(
        opaque_png_bytes,
        engine="chroma",
        tolerance=40,
        edge_feather=2,
        defringe=True,
        output_format="png",
        filename="greenscreen.png",
    )
    assert result.status == "success"
    assert len(result.data) > 0


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


def test_ai_models_and_palettes_exist():
    assert "u2net" in AI_MODELS
    assert "u2net_human_seg" in AI_MODELS
    assert "Studio White" in STUDIO_PALETTES
    assert isinstance(has_ai_remover(), bool)
