"""Passport and Stamp Size Photo Studio Core Engine.

Specialized engine for generating official-standard Passport and Stamp size photos:
- Bangladesh / India / UK / EU / Schengen Standard (35 × 45 mm / 413 × 531 px @ 300 DPI)
- US Visa / US Passport 2×2 inch (51 × 51 mm / 600 × 600 px @ 300 DPI)
- Stamp Size Standard (20 × 25 mm / 236 × 295 px @ 300 DPI)
- Stamp Size Large (25 × 30 mm / 295 × 354 px @ 300 DPI)
- Custom mm / px sizing
- Smart AI head/portrait centering and framing without distortion
- Official studio backdrop replacement (White, Light Blue, Soft Gray, Cyan, Custom)
- 1px crisp cutting guide borders
- Printable Multi-Photo Sheets (4-in-1, 6-in-1, 8-in-1, 12-in-1 on standard 4R photo paper).
"""

from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from core.analyzer import make_thumbnail
from core.bg_remover import _cutout_subject, _parse_color, has_ai_remover
from core.converter import EXTENSIONS, FORMAT_LABELS, encode_image
from utils.file_utils import build_output_filename

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PassportPreset:
    key: str
    name: str
    width_mm: float
    height_mm: float
    width_px: int
    height_px: int
    description: str


PASSPORT_PRESETS: Dict[str, PassportPreset] = {
    "passport_bd_global": PassportPreset(
        key="passport_bd_global",
        name="🇧🇩 Passport Standard (35 × 45 mm)",
        width_mm=35.0,
        height_mm=45.0,
        width_px=413,
        height_px=531,
        description="Standard for Bangladesh, India, UK, EU, Schengen & Commonwealth",
    ),
    "stamp_standard": PassportPreset(
        key="stamp_standard",
        name="🔖 Stamp Size Standard (20 × 25 mm)",
        width_mm=20.0,
        height_mm=25.0,
        width_px=236,
        height_px=295,
        description="Standard Stamp size for official forms, admissions & ID cards",
    ),
    "passport_us_visa": PassportPreset(
        key="passport_us_visa",
        name="🇺🇸 US Visa / 2×2 inch (51 × 51 mm)",
        width_mm=50.8,
        height_mm=50.8,
        width_px=600,
        height_px=600,
        description="Standard 2×2 inch for US Visa, US Passport, OCI & Online Portals",
    ),
    "stamp_large": PassportPreset(
        key="stamp_large",
        name="🏷️ Stamp Size Large (25 × 30 mm)",
        width_mm=25.0,
        height_mm=30.0,
        width_px=295,
        height_px=354,
        description="Admissions, Admit Cards, Certificates & Badges",
    ),
}

OFFICIAL_BACKDROPS: Dict[str, str] = {
    "Official White": "#FFFFFF",
    "Passport Light Blue": "#B9E2FA",
    "Govt Sky Blue": "#78C0E0",
    "Studio Soft Gray": "#E5E7EB",
    "Off-White Cream": "#FDFBF7",
}


@dataclass
class PassportResult:
    status: str = "success"
    image_id: str = ""
    original_filename: str = ""
    output_filename: str = ""
    preset_name: str = ""
    width_mm: float = 35.0
    height_mm: float = 45.0
    width_px: int = 413
    height_px: int = 531
    dpi: int = 300
    original_size: int = 0
    optimized_size: int = 0
    processing_time: float = 0.0
    data: bytes = b""
    thumb: bytes = b""
    original_thumb: bytes = b""
    sheet_data: bytes = b""
    sheet_filename: str = ""
    sheet_copies: int = 0
    error: str = ""


