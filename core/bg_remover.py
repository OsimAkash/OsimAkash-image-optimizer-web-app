"""Background removal and subject extraction engine.

Supports transparent cutout creation, custom solid backdrop replacement,
and smooth alpha feathering. Uses rembg if installed, with a built-in pure
Pillow + NumPy edge/color-distance keying engine as a zero-dependency fallback.
"""

from __future__ import annotations

import io
import logging
import time
from typing import Tuple, Union

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from core.analyzer import make_thumbnail
from core.converter import EXTENSIONS, FORMAT_LABELS, encode_image
from core.optimizer import OptimizationResult, calculate_savings
from utils.file_utils import build_output_filename

logger = logging.getLogger(__name__)

# Try optional AI background removal
try:
    import rembg  # type: ignore
    _HAS_REMBG = True
except ImportError:
    rembg = None
    _HAS_REMBG = False


def has_ai_remover() -> bool:
    """Return True if neural rembg backend is installed and available."""
    return _HAS_REMBG


def remove_background(
    data: bytes,
    *,
    mode: str = "transparent",  # "transparent" | "color"
    bg_color: Union[Tuple[int, int, int], str] = (255, 255, 255),
    tolerance: int = 30,
    edge_feather: int = 2,
    output_format: str = "png",
    quality: int = 90,
    filename: str = "image.png",
    image_id: str = "",
) -> OptimizationResult:
    """Extract foreground subject and remove or replace image background."""
    start_time = time.perf_counter()
    original_size = len(data)

    try:
        with Image.open(io.BytesIO(data)) as raw_img:
            img = ImageOps.exif_transpose(raw_img)
            orig_w, orig_h = img.size
            orig_fmt = (img.format or "PNG").upper()

            # Process background cutout
            cutout_img = _cutout_subject(img, tolerance=tolerance, edge_feather=edge_feather)

            # Composite onto background if requested
            if mode == "color":
                rgb_bg = _parse_color(bg_color)
                final_img = Image.new("RGBA", cutout_img.size, (*rgb_bg, 255))
                final_img.paste(cutout_img, (0, 0), cutout_img)
                # If target is JPEG, convert to RGB
                target_fmt = output_format.lower()
                if target_fmt == "jpeg" or target_fmt == "jpg":
                    final_img = final_img.convert("RGB")
                    actual_format = "jpeg"
                else:
                    actual_format = target_fmt if target_fmt in ("png", "webp") else "png"
            else:
                final_img = cutout_img
                # Transparent mode needs alpha channel (PNG or WebP)
                actual_format = "webp" if output_format.lower() == "webp" else "png"

            out_bytes = encode_image(final_img, actual_format, quality=quality)
            processing_time = round(time.perf_counter() - start_time, 4)
            optimized_size = len(out_bytes)

            out_fn = build_output_filename(
                filename,
                EXTENSIONS.get(actual_format, "png"),
                suffix="-cutout" if mode == "transparent" else "-bg",
            )

            return OptimizationResult(
                status="success",
                image_id=image_id,
                original_filename=filename,
                output_filename=out_fn,
                original_size=original_size,
                optimized_size=optimized_size,
                original_format=orig_fmt,
                output_format=FORMAT_LABELS.get(actual_format, actual_format.upper()),
                original_width=orig_w,
                original_height=orig_h,
                new_width=final_img.width,
                new_height=final_img.height,
                quality=quality,
                processing_time=processing_time,
                saved_percent=calculate_savings(original_size, optimized_size),
                data=out_bytes,
                thumb=make_thumbnail(out_bytes),
                note="AI neural matting" if _HAS_REMBG else "Color & edge-aware keying",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Background removal failed for %s", filename)
        return OptimizationResult(
            status="failed",
            image_id=image_id,
            original_filename=filename,
            original_size=original_size,
            error=str(exc) or "Failed to remove background.",
            processing_time=round(time.perf_counter() - start_time, 4),
        )


def _cutout_subject(img: Image.Image, tolerance: int, edge_feather: int) -> Image.Image:
    """Extract foreground cutout using AI rembg or smart color thresholding."""
    if _HAS_REMBG and rembg is not None:
        try:
            # AI segmentation
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            cutout_bytes = rembg.remove(buf.getvalue())
            return Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
        except Exception as exc:
            logger.warning("AI rembg failed, falling back to smart keying: %s", exc)

    # Built-in pure Pillow + NumPy smart color & edge thresholding
    return _smart_color_cutout(img, tolerance=tolerance, edge_feather=edge_feather)


def _smart_color_cutout(img: Image.Image, tolerance: int, edge_feather: int) -> Image.Image:
    """Extract cutout using border sampling and Euclidean color distance."""
    rgba = img.convert("RGBA")
    arr = np.array(rgba)
    rgb = arr[:, :, :3].astype(np.float32)

    # Sample corners and borders to identify dominant backdrop color
    h, w, _ = arr.shape
    border_samples = np.concatenate([
        arr[0, :, :3],        # top border
        arr[h - 1, :, :3],    # bottom border
        arr[:, 0, :3],        # left border
        arr[:, w - 1, :3],    # right border
    ], axis=0)

    # Median background color estimate
    bg_sample = np.median(border_samples, axis=0)

    # Compute Euclidean distance in RGB color space
    dist = np.sqrt(np.sum((rgb - bg_sample) ** 2, axis=2))

    # Compute soft alpha mask based on tolerance
    tol = float(max(tolerance, 5))
    softness = max(tol * 0.4, 4.0)

    # Alpha: 0 where close to background color, 255 where distinct foreground
    alpha = np.clip((dist - (tol - softness)) / (softness * 2.0), 0.0, 1.0) * 255.0
    alpha = alpha.astype(np.uint8)

    # Apply edge feathering using Pillow filter for smooth anti-aliased cutout
    alpha_img = Image.fromarray(alpha, mode="L")
    if edge_feather > 0:
        alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=edge_feather))

    # Preserve existing transparency if original had any
    if "A" in img.getbands():
        orig_alpha = np.array(img.getchannel("A"))
        combined_alpha = np.minimum(np.array(alpha_img), orig_alpha)
        alpha_img = Image.fromarray(combined_alpha, mode="L")

    rgba.putalpha(alpha_img)
    return rgba


def _parse_color(bg_color: Union[Tuple[int, int, int], str]) -> Tuple[int, int, int]:
    """Parse tuple or hex string into RGB 3-tuple."""
    if isinstance(bg_color, (tuple, list)) and len(bg_color) >= 3:
        return (int(bg_color[0]), int(bg_color[1]), int(bg_color[2]))
    if isinstance(bg_color, str):
        hex_str = bg_color.lstrip("#")
        if len(hex_str) == 6:
            return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
        if len(hex_str) == 3:
            return (int(hex_str[0] * 2, 16), int(hex_str[1] * 2, 16), int(hex_str[2] * 2, 16))
    return (255, 255, 255)
