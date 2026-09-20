"""The OptiPic optimization engine.

One entry point — :func:`optimize_image` — runs the full pipeline:

1. decode + honor EXIF orientation,
2. resolve the effective quality from the compression mode,
3. resize (LANCZOS) when requested,
4. prepare color modes for the target format (transparency-safe),
5. encode with format-specific settings, stripping or preserving metadata,
6. fall back to the original file when re-encoding gains nothing,
7. return real measured numbers (sizes, savings, timing).
"""

from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass, field

from PIL import Image, ImageOps

from core.analyzer import ImageInfo, make_thumbnail
from core.converter import EXTENSIONS, FORMAT_LABELS, encode_image, prepare_for_format
from core.resizer import compute_resize_dimensions, resize_image
from utils.file_utils import build_output_filename

logger = logging.getLogger(__name__)

# Safety net against decompression-bomb style inputs (Pillow raises past this).
Image.MAX_IMAGE_PIXELS = 80_000_000

#: Compression mode (label shown in the UI) -> fixed quality. "Custom" uses the slider.
MODE_QUALITY = {
    "Maximum Compression": 60,
    "Balanced": 80,
    "High Quality": 92,
}

COMPRESSION_MODE_LABELS = tuple(MODE_QUALITY) + ("Custom",)


@dataclass(frozen=True)
class Preset:
    """A named bundle of settings applied from the preset bar."""

    label: str
    quality: int
    output_format: str   # "original" | "jpeg" | "png" | "webp"
    mode: str


#: Ordered presets shown in the UI (spec: section 10).
PRESETS: dict[str, Preset] = {
    "Maximum Compression": Preset("Maximum Compression", 60, "webp", "Maximum Compression"),
    "Website": Preset("Website", 80, "webp", "Balanced"),
    "E-commerce": Preset("E-commerce", 82, "jpeg", "Balanced"),
    "Social Media": Preset("Social Media", 85, "jpeg", "Balanced"),
    "High Quality": Preset("High Quality", 92, "original", "High Quality"),
}


@dataclass
class OptimizationSettings:
    """Everything the engine needs to process one image."""

    mode: str = "Balanced"            # one of COMPRESSION_MODE_LABELS
    quality: int = 80                 # used when mode == "Custom" (10–100)
    output_format: str = "original"   # "original" | "jpeg" | "png" | "webp"
    resize_mode: str = "original"     # "original" | "width" | "height" | "percent"
    resize_value: int = 100           # px for width/height, % for percent
    maintain_aspect: bool = True
    remove_metadata: bool = True

    @property
    def effective_quality(self) -> int:
        """Quality actually used: fixed per mode, or the slider value in Custom mode."""
        return MODE_QUALITY.get(self.mode, self.quality)


@dataclass
class OptimizationResult:
    """Outcome of processing a single image — all numbers are real measurements."""

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
    metadata_removed: bool = False
    background_applied: bool = False
    settings_used: OptimizationSettings = field(default_factory=OptimizationSettings)


def calculate_savings(original_size: int, optimized_size: int) -> float:
    """Percent of space saved (negative when the output is larger)."""
    if original_size <= 0:
        return 0.0
    return round((1 - optimized_size / original_size) * 100, 2)


def resolve_target_format(original_format: str, requested: str) -> str:
    """Map the user's requested output format to a concrete target."""
    requested = (requested or "original").lower()
    if requested != "original":
        return requested
    original = (original_format or "JPEG").upper()
    return "jpeg" if original == "MPO" else original.lower()


def remove_metadata(data: bytes, *, quality: int = 95) -> bytes:
    """Re-encode an image without EXIF/ICC data, keeping visual content intact."""
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        target = "jpeg" if (image.format or "").upper() in ("JPEG", "MPO") else (image.format or "png").lower()
        clean, _ = prepare_for_format(image, target)
        return encode_image(clean, target, quality)


def compress_image(image: Image.Image, quality: int = 85, output_format: str = "jpeg") -> bytes:
    """Encode a Pillow image directly — the low-level building block."""
    prepared, _ = prepare_for_format(image, output_format)
    return encode_image(prepared, output_format, quality)


def recommend_settings(info: ImageInfo) -> tuple[OptimizationSettings, str]:
    """Smart Optimize: choose settings from format, size, dimensions and content.

    Returns ``(settings, human-readable reason)``.
    """
    fmt = info.format
    size = info.size_bytes

    if info.has_alpha:
        if fmt == "PNG" and size > 512 * 1024:
            return (
                OptimizationSettings(mode="Custom", quality=85, output_format="webp"),
                "Transparent PNG — WebP keeps the alpha channel and compresses much better.",
            )
        return (
            OptimizationSettings(mode="Custom", quality=88, output_format="original"),
            "Transparency detected — format kept so the alpha channel is preserved.",
        )

    if info.megapixels > 12:
        return (
            OptimizationSettings(
                mode="Custom", quality=82, output_format="webp",
                resize_mode="width", resize_value=2560,
            ),
            "Very large image — resized to 2560 px wide before compression.",
        )

    if fmt in ("BMP", "TIFF"):
        return (
            OptimizationSettings(mode="Custom", quality=85, output_format="webp"),
            "Unoptimized bitmap format — converting to WebP saves the most space.",
        )

    if fmt in ("JPEG", "MPO") and size > 1024 * 1024:
        return (
            OptimizationSettings(mode="Custom", quality=82, output_format="webp"),
            "Large JPEG — WebP at 82% quality gives the best size/quality trade-off.",
        )

    if size < 150 * 1024:
        return (
            OptimizationSettings(mode="Custom", quality=90, output_format="original"),
            "Small image — light compression only to protect quality.",
        )

    if not info.is_photo_like:
        return (
            OptimizationSettings(mode="Custom", quality=85, output_format="original"),
            "Graphic-style image — gentle settings preserve flat colors and text.",
        )

    return (
        OptimizationSettings(mode="Custom", quality=80, output_format="original"),
        "Standard photo — balanced compression.",
    )


