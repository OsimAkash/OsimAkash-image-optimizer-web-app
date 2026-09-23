"""Image color enhancement, aesthetic grading, and fresh filters engine.

Provides one-click aesthetic presets (Fresh & Clean, Vivid Pop, Warm Glow, Cool Breeze,
Studio Pro, B&W Noir, Vintage Film) alongside fine-grained Brightness, Contrast,
Saturation/Color Balance, and Sharpness controls.
"""

from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass

from PIL import Image, ImageEnhance, ImageOps

from core.analyzer import make_thumbnail
from core.converter import EXTENSIONS, FORMAT_LABELS, encode_image, prepare_for_format
from core.optimizer import OptimizationResult, calculate_savings, resolve_target_format
from utils.file_utils import build_output_filename

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ColorPreset:
    """Named preset bundle for rapid visual styling."""

    name: str
    icon: str
    description: str
    brightness: float
    contrast: float
    saturation: float
    sharpness: float
    auto_contrast: bool = False
    tint: str = "none"  # "none" | "warm" | "cool" | "vintage"


COLOR_PRESETS: dict[str, ColorPreset] = {
    "Normal": ColorPreset(
        name="Normal",
        icon="🔘",
        description="Original unmodified color values.",
        brightness=1.0,
        contrast=1.0,
        saturation=1.0,
        sharpness=1.0,
    ),
    "Fresh & Clean": ColorPreset(
        name="Fresh & Clean",
        icon="✨",
        description="Luminous brightness, crisp clarity, and fresh natural tones.",
        brightness=1.08,
        contrast=1.15,
        saturation=1.22,
        sharpness=1.28,
        auto_contrast=True,
    ),
    "Vivid Pop": ColorPreset(
        name="Vivid Pop",
        icon="🔥",
        description="Deep punchy contrast, saturated colors and razor-sharp edges.",
        brightness=1.04,
        contrast=1.25,
        saturation=1.42,
        sharpness=1.35,
    ),
    "Warm Glow": ColorPreset(
        name="Warm Glow",
        icon="☀️",
        description="Golden hour warmth, gentle contrast, and sunset ambiance.",
        brightness=1.05,
        contrast=1.12,
        saturation=1.18,
        sharpness=1.12,
        tint="warm",
    ),
    "Cool Breeze": ColorPreset(
        name="Cool Breeze",
        icon="❄️",
        description="Modern icy blue tones, crisp high-definition contrast.",
        brightness=1.03,
        contrast=1.14,
        saturation=1.16,
        sharpness=1.22,
        tint="cool",
    ),
    "Studio Pro": ColorPreset(
        name="Studio Pro",
        icon="📸",
        description="Balanced commercial grade lighting with unsharp mask detail.",
        brightness=1.06,
        contrast=1.22,
        saturation=1.08,
        sharpness=1.45,
    ),
    "B&W Noir": ColorPreset(
        name="B&W Noir",
        icon="⚫",
        description="Dramatic monochrome with deep shadows and striking highlights.",
        brightness=1.02,
        contrast=1.45,
        saturation=0.0,
        sharpness=1.30,
    ),
    "Vintage Film": ColorPreset(
        name="Vintage Film",
        icon="🎞️",
        description="Analog film aesthetic with muted saturation and softened contrast.",
        brightness=0.98,
        contrast=0.96,
        saturation=0.88,
        sharpness=1.08,
        tint="vintage",
    ),
}