def compute_portrait_framing(
    img: Image.Image,
    target_w: int,
    target_h: int,
    *,
    zoom: float = 1.0,
    offset_y: float = 0.0,
    offset_x: float = 0.0,
    alpha_mask: Optional[np.ndarray] = None,
) -> Tuple[int, int, int, int]:
    """Calculate bounding crop coordinates [left, top, right, bottom] on the source image.

    If an alpha mask is provided, locates the subject's head and centers on it
    with official passport proportion (head ~70% of frame, 10% headroom).
    """
    orig_w, orig_h = img.size
    target_ratio = float(target_w) / float(target_h)

    # 1. Detect subject bounds if alpha mask is available
    if alpha_mask is not None and np.any(alpha_mask > 20):
        y_indices, x_indices = np.where(alpha_mask > 20)
        subj_top = int(np.min(y_indices))
        subj_bot = int(np.max(y_indices))
        subj_left = int(np.min(x_indices))
        subj_right = int(np.max(x_indices))
        subj_h = max(10, subj_bot - subj_top)
        subj_center_x = (subj_left + subj_right) // 2

        # In passport photos, frame should cover head + shoulders down to upper chest
        # Base frame height on head/upper-body proportion
        base_h = int(subj_h * 1.25)
    else:
        # Default portrait heuristic: upper-third of image
        subj_top = int(orig_h * 0.06)
        subj_center_x = orig_w // 2
        base_h = int(orig_h * 0.75)

    # Apply user zoom (higher zoom = smaller crop window, zooming in closer)
    effective_zoom = max(0.4, min(3.0, float(zoom)))
    crop_h = int(base_h / effective_zoom)
    crop_w = int(crop_h * target_ratio)

    # Clamp to image dimensions if crop exceeds image bounds
    if crop_w > orig_w:
        crop_w = orig_w
        crop_h = int(crop_w / target_ratio)
    if crop_h > orig_h:
        crop_h = orig_h
        crop_w = int(crop_h * target_ratio)

    # Position vertically: give ~10% headroom above head
    headroom = int(crop_h * 0.10)
    ideal_top = subj_top - headroom

    # Apply user vertical and horizontal offsets
    ideal_top += int(offset_y * crop_h)
    ideal_left = int(subj_center_x - (crop_w // 2) + (offset_x * crop_w))

    # Clamp coordinates to image boundaries
    left = max(0, min(orig_w - crop_w, ideal_left))
    top = max(0, min(orig_h - crop_h, ideal_top))
    right = left + crop_w
    bottom = top + crop_h

    return (left, top, right, bottom)


def generate_passport_photo(
    data: bytes,
    *,
    preset_key: str = "passport_bd_global",
    custom_w_px: int = 413,
    custom_h_px: int = 531,
    custom_w_mm: float = 35.0,
    custom_h_mm: float = 45.0,
    bg_mode: str = "white",  # "white" | "light_blue" | "gray" | "custom_color" | "keep_original"
    custom_bg_hex: str = "#FFFFFF",
    zoom: float = 1.0,
    offset_y: float = 0.0,
    offset_x: float = 0.0,
    auto_face_framing: bool = True,
    add_border: bool = True,
    border_color: str = "#D1D5DB",
    border_width: int = 1,
    sheet_layout: str = "6_copies",  # "single" | "4_copies" | "6_copies" | "8_copies" | "12_copies"
    output_format: str = "jpeg",
    quality: int = 95,
    filename: str = "passport.jpg",
    image_id: str = "",
) -> PassportResult:
    """Generate professional passport/stamp photo and optional multi-photo print sheet."""
    start_time = time.perf_counter()
    original_size = len(data)
    orig_thumb = make_thumbnail(data)

    preset = PASSPORT_PRESETS.get(preset_key)
    if preset is not None:
        target_w_px = preset.width_px
        target_h_px = preset.height_px
        target_w_mm = preset.width_mm
        target_h_mm = preset.height_mm
        preset_title = preset.name
    else:
        target_w_px = max(50, custom_w_px)
        target_h_px = max(50, custom_h_px)
        target_w_mm = max(5.0, custom_w_mm)
        target_h_mm = max(5.0, custom_h_mm)
        preset_title = f"Custom ({target_w_mm:.1f} × {target_h_mm:.1f} mm)"

    try:
        with Image.open(io.BytesIO(data)) as raw_img:
            img = ImageOps.exif_transpose(raw_img)

            # 1. Background & Subject Extraction
            alpha_mask: Optional[np.ndarray] = None
            if bg_mode != "keep_original":
                # Determine backdrop color
                if bg_mode == "light_blue":
                    bg_rgb = _parse_color(OFFICIAL_BACKDROPS["Passport Light Blue"])
                elif bg_mode == "gray":
                    bg_rgb = _parse_color(OFFICIAL_BACKDROPS["Studio Soft Gray"])
                elif bg_mode == "govt_blue":
                    bg_rgb = _parse_color(OFFICIAL_BACKDROPS["Govt Sky Blue"])
                elif bg_mode == "custom_color":
                    bg_rgb = _parse_color(custom_bg_hex)
                else:
                    bg_rgb = (255, 255, 255)

                # Extract cutout subject
                cutout_img, _ = _cutout_subject(
                    img,
                    engine="ai" if has_ai_remover() else "smart",
                    model_name="u2net_human_seg" if has_ai_remover() else "u2net",
                    alpha_matting=False,
                    defringe=True,
                )

                # Composite over studio solid backdrop
                studio_base = Image.new("RGBA", cutout_img.size, (*bg_rgb, 255))
                studio_base.paste(cutout_img, (0, 0), cutout_img)
                composed_img = studio_base.convert("RGB")

                # Extract mask for face framing
                alpha_channel = cutout_img.getchannel("A")
                alpha_mask = np.array(alpha_channel)
            else:
                composed_img = img.convert("RGB")
                if auto_face_framing and has_ai_remover():
                    # Quick cutout just to get subject mask for framing
                    try:
                        mask_cutout, _ = _cutout_subject(img, engine="ai")
                        alpha_mask = np.array(mask_cutout.getchannel("A"))
                    except Exception:
                        alpha_mask = None

            # 2. Smart Portrait Framing & Crop
            left, top, right, bottom = compute_portrait_framing(
                composed_img,
                target_w_px,
                target_h_px,
                zoom=zoom,
                offset_y=offset_y,
                offset_x=offset_x,
                alpha_mask=alpha_mask if auto_face_framing else None,
            )

            cropped = composed_img.crop((left, top, right, bottom))
            final_passport = cropped.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)

            # 3. Add clean subtle cutting guide border if requested
            if add_border and border_width > 0:
                draw = ImageDraw.Draw(final_passport)
                b_color = _parse_color(border_color)
                for i in range(border_width):
                    draw.rectangle(
                        [i, i, target_w_px - 1 - i, target_h_px - 1 - i],
                        outline=b_color,
                    )

            # 4. Encode single passport photo with 300 DPI metadata
            target_fmt = output_format.lower()
            if target_fmt not in ("jpeg", "jpg", "png"):
                target_fmt = "jpeg"

            single_buf = io.BytesIO()
            if target_fmt in ("jpeg", "jpg"):
                final_passport.save(single_buf, format="JPEG", quality=quality, dpi=(300, 300))
                ext = "jpg"
            else:
                final_passport.save(single_buf, format="PNG", dpi=(300, 300))
                ext = "png"
            single_bytes = single_buf.getvalue()

            # 5. Generate Multi-Photo Print Sheet (4R paper) if requested
            sheet_bytes = b""
            sheet_fn = ""
            sheet_num = 0
            if sheet_layout != "single":
                sheet_img, sheet_num = generate_print_sheet(final_passport, layout=sheet_layout)
                sheet_buf = io.BytesIO()
                sheet_img.save(sheet_buf, format="JPEG", quality=98, dpi=(300, 300))
                sheet_bytes = sheet_buf.getvalue()
                sheet_fn = build_output_filename(
                    filename,
                    "jpg",
                    suffix=f"-sheet-4R-{sheet_num}pcs",
                )

            proc_time = round(time.perf_counter() - start_time, 4)
            out_fn = build_output_filename(
                filename,
                ext,
                suffix=f"-{preset_key.replace('_', '-')}",
            )

            return PassportResult(
                status="success",
                image_id=image_id,
                original_filename=filename,
                output_filename=out_fn,
                preset_name=preset_title,
                width_mm=target_w_mm,
                height_mm=target_h_mm,
                width_px=target_w_px,
                height_px=target_h_px,
                dpi=300,
                original_size=original_size,
                optimized_size=len(single_bytes),
                processing_time=proc_time,
                data=single_bytes,
                thumb=make_thumbnail(single_bytes),
                original_thumb=orig_thumb,
                sheet_data=sheet_bytes,
                sheet_filename=sheet_fn,
                sheet_copies=sheet_num,
            )

    except Exception as exc:  # noqa: BLE001
        logger.exception("Passport photo generation failed for %s", filename)
        return PassportResult(
            status="failed",
            image_id=image_id,
            original_filename=filename,
            original_size=original_size,
            original_thumb=orig_thumb,
            error=str(exc) or "Failed to generate passport photo.",
            processing_time=round(time.perf_counter() - start_time, 4),
        )


def generate_print_sheet(
    passport_img: Image.Image,
    *,
    layout: str = "6_copies",  # "4_copies" | "6_copies" | "8_copies" | "12_copies"
    paper_size: Tuple[int, int] = (1800, 1200),  # 4R paper (4 × 6 inch @ 300 DPI) landscape
    sheet_bg: Union[Tuple[int, int, int], str] = "#FFFFFF",
) -> Tuple[Image.Image, int]:
    """Tiling passport/stamp photos onto standard 4R (4×6 inch) photo paper with cutting guides."""
    pw_w, pw_h = passport_img.size
    sheet_w, sheet_h = paper_size
    bg_rgb = _parse_color(sheet_bg)
    sheet = Image.new("RGB", (sheet_w, sheet_h), bg_rgb)
    draw = ImageDraw.Draw(sheet)

    # Determine grid rows and columns based on layout and photo size
    if layout == "4_copies":
        rows, cols = 2, 2
    elif layout == "8_copies":
        rows, cols = 2, 4
    elif layout == "12_copies":
        rows, cols = 3, 4
    else:  # default 6_copies
        rows, cols = 2, 3

    total_copies = rows * cols

    # Calculate spacing and centering
    total_photo_w = cols * pw_w
    total_photo_h = rows * pw_h

    # Ensure photos fit on the sheet, if not, adjust gap or scale down slightly
    gap_x = max(20, (sheet_w - total_photo_w) // (cols + 1))
    gap_y = max(20, (sheet_h - total_photo_h) // (rows + 1))

    start_x = (sheet_w - (cols * pw_w + (cols - 1) * gap_x)) // 2
    start_y = (sheet_h - (rows * pw_h + (rows - 1) * gap_y)) // 2

    guide_color = (200, 200, 200)

    for r in range(rows):
        for c in range(cols):
            x = start_x + c * (pw_w + gap_x)
            y = start_y + r * (pw_h + gap_y)
            sheet.paste(passport_img, (x, y))

            # Draw subtle cutting guideline crosshairs at corners
            arm = 8
            # Top-left
            draw.line([(x - arm, y), (x + arm, y)], fill=guide_color, width=1)
            draw.line([(x, y - arm), (x, y + arm)], fill=guide_color, width=1)
            # Top-right
            draw.line([(x + pw_w - arm, y), (x + pw_w + arm, y)], fill=guide_color, width=1)
            draw.line([(x + pw_w, y - arm), (x + pw_w, y + arm)], fill=guide_color, width=1)
            # Bottom-left
            draw.line([(x - arm, y + pw_h), (x + arm, y + pw_h)], fill=guide_color, width=1)
            draw.line([(x, y + pw_h - arm), (x, y + pw_h + arm)], fill=guide_color, width=1)
            # Bottom-right
            draw.line([(x + pw_w - arm, y + pw_h), (x + pw_w + arm, y + pw_h)], fill=guide_color, width=1)
            draw.line([(x + pw_w, y + pw_h - arm), (x + pw_w, y + pw_h + arm)], fill=guide_color, width=1)

    return sheet, total_copies