def optimize_image(
    data: bytes,
    settings: OptimizationSettings,
    *,
    filename: str = "image",
    image_id: str = "",
    max_pixels: int = 80_000_000,
) -> OptimizationResult:
    """Run the full optimization pipeline on raw image bytes.

    Never raises — any processing failure is returned as a failed
    :class:`OptimizationResult` with a user-friendly message; technical details
    go to the log.
    """
    result = OptimizationResult(
        image_id=image_id,
        original_filename=filename,
        original_size=len(data),
        metadata_removed=settings.remove_metadata,
        settings_used=settings,
    )
    started = time.perf_counter()
    try:
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            original_format = (source.format or "UNKNOWN").upper()
            result.original_format = FORMAT_LABELS.get(original_format, original_format)
            result.original_width, result.original_height = source.size
            exif = source.info.get("exif")
            icc_profile = source.info.get("icc_profile")
            image = ImageOps.exif_transpose(source)  # honor orientation tags

        target = resolve_target_format(original_format, settings.output_format)
        quality = settings.effective_quality

        new_width, new_height = image.size
        if settings.resize_mode != "original":
            new_width, new_height = compute_resize_dimensions(
                image.width, image.height, settings.resize_mode, settings.resize_value,
                maintain_aspect=settings.maintain_aspect,
            )
            if new_width * new_height > max_pixels:
                return _failed(result, "Requested dimensions are too large to process safely.")
            if (new_width, new_height) != image.size:
                image = resize_image(image, new_width, new_height)

        image, background_applied = prepare_for_format(image, target)

        # Detach Pillow's info dict so incidental chunks (PNG text, etc.) don't leak.
        image.info = {}
        output = encode_image(
            image, target, quality,
            exif=None if settings.remove_metadata else exif,
            icc_profile=None if settings.remove_metadata else icc_profile,
        )

        resized = (new_width, new_height) != (result.original_width, result.original_height)
        if (
            target == original_format.lower()
            and not resized
            and len(output) >= len(data)
        ):
            if settings.remove_metadata:
                result.note = "Metadata removed; the re-encoded file was not smaller, so it is used anyway."
            else:
                output = data
                result.metadata_removed = False
                result.note = "Already well optimized — original file kept."

        result.status = "success"
        result.data = output
        result.optimized_size = len(output)
        result.output_format = FORMAT_LABELS.get(target.upper(), target.upper())
        result.new_width, result.new_height = image.size
        result.quality = quality
        result.saved_percent = calculate_savings(len(data), len(output))
        result.processing_time = time.perf_counter() - started
        result.thumb = make_thumbnail(output)
        result.background_applied = background_applied
        result.output_filename = build_output_filename(filename, EXTENSIONS[target])
        if background_applied:
            result.note = (result.note + " " if result.note else "") + "Transparent areas were filled with white."
        return result

    except MemoryError:
        logger.exception("Optimization ran out of memory for %s", filename)
        return _failed(result, "The image is too large to process in memory. Try a smaller resize.")
    except Image.DecompressionBombError:
        return _failed(result, "Image dimensions are too large to process safely.")
    except (OSError, ValueError, SyntaxError, KeyError) as exc:
        logger.exception("Optimization failed for %s", filename)
        return _failed(result, "Unable to process this image. It may be corrupted or in an unsupported color mode.")
    except Exception:  # noqa: BLE001 - the UI must never see a traceback
        logger.exception("Unexpected error while optimizing %s", filename)
        return _failed(result, "Unexpected error while processing this image.")


def batch_optimize(
    items: list[tuple[str, bytes, OptimizationSettings]],
    *,
    on_progress=None,
) -> list[OptimizationResult]:
    """Optimize many images, isolating failures so one bad file never stops the batch."""
    results: list[OptimizationResult] = []
    total = len(items)
    for index, (filename, data, settings) in enumerate(items, start=1):
        if on_progress is not None:
            on_progress(index, total, filename)
        results.append(optimize_image(data, settings, filename=filename))
    return results


def _failed(result: OptimizationResult, message: str) -> OptimizationResult:
    result.status = "failed"
    result.error = message
    result.processing_time = 0.0
    return result
