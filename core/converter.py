"""Format conversion primitives shared by the whole engine.

This module owns the two lowest-level building blocks:

* :func:`prepare_for_format` — converts any Pillow image into a mode that the
  target format can actually encode (handling transparency correctly, e.g.
  compositing onto a white background before a JPEG save).
* :func:`encode_image` — encodes a Pillow image to bytes with sensible,
  quality-aware settings per format.
"""

from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

from PIL import Image

logger = logging.getLogger(__name__)

SUPPORTED_TARGETS = ("jpeg", "png", "webp")

#: Internal Pillow format name -> display label.
FORMAT_LABELS = {
    "JPEG": "JPEG", "MPO": "JPEG", "PNG": "PNG", "WEBP": "WebP",
    "BMP": "BMP", "TIFF": "TIFF", "GIF": "GIF", "ICO": "ICO",
}

#: Target format -> file extension used for outputs.
EXTENSIONS = {"jpeg": "jpg", "png": "png", "webp": "webp", "bmp": "bmp", "tiff": "tif"}

#: Output format -> MIME type used by download buttons.
MIME_TYPES = {
    "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp",
    "bmp": "image/bmp", "tiff": "image/tiff",
}


def detect_transparency(image: Image.Image) -> bool:
    """Return True when the image actually uses (non-fully-opaque) transparency."""
    mode = image.mode
    if mode == "P":
        return "transparency" in image.info
    if mode in ("RGBA", "LA"):
        alpha_min, _ = image.getchannel("A").getextrema()
        return alpha_min < 250
    return False


def prepare_for_format(image: Image.Image, target: str) -> tuple[Image.Image, bool]:
    """Return ``(image, background_applied)`` encodable by ``target``.

    Transparent images saved as JPEG get composited onto a white background
    instead of raising an error. CMYK sources are converted to RGB.
    """
    target = target.lower()

    if target == "jpeg":
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and detect_transparency(image)):
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.getchannel("A"))
            return background, True
        if image.mode in ("P", "CMYK"):
            return image.convert("RGB"), False
        return image, False  # RGB, L and 1 encode directly

    if target == "webp":
        if image.mode in ("RGB", "RGBA", "L", "LA"):
            return image, False
        if image.mode == "P":
            return image.convert("RGBA" if detect_transparency(image) else "RGB"), False
        if image.mode == "CMYK":
            return image.convert("RGB"), False
        return image.convert("RGB"), False

    if target == "png":
        if image.mode in ("1", "L", "LA", "P", "RGB", "RGBA"):
            return image, False
        if image.mode == "CMYK":
            return image.convert("RGB"), False
        return image.convert("RGBA" if detect_transparency(image) else "RGB"), False

    if target in ("bmp", "tiff"):
        if image.mode in ("1", "L", "P", "RGB") or (target == "tiff" and image.mode in ("RGBA", "CMYK")):
            return image, False
        return image.convert("RGB"), False

    return image, False


def encode_image(
    image: Image.Image,
    target: str,
    quality: int = 85,
    *,
    exif: bytes | None = None,
    icc_profile: bytes | None = None,
) -> bytes:
    """Encode ``image`` to bytes in ``target`` format.

    JPEG is saved optimized + progressive, WebP with an efficient encoder method
    (lossless when quality is 100) and PNG with Pillow's optimizer. Metadata is
    only written when explicitly supplied.
    """
    target = target.lower()
    params: dict = {}
    if exif and target in ("jpeg", "webp", "tiff"):
        params["exif"] = exif
    if icc_profile:
        params["icc_profile"] = icc_profile

    buffer = io.BytesIO()
    if target == "jpeg":
        params.update(quality=int(quality), optimize=True, progressive=True)
        image.save(buffer, format="JPEG", **params)
    elif target == "png":
        params.update(optimize=True)
        image.save(buffer, format="PNG", **params)
    elif target == "webp":
        if quality >= 100:
            params.update(lossless=True, method=6)
        else:
            params.update(quality=int(quality), method=4)
        image.save(buffer, format="WEBP", **params)
    elif target == "bmp":
        image.save(buffer, format="BMP")
    elif target == "tiff":
        params.update(compression="tiff_deflate")
        image.save(buffer, format="TIFF", **params)
    else:
        raise ValueError(f"Unsupported target format: {target!r}")
    return buffer.getvalue()


@dataclass
class ConversionResult:
    """Outcome of converting a single image."""

    status: str = "success"            # "success" | "failed"
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


def convert_image(data: bytes, target: str, quality: int = 90, *, filename: str = "image") -> ConversionResult:
    """Convert raw image ``data`` to ``target`` format.

    Compression settings apply only to lossy targets (JPEG/WebP); PNG/BMP/TIFF
    are re-encoded losslessly.
    """
    from core.analyzer import make_thumbnail  # local import keeps module deps acyclic
    from core.optimizer import calculate_savings
    from utils.file_utils import build_output_filename

    result = ConversionResult(
        original_filename=filename,
        original_size=len(data),
        quality=int(quality) if target.lower() in ("jpeg", "webp") else 0,
        metadata_removed=True,
    )
    started = time.perf_counter()
    try:
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            original_format = (source.format or "UNKNOWN").upper()
            result.original_format = FORMAT_LABELS.get(original_format, original_format)
            result.original_width, result.original_height = source.size
            image, background_applied = prepare_for_format(source, target)
            result.background_applied = background_applied
            output = encode_image(image, target, quality)
    except MemoryError:
        logger.exception("Conversion ran out of memory")
        return _failed(result, "The image is too large to process in memory.")
    except Image.DecompressionBombError:
        return _failed(result, "Image dimensions are too large to process safely.")
    except (OSError, ValueError, SyntaxError, KeyError) as exc:
        logger.exception("Conversion failed for %s", filename)
        return _failed(result, "Unable to convert this image. It may be corrupted or in an unsupported mode.")

    result.processing_time = time.perf_counter() - started
    result.data = output
    result.optimized_size = len(output)
    result.output_format = FORMAT_LABELS.get(target.upper(), target.upper())
    result.new_width, result.new_height = image.size
    result.saved_percent = calculate_savings(len(data), len(output))
    result.output_filename = build_output_filename(filename, EXTENSIONS[target.lower()], suffix="")
    result.thumb = make_thumbnail(output)
    if background_applied:
        result.note = "Transparent areas were filled with white."
    return result


def batch_convert(
    items: Iterable[tuple[str, bytes]],
    target: str,
    quality: int = 90,
    *,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> list[ConversionResult]:
    """Convert many images, isolating failures so one bad file never stops the batch."""
    items = list(items)
    results: list[ConversionResult] = []
    total = len(items)
    for index, (filename, data) in enumerate(items, start=1):
        if on_progress is not None:
            on_progress(index, total, filename)
        results.append(convert_image(data, target, quality, filename=filename))
    return results


def _failed(result: ConversionResult, message: str) -> ConversionResult:
    result.status = "failed"
    result.error = message
    return result
