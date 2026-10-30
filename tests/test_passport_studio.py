"""Tests for Passport & Stamp Photo Studio Core Engine."""

from __future__ import annotations

import io
from PIL import Image

from core.passport_studio import (
    OFFICIAL_BACKDROPS,
    PASSPORT_PRESETS,
    generate_passport_photo,
    generate_print_sheet,
)


def test_passport_presets_definitions():
    assert "passport_bd_global" in PASSPORT_PRESETS
    assert "stamp_standard" in PASSPORT_PRESETS
    assert "passport_us_visa" in PASSPORT_PRESETS
    assert "stamp_large" in PASSPORT_PRESETS

    bd = PASSPORT_PRESETS["passport_bd_global"]
    assert bd.width_mm == 35.0
    assert bd.height_mm == 45.0
    assert bd.width_px == 413
    assert bd.height_px == 531

    stamp = PASSPORT_PRESETS["stamp_standard"]
    assert stamp.width_mm == 20.0
    assert stamp.height_mm == 25.0
    assert stamp.width_px == 236
    assert stamp.height_px == 295


def test_generate_passport_photo_bd_standard(photo_jpeg_bytes):
    result = generate_passport_photo(
        photo_jpeg_bytes,
        preset_key="passport_bd_global",
        bg_mode="white",
        output_format="jpeg",
        filename="applicant.jpg",
    )
    assert result.status == "success"
    assert result.width_px == 413
    assert result.height_px == 531
    assert result.width_mm == 35.0
    assert result.height_mm == 45.0
    assert len(result.data) > 0

    with Image.open(io.BytesIO(result.data)) as img:
        assert img.size == (413, 531)
        assert img.mode == "RGB"


def test_generate_stamp_size_photo(photo_jpeg_bytes):
    result = generate_passport_photo(
        photo_jpeg_bytes,
        preset_key="stamp_standard",
        bg_mode="light_blue",
        output_format="jpeg",
        filename="stamp_applicant.jpg",
    )
    assert result.status == "success"
    assert result.width_px == 236
    assert result.height_px == 295
    assert result.width_mm == 20.0
    assert result.height_mm == 25.0
    assert len(result.data) > 0

    with Image.open(io.BytesIO(result.data)) as img:
        assert img.size == (236, 295)


def test_generate_passport_us_visa_photo(photo_jpeg_bytes):
    result = generate_passport_photo(
        photo_jpeg_bytes,
        preset_key="passport_us_visa",
        bg_mode="white",
        output_format="jpeg",
        filename="visa.jpg",
    )
    assert result.status == "success"
    assert result.width_px == 600
    assert result.height_px == 600
    assert len(result.data) > 0

    with Image.open(io.BytesIO(result.data)) as img:
        assert img.size == (600, 600)


def test_generate_print_sheet(photo_jpeg_bytes):
    # First generate a passport photo
    res = generate_passport_photo(
        photo_jpeg_bytes,
        preset_key="passport_bd_global",
        sheet_layout="6_copies",
        filename="sheet_test.jpg",
    )
    assert res.status == "success"
    assert len(res.sheet_data) > 0
    assert res.sheet_copies == 6
    assert "-sheet-4R-6pcs" in res.sheet_filename

    # Verify sheet dimensions (4R paper landscape 1800 x 1200 @ 300 DPI)
    with Image.open(io.BytesIO(res.sheet_data)) as sheet_img:
        assert sheet_img.size == (1800, 1200)


def test_passport_photo_corrupted_data():
    result = generate_passport_photo(
        b"corrupted_binary_data",
        filename="corrupted.jpg",
    )
    assert result.status == "failed"
    assert len(result.error) > 0
