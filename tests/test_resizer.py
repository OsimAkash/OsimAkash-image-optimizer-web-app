"""Tests for dimension math and the resize pipeline (spec: resizer)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from core.resizer import compute_resize_dimensions, resize_data, resize_image


def test_width_mode_maintains_aspect():
    assert compute_resize_dimensions(4000, 3000, "width", 1600) == (1600, 1200)


def test_height_mode_maintains_aspect():
    assert compute_resize_dimensions(1920, 1080, "height", 540) == (960, 540)


def test_width_mode_without_aspect_keeps_height():
    assert compute_resize_dimensions(4000, 3000, "width", 1600, maintain_aspect=False) == (1600, 3000)


def test_percent_mode_scales_both():
    assert compute_resize_dimensions(800, 600, "percent", 50) == (400, 300)
    assert compute_resize_dimensions(800, 600, "percent", 200) == (1600, 1200)


def test_minimum_one_pixel():
    assert compute_resize_dimensions(10, 10, "width", 0) == (1, 1)
    assert compute_resize_dimensions(10, 10, "percent", 1) == (1, 1)


def test_original_mode_is_noop():
    assert compute_resize_dimensions(640, 480, "original", 100) == (640, 480)


def test_resize_image_uses_lanczos(opaque_png_bytes):
    image = Image.open(io.BytesIO(opaque_png_bytes))
    resized = resize_image(image, 200, 150)
    assert resized.size == (200, 150)
    assert resized.mode == "RGB"


def test_resize_data_changes_dimensions(photo_jpeg_bytes):
    result = resize_data(photo_jpeg_bytes, "width", 320, filename="photo.jpg")
    assert result.status == "success"
    assert (result.new_width, result.new_height) == (320, 240)
    assert result.output_filename.endswith("-resized.jpg")
    assert Image.open(io.BytesIO(result.data)).size == (320, 240)


def test_resize_data_same_size_keeps_original(photo_jpeg_bytes):
    result = resize_data(photo_jpeg_bytes, "width", 800, filename="photo.jpg")
    assert result.status == "success"
    assert result.data == photo_jpeg_bytes
    assert "kept" in result.note


def test_resize_data_invalid_input_fails():
    result = resize_data(b"junk", "width", 300, filename="bad.jpg")
    assert result.status == "failed"
    assert result.error
