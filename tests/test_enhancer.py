"""Tests for the Fresh Color Editor & Enhancement engine."""

from __future__ import annotations

import io
from PIL import Image

from core.enhancer import COLOR_PRESETS, enhance_image


def test_enhance_image_with_presets(photo_jpeg_bytes):
    for preset_name, preset in COLOR_PRESETS.items():
        result = enhance_image(
            photo_jpeg_bytes,
            brightness=preset.brightness,
            contrast=preset.contrast,
            saturation=preset.saturation,
            sharpness=preset.sharpness,
            auto_contrast=preset.auto_contrast,
            tint=preset.tint,
            filename=f"preset_{preset_name}.jpg",
        )
        assert result.status == "success"
        assert len(result.data) > 0
        assert result.new_width == 800
        assert result.new_height == 600


def test_enhance_image_preserves_alpha(transparent_png_bytes):
    result = enhance_image(
        transparent_png_bytes,
        brightness=1.1,
        contrast=1.2,
        saturation=1.3,
        output_format="png",
        filename="alpha_enhanced.png",
    )
    assert result.status == "success"
    assert result.output_format == "PNG"

    with Image.open(io.BytesIO(result.data)) as img:
        assert "A" in img.getbands()


def test_enhance_image_auto_contrast_and_tints(photo_jpeg_bytes):
    for tint in ("warm", "cool", "vintage"):
        result = enhance_image(
            photo_jpeg_bytes,
            auto_contrast=True,
            tint=tint,
            output_format="webp",
            filename=f"tint_{tint}.webp",
        )
        assert result.status == "success"
        assert result.output_format == "WEBP"
        assert len(result.data) > 0


def test_enhance_image_corrupted_data():
    result = enhance_image(
        b"invalid_corrupt_data",
        filename="bad.jpg",
    )
    assert result.status == "failed"
    assert len(result.error) > 0
