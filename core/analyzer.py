"""Image inspection: metadata extraction, NumPy-powered content statistics,
output-size estimation and thumbnail generation."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

from core.converter import FORMAT_LABELS, detect_transparency, encode_image, prepare_for_format
from core.resizer import compute_resize_dimensions

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageInfo:
    """Facts extracted from a single image (no raw pixels kept)."""

    format: str            # display label, e.g. "JPEG"
    width: int
    height: int
    mode: str              # Pillow mode, e.g. "RGB"
    size_bytes: int
    has_alpha: bool
    megapixels: float
    is_photo_like: bool
    brightness: float
    contrast: float


@dataclass(frozen=True)
class SizeEstimate:
    """A deliberately *ranged* output-size estimate — never presented as exact."""

    low_bytes: int
    high_bytes: int
    savings_low: float     # percent, conservative end
    savings_high: float    # percent, optimistic end
    note: str = "Estimate only — the actual result depends on image content and settings."


@dataclass
class UploadedImage:
    """A validated image held in the session (raw bytes + light analysis)."""

    id: str
    filename: str          # sanitized display name — never the raw upload name
    data: bytes
    thumb: bytes
    info: ImageInfo
    note: str = ""

    @property
    def width(self) -> int:
        return self.info.width

    @property
    def height(self) -> int:
        return self.info.height

    @property
    def format(self) -> str:
        return self.info.format

    @property
    def mode(self) -> str:
        return self.info.mode

    @property
    def size(self) -> int:
        return self.info.size_bytes

    @property
    def has_alpha(self) -> bool:
        return self.info.has_alpha


def _content_stats(image: Image.Image) -> tuple[float, float, bool]:
    """Brightness, contrast and a photo-vs-graphic heuristic via NumPy.

    A small 64×64 sample keeps this cheap even for very large sources.
    """
    sample = np.asarray(image.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR), dtype=np.float32)
    brightness = float(sample.mean())
    contrast = float(sample.std())
    unique_colors = len(np.unique(sample.reshape(-1, 3), axis=0))
    is_photo_like = (unique_colors / 4096.0) > 0.35 and contrast > 25.0
    return brightness, contrast, is_photo_like


def get_image_info(image: Image.Image, size_bytes: int = 0) -> ImageInfo:
    """Build :class:`ImageInfo` from an already-opened Pillow image."""
    width, height = image.size
    brightness, contrast, is_photo_like = _content_stats(image)
    return ImageInfo(
        format=FORMAT_LABELS.get((image.format or "UNKNOWN").upper(), (image.format or "UNKNOWN").upper()),
        width=width,
        height=height,
        mode=image.mode,
        size_bytes=size_bytes,
        has_alpha=detect_transparency(image),
        megapixels=round(width * height / 1_000_000, 2),
        is_photo_like=is_photo_like,
        brightness=round(brightness, 1),
        contrast=round(contrast, 1),
    )


def analyze_image(data: bytes, *, filename: str = "") -> ImageInfo:
    """Decode ``data`` once and extract analysis info. Raises Pillow errors on bad input."""
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        info = get_image_info(image, size_bytes=len(data))
    logger.debug("Analyzed %s: %s %dx%d %s", filename, info.format, info.width, info.height, info.mode)
    return info


def make_thumbnail(data: bytes, max_side: int = 480) -> bytes:
    """Create a small JPEG/PNG copy used for fast UI previews.

    Keeping one thumbnail per image avoids re-decoding large originals on every
    Streamlit rerun.
    """
    try:
        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGBA")
                buffer = io.BytesIO()
                image.save(buffer, format="PNG", optimize=True)
            else:
                image = image.convert("RGB")
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=88)
            return buffer.getvalue()
    except Exception:  # noqa: BLE001 - thumbnails must never break processing
        logger.exception("Thumbnail generation failed")
        return b""


def estimate_output_size(
    data: bytes,
    *,
    target_format: str,
    quality: int,
    resize_mode: str = "original",
    resize_value: int = 100,
    maintain_aspect: bool = True,
) -> SizeEstimate:
    """Estimate the optimized size by encoding a small sample at the real settings.

    A thumbnail (max 512×512) is encoded with the exact target format/quality,
    its bytes-per-pixel rate is measured and extrapolated to the full image.
    The result is returned as a range, never a single number.
    """
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            width, height = image.size
            target = target_format.lower()
            if target == "original":
                target = (image.format or "jpeg").lower()
                if target == "mpo":
                    target = "jpeg"

            new_width, new_height = compute_resize_dimensions(
                width, height, resize_mode, resize_value, maintain_aspect=maintain_aspect
            )

            scale = min(1.0, (512 * 512 / max(width * height, 1)) ** 0.5)
            sample = (
                image.resize((max(1, round(width * scale)), max(1, round(height * scale))), Image.Resampling.LANCZOS)
                if scale < 1.0
                else image.copy()
            )
    except Exception:  # noqa: BLE001 - estimation must never break the UI
        logger.exception("Size estimation failed")
        return SizeEstimate(0, 0, 0.0, 0.0, note="Estimate unavailable for this image.")

    prepared, _ = prepare_for_format(sample, target)
    sample_bytes = encode_image(prepared, target, quality)
    bytes_per_pixel = len(sample_bytes) / max(prepared.width * prepared.height, 1)

    estimate = bytes_per_pixel * new_width * new_height
    low = max(int(estimate * 0.85), 512)
    high = max(int(estimate * 1.18), low + 1)

    original_size = len(data)
    if original_size > 0:
        savings_low = max(round((original_size - high) / original_size * 100, 1), 0.0)
        savings_high = min(round((original_size - low) / original_size * 100, 1), 99.0)
        savings_high = max(savings_high, savings_low)
    else:
        savings_low = savings_high = 0.0

    return SizeEstimate(low, high, savings_low, savings_high)
