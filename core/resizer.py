"""High-quality resizing (LANCZOS) used by the optimizer and the dedicated Resizer tool."""

from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass

from PIL import Image, ImageOps

from core.converter import EXTENSIONS, FORMAT_LABELS, encode_image, prepare_for_format

logger = logging.getLogger(__name__)

RESIZE_MODES = ("original", "width", "height", "percent")

#: Quick width presets offered on the Resizer page.
PRESET_WIDTHS = (1920, 1600, 1280, 1080, 720, 500)


def compute_resize_dimensions(
    width: int,
    height: int,
    mode: str,
    value: int,
    *,
    maintain_aspect: bool = True,
) -> tuple[int, int]:
    """Compute target dimensions for a resize request.

    * ``width``   — set the width; height follows proportionally (or stays
      unchanged when ``maintain_aspect`` is False).
    * ``height``  — set the height; width follows proportionally (or stays).
    * ``percent`` — uniform scale by ``value`` percent.

    Results are always at least 1×1 pixel.
    """
    width, height = max(1, int(width)), max(1, int(height))
    value = max(1, int(value))
    mode = mode.lower()

    if mode == "width":
        new_width = value
        new_height = round(height * value / width) if maintain_aspect else height
    elif mode == "height":
        new_height = value
        new_width = round(width * value / height) if maintain_aspect else width
    elif mode == "percent":
        factor = value / 100
        new_width, new_height = round(width * factor), round(height * factor)
    else:  # "original" or unknown
        return width, height

    return max(1, new_width), max(1, new_height)


def resize_image(image: Image.Image, new_width: int, new_height: int) -> Image.Image:
    """Resize a Pillow image with high-quality LANCZOS resampling."""
    return image.resize((max(1, new_width), max(1, new_height)), Image.Resampling.LANCZOS)


@dataclass
class ResizeResult:
    """Outcome of resizing a single image."""

    status: str = "success"
    image_id: str = ""
    original_filename: str = ""
    output_filename: str = ""
    original_size: int = 0
    optimized_size: int = 0
    original_format: str = ""
    output_format: str = ""
    original_width: int = 0
    original_height: int = 0
    new_width: int = 0
    new_height: int = 0
    quality: int = 0
    processing_time: float = 0.0
    saved_percent: float = 0.0
    data: bytes = b""
    thumb: bytes = b""
    error: str = ""
    note: str = ""
    metadata_removed: bool = True
    background_applied: bool = False


def resize_data(
    data: bytes,
    mode: str,
    value: int,
    *,
    maintain_aspect: bool = True,
    output_format: str = "original",
    quality: int = 90,
    filename: str = "image",
    max_pixels: int = 60_000_000,
) -> ResizeResult:
    """Resize raw image bytes and re-encode in the requested output format."""
    from core.analyzer import make_thumbnail  # local import keeps module deps acyclic
    from core.optimizer import calculate_savings, resolve_target_format
    from utils.file_utils import build_output_filename

    result = ResizeResult(
        original_filename=filename,
        original_size=len(data),
        quality=int(quality) if output_format.lower() in ("jpeg", "webp", "original") else 0,
        metadata_removed=True,
    )
    started = time.perf_counter()
    try:
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            original_format = (source.format or "UNKNOWN").upper()
            result.original_format = FORMAT_LABELS.get(original_format, original_format)
            result.original_width, result.original_height = source.size
            oriented = ImageOps.exif_transpose(source)

            new_width, new_height = compute_resize_dimensions(
                oriented.width, oriented.height, mode, value, maintain_aspect=maintain_aspect
            )
            if new_width * new_height > max_pixels:
                return _failed(result, "Requested dimensions are too large to process safely.")

            target = resolve_target_format(original_format, output_format)
            if (new_width, new_height) == oriented.size and target == original_format.lower():
                result.data = data
                result.new_width, result.new_height = oriented.size
                result.output_format = result.original_format
                result.note = "Already at the requested size — original file kept."
                result.thumb = make_thumbnail(data)
                return result

            image = (
                resize_image(oriented, new_width, new_height)
                if (new_width, new_height) != oriented.size
                else oriented
            )
            image, background_applied = prepare_for_format(image, target)
            effective_quality = quality if target in ("jpeg", "webp") else 90
            output = encode_image(image, target, effective_quality)
    except MemoryError:
        logger.exception("Resize ran out of memory")
        return _failed(result, "The image is too large to process in memory.")
    except Image.DecompressionBombError:
        return _failed(result, "Image dimensions are too large to process safely.")
    except (OSError, ValueError, SyntaxError, KeyError):
        logger.exception("Resize failed for %s", filename)
        return _failed(result, "Unable to resize this image. It may be corrupted or in an unsupported mode.")

    result.processing_time = time.perf_counter() - started
    result.data = output
    result.optimized_size = len(output)
    result.output_format = FORMAT_LABELS.get(target.upper(), target.upper())
    result.new_width, result.new_height = image.size
    result.saved_percent = calculate_savings(len(data), len(output))
    result.output_filename = build_output_filename(filename, EXTENSIONS[target], suffix="-resized")
    result.thumb = make_thumbnail(output)
    result.background_applied = background_applied
    if background_applied:
        result.note = "Transparent areas were filled with white."
    return result


def _failed(result: ResizeResult, message: str) -> ResizeResult:
    result.status = "failed"
    result.error = message
    return result