def enhance_image(
    data: bytes,
    *,
    brightness: float = 1.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    sharpness: float = 1.0,
    auto_contrast: bool = False,
    tint: str = "none",
    output_format: str = "original",
    quality: int = 90,
    filename: str = "image.png",
    image_id: str = "",
) -> OptimizationResult:
    """Apply color transformations, enhancements, and aesthetic grading."""
    start_time = time.perf_counter()
    original_size = len(data)

    try:
        with Image.open(io.BytesIO(data)) as raw_img:
            img = ImageOps.exif_transpose(raw_img)
            orig_w, orig_h = img.size
            orig_fmt = (img.format or "JPEG").upper()

            # Preserve alpha channel separately if present
            has_alpha = "A" in img.getbands()
            alpha_channel = img.getchannel("A") if has_alpha else None

            # Work in RGB mode for color grading
            rgb_img = img.convert("RGB")

            # 1. Auto-contrast / Auto-levels if enabled
            if auto_contrast:
                rgb_img = ImageOps.autocontrast(rgb_img, cutoff=1)

            # 2. Brightness enhancement
            if brightness != 1.0:
                enhancer = ImageEnhance.Brightness(rgb_img)
                rgb_img = enhancer.enhance(float(brightness))

            # 3. Contrast enhancement
            if contrast != 1.0:
                enhancer = ImageEnhance.Contrast(rgb_img)
                rgb_img = enhancer.enhance(float(contrast))

            # 4. Color / Saturation enhancement
            if saturation != 1.0:
                enhancer = ImageEnhance.Color(rgb_img)
                rgb_img = enhancer.enhance(float(saturation))

            # 5. Sharpness enhancement
            if sharpness != 1.0:
                enhancer = ImageEnhance.Sharpness(rgb_img)
                rgb_img = enhancer.enhance(float(sharpness))

            # 6. Apply subtle color tints if selected
            if tint != "none":
                rgb_img = _apply_tint(rgb_img, tint)

            # Re-attach alpha channel if original had transparency
            if has_alpha and alpha_channel is not None:
                final_img = rgb_img.convert("RGBA")
                final_img.putalpha(alpha_channel)
            else:
                final_img = rgb_img

            # Determine target format and encode
            target_fmt = resolve_target_format(orig_fmt, output_format)
            prep_img, _ = prepare_for_format(final_img, target_fmt)
            out_bytes = encode_image(prep_img, target_fmt, quality=quality)

            processing_time = round(time.perf_counter() - start_time, 4)
            optimized_size = len(out_bytes)

            out_fn = build_output_filename(
                filename,
                EXTENSIONS.get(target_fmt, "jpg"),
                suffix="-fresh",
            )

            return OptimizationResult(
                status="success",
                image_id=image_id,
                original_filename=filename,
                output_filename=out_fn,
                original_size=original_size,
                optimized_size=optimized_size,
                original_format=orig_fmt,
                output_format=FORMAT_LABELS.get(target_fmt, target_fmt.upper()),
                original_width=orig_w,
                original_height=orig_h,
                new_width=final_img.width,
                new_height=final_img.height,
                quality=quality,
                processing_time=processing_time,
                saved_percent=calculate_savings(original_size, optimized_size),
                data=out_bytes,
                thumb=make_thumbnail(out_bytes),
                note="Fresh color enhancement applied",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Enhancement failed for %s", filename)
        return OptimizationResult(
            status="failed",
            image_id=image_id,
            original_filename=filename,
            original_size=original_size,
            error=str(exc) or "Failed to enhance image.",
            processing_time=round(time.perf_counter() - start_time, 4),
        )


def _apply_tint(img: Image.Image, tint_type: str) -> Image.Image:
    """Apply subtle color balance curve / tint to RGB image."""
    r, g, b = img.split()
    if tint_type == "warm":
        # Warm: boost red slightly, soft decrease in blue
        r = r.point(lambda i: min(255, int(i * 1.05 + 4)))
        b = b.point(lambda i: max(0, int(i * 0.94)))
    elif tint_type == "cool":
        # Cool: boost blue/cyan slightly
        b = b.point(lambda i: min(255, int(i * 1.08 + 5)))
        r = r.point(lambda i: max(0, int(i * 0.95)))
    elif tint_type == "vintage":
        # Vintage: amber highlights and faded shadows
        r = r.point(lambda i: min(255, int(i * 1.04 + 10)))
        g = g.point(lambda i: min(255, int(i * 1.02 + 5)))
        b = b.point(lambda i: max(12, int(i * 0.90 + 10)))
    return Image.merge("RGB", (r, g, b))
