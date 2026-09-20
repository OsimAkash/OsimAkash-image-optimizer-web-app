"""Shared pytest fixtures: sample images and an UploadFile-like test double."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _photo_array(width: int = 800, height: int = 600, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = np.zeros((height, width, 3), dtype=np.float32)
    gradient = np.linspace(40, 220, width, dtype=np.float32)
    base += gradient[None, :, None]
    noise = rng.normal(0, 18, (height, width, 3))
    return np.clip(base + noise, 0, 255).astype(np.uint8)


def _encode(image: Image.Image, fmt: str, **kwargs) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


@pytest.fixture
def photo_jpeg_bytes() -> bytes:
    """A noisy JPEG that compresses well — realistic photo content."""
    return _encode(Image.fromarray(_photo_array(), "RGB"), "JPEG", quality=92)


@pytest.fixture
def photo_jpeg_with_exif() -> bytes:
    image = Image.fromarray(_photo_array(seed=11), "RGB")
    exif = Image.Exif()
    exif[271] = "OptiPicTest"   # Make
    exif[272] = "UnitCam 1.0"   # Model
    return _encode(image, "JPEG", quality=92, exif=exif.tobytes())


@pytest.fixture
def transparent_png_bytes() -> bytes:
    """A PNG with real transparency: an opaque circle on a fully transparent background."""
    array = np.zeros((300, 300, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:300, 0:300]
    array[..., 0] = (xx / 299 * 255).astype(np.uint8)
    array[..., 1] = 90
    array[..., 2] = 200
    inside = (xx - 150) ** 2 + (yy - 150) ** 2 < 120 ** 2
    array[..., 3] = np.where(inside, 255, 0).astype(np.uint8)
    return _encode(Image.fromarray(array, "RGBA"), "PNG")


@pytest.fixture
def opaque_png_bytes() -> bytes:
    return _encode(Image.fromarray(_photo_array(seed=3), "RGB"), "PNG")


@pytest.fixture
def webp_bytes() -> bytes:
    return _encode(Image.fromarray(_photo_array(seed=5), "RGB"), "WEBP", quality=90)


@pytest.fixture
def bmp_bytes() -> bytes:
    return _encode(Image.fromarray(_photo_array(seed=9)[:200, :200], "RGB"), "BMP")


@pytest.fixture
def tiff_bytes() -> bytes:
    return _encode(Image.fromarray(_photo_array(seed=13)[:200, :200], "RGB"), "TIFF")


class FakeUpload:
    """Minimal stand-in for streamlit's UploadedFile."""

    def __init__(self, name: str, data: bytes, mime: str = "application/octet-stream"):
        self.name = name
        self.type = mime
        self._data = data
        self.size = len(data)

    def getvalue(self) -> bytes:
        return self._data


@pytest.fixture
def fake_upload_cls():
    return FakeUpload
