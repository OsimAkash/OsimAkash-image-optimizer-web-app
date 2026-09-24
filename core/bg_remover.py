"""Professional Background Removal and Subject Extraction Engine.

Features:
- AI Neural Matting powered by rembg (U2Net, U2Net-Human-Seg, ISNet, Silueta, Anime)
  with fine-grain alpha matting for hair/fur and mask post-processing.
- Intelligent Pure-Python + NumPy multi-pass perceptual color and chroma keying fallback.
- Multiple output modes: Transparent Cutout, Solid Studio Backdrop, DSLR Portrait Bokeh Blur,
  Custom Image Backdrop, and Black/White Alpha Mask.
- Color despilling / defringing to remove background reflection halos around edges.
"""

from __future__ import annotations

import io
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

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

_REMBG_SESSIONS: Dict[str, Any] = {}

AI_MODELS: Dict[str, str] = {
    "u2net": "U2Net (General / High Quality)",
    "u2net_human_seg": "U2Net Human (Portraits & People)",
    "isnet-general-use": "ISNet (Ultra Precision & Fine Edges)",
    "u2netp": "U2Netp (Fast Lightweight)",
    "silueta": "Silueta (Compact 43MB)",
    "isnet-anime": "ISNet Anime (Anime & Artwork)",
}

STUDIO_PALETTES: Dict[str, str] = {
    "Studio White": "#FFFFFF",
    "Soft Gray": "#F3F4F6",
    "E-Commerce Cream": "#FDFBF7",
    "Warm Sand": "#F5EFEB",
    "Slate Charcoal": "#1E293B",
    "Midnight Blue": "#0F172A",
    "Chroma Green": "#00FF00",
    "Chroma Blue": "#0000FF",
    "Pastel Purple": "#EDE9FE",
    "Rose Pink": "#FFE4E6",
}


def has_ai_remover() -> bool:
    """Return True if neural rembg backend is installed and available."""
    return _HAS_REMBG


def get_rembg_session(model_name: str = "u2net") -> Any:
    """Get or create a cached rembg model session."""
    if not _HAS_REMBG or rembg is None:
        return None
    if model_name not in _REMBG_SESSIONS:
        try:
            logger.info("Initializing rembg neural session: %s", model_name)
            _REMBG_SESSIONS[model_name] = rembg.new_session(model_name)
        except Exception as exc:
            logger.warning("Could not create rembg session for '%s': %s", model_name, exc)
            _REMBG_SESSIONS[model_name] = None
    return _REMBG_SESSIONS.get(model_name)


def remove_background(
    data: bytes,
    *,
    mode: str = "transparent",  # "transparent" | "color" | "blur" | "custom_image" | "mask"
    bg_color: Union[Tuple[int, int, int], str] = (255, 255, 255),
    blur_radius: int = 25,
    bg_image_data: bytes = b"",
    engine: str = "auto",  # "auto" | "ai" | "smart" | "chroma"
    model_name: str = "u2net",
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
    post_process_mask: bool = True,
    tolerance: int = 35,
    edge_feather: int = 2,
    defringe: bool = True,
    output_format: str = "png",
    quality: int = 90,
    filename: str = "image.png",
    image_id: str = "",
) -> OptimizationResult:
    """Extract foreground subject and remove or replace image background."""
    start_time = time.perf_counter()
    original_size = len(data)
    orig_thumb = make_thumbnail(data)

    try:
        with Image.open(io.BytesIO(data)) as raw_img:
            img = ImageOps.exif_transpose(raw_img)
            orig_w, orig_h = img.size
            orig_fmt = (img.format or "PNG").upper()

            # 1. Extract Cutout Subject RGBA
            cutout_img, used_engine_label = _cutout_subject(
                img,
                engine=engine,
                model_name=model_name,
                alpha_matting=alpha_matting,
                alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
                alpha_matting_background_threshold=alpha_matting_background_threshold,
                alpha_matting_erode_size=alpha_matting_erode_size,
                post_process_mask=post_process_mask,
                tolerance=tolerance,
                edge_feather=edge_feather,
                defringe=defringe,
            )

            # 2. Render into requested mode
            target_fmt = output_format.lower()
            if mode == "color":
                rgb_bg = _parse_color(bg_color)
                final_img = Image.new("RGBA", cutout_img.size, (*rgb_bg, 255))
                final_img.paste(cutout_img, (0, 0), cutout_img)
                if target_fmt in ("jpeg", "jpg"):
                    final_img = final_img.convert("RGB")
                    actual_format = "jpeg"
                else:
                    actual_format = target_fmt if target_fmt in ("png", "webp") else "png"
                suffix = "-color-bg"

            elif mode == "blur":
                # Portrait Bokeh Mode: blur original and composite sharp subject on top
                blurred_base = img.convert("RGBA").filter(ImageFilter.GaussianBlur(radius=max(1, blur_radius)))
                blurred_base.paste(cutout_img, (0, 0), cutout_img)
                if target_fmt in ("jpeg", "jpg"):
                    final_img = blurred_base.convert("RGB")
                    actual_format = "jpeg"
                else:
                    final_img = blurred_base
                    actual_format = target_fmt if target_fmt in ("png", "webp") else "png"
                suffix = "-bokeh-blur"

            elif mode == "custom_image" and bg_image_data:
                # Custom Image Backdrop Mode
                with Image.open(io.BytesIO(bg_image_data)) as bg_raw:
                    bg_img = ImageOps.exif_transpose(bg_raw).convert("RGBA")
                    # Fit/crop background to match cutout dimensions
                    bg_fit = ImageOps.fit(bg_img, cutout_img.size, method=Image.Resampling.LANCZOS)
                    bg_fit.paste(cutout_img, (0, 0), cutout_img)
                    if target_fmt in ("jpeg", "jpg"):
                        final_img = bg_fit.convert("RGB")
                        actual_format = "jpeg"
                    else:
                        final_img = bg_fit
                        actual_format = target_fmt if target_fmt in ("png", "webp") else "png"
                suffix = "-custom-bg"

            elif mode == "mask":
                # Export Alpha Mask (White subject on Black background)
                alpha_channel = cutout_img.getchannel("A")
                final_img = alpha_channel.convert("RGB") if target_fmt in ("jpeg", "jpg") else alpha_channel
                actual_format = target_fmt if target_fmt in ("png", "jpeg", "webp") else "png"
                suffix = "-alpha-mask"

            else:
                # Default Transparent Cutout Mode
                final_img = cutout_img
                # Transparent mode requires PNG or WebP with alpha
                actual_format = "webp" if target_fmt == "webp" else "png"
                suffix = "-cutout"

            out_bytes = encode_image(final_img, actual_format, quality=quality)
            processing_time = round(time.perf_counter() - start_time, 4)
            optimized_size = len(out_bytes)

            out_fn = build_output_filename(
                filename,
                EXTENSIONS.get(actual_format, "png"),
                suffix=suffix,
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
                original_thumb=orig_thumb,
                note=f"{used_engine_label} · Mode: {mode.capitalize()}",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Background removal failed for %s", filename)
        return OptimizationResult(
            status="failed",
            image_id=image_id,
            original_filename=filename,
            original_size=original_size,
            original_thumb=orig_thumb,
            error=str(exc) or "Failed to remove background.",
            processing_time=round(time.perf_counter() - start_time, 4),
        )


def _cutout_subject(
    img: Image.Image,
    *,
    engine: str = "auto",
    model_name: str = "u2net",
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
    post_process_mask: bool = True,
    tolerance: int = 35,
    edge_feather: int = 2,
    defringe: bool = True,
) -> Tuple[Image.Image, str]:
    """Extract foreground cutout using AI Neural Matting or Smart Keying."""
    use_ai = (engine in ("auto", "ai")) and _HAS_REMBG and (rembg is not None)

    if use_ai:
        try:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            session = get_rembg_session(model_name)
            
            kwargs: Dict[str, Any] = {
                "post_process_mask": post_process_mask,
            }
            if session is not None:
                kwargs["session"] = session
            if alpha_matting:
                kwargs["alpha_matting"] = True
                kwargs["alpha_matting_foreground_threshold"] = alpha_matting_foreground_threshold
                kwargs["alpha_matting_background_threshold"] = alpha_matting_background_threshold
                kwargs["alpha_matting_erode_size"] = alpha_matting_erode_size

            cutout_bytes = rembg.remove(buf.getvalue(), **kwargs)
            res_img = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
            
            if defringe and edge_feather > 0:
                res_img = _defringe_cutout(res_img)
                
            model_label = AI_MODELS.get(model_name, model_name)
            return res_img, f"AI Neural ({model_label})"
        except Exception as exc:
            logger.warning("AI rembg execution failed, switching to smart keying: %s", exc)

    # Built-in zero-dependency smart color & edge keyer
    is_chroma = (engine == "chroma")
    keyer_img = _smart_color_cutout(
        img,
        tolerance=tolerance,
        edge_feather=edge_feather,
        defringe=defringe,
        is_chroma=is_chroma,
    )
    engine_label = "Chroma Screen Keyer" if is_chroma else "Smart Perceptual & Edge Keyer"
    return keyer_img, engine_label


def _smart_color_cutout(
    img: Image.Image,
    *,
    tolerance: int = 35,
    edge_feather: int = 2,
    defringe: bool = True,
    is_chroma: bool = False,
) -> Image.Image:
    """Multi-pass perceptual color distance and boundary-seeded keying engine."""
    rgba = img.convert("RGBA")
    arr = np.array(rgba)
    h, w, _ = arr.shape
    rgb = arr[:, :, :3].astype(np.float32)

    if is_chroma:
        # Chroma Green/Blue screen keying
        # Green screen metric: green dominance over max(red, blue)
        r = rgb[:, :, 0]
        g = rgb[:, :, 1]
        b = rgb[:, :, 2]
        
        green_diff = g - np.maximum(r, b)
        tol = float(max(tolerance, 5))
        # Mask: 0 where green is dominant, 255 where foreground
        alpha = np.clip(1.0 - (green_diff / tol), 0.0, 1.0) * 255.0
    else:
        # Perceptual color distance to multi-point border samples
        # Sample border slices and 4 corner patches
        top_samples = arr[0:max(1, h // 20), :, :3].reshape(-1, 3)
        bot_samples = arr[max(0, h - h // 20):, :, :3].reshape(-1, 3)
        left_samples = arr[:, 0:max(1, w // 20), :3].reshape(-1, 3)
        right_samples = arr[:, max(0, w - w // 20):, :3].reshape(-1, 3)
        
        all_border_samples = np.vstack([top_samples, bot_samples, left_samples, right_samples])
        
        # Primary backdrop sample (median) and corner samples
        bg_primary = np.median(all_border_samples, axis=0).astype(np.float32)
        corner_tl = np.mean(arr[0:5, 0:5, :3], axis=(0, 1)).astype(np.float32)
        corner_tr = np.mean(arr[0:5, max(0, w - 5):, :3], axis=(0, 1)).astype(np.float32)
        corner_bl = np.mean(arr[max(0, h - 5):, 0:5, :3], axis=(0, 1)).astype(np.float32)
        corner_br = np.mean(arr[max(0, h - 5):, max(0, w - 5):, :3], axis=(0, 1)).astype(np.float32)

        # Weighted perceptual distance: human eye sensitivity (R: 0.299, G: 0.587, B: 0.114)
        weights = np.array([0.299, 0.587, 0.114], dtype=np.float32)
        
        def calc_dist(bg_pt: np.ndarray) -> np.ndarray:
            diff = (rgb - bg_pt) ** 2
            return np.sqrt(np.sum(diff * weights, axis=2))

        d_primary = calc_dist(bg_primary)
        d_tl = calc_dist(corner_tl)
        d_tr = calc_dist(corner_tr)
        d_bl = calc_dist(corner_bl)
        d_br = calc_dist(corner_br)

        # Minimum distance to any of the background sample points (handles gradients & lighting)
        min_dist = np.minimum(d_primary, np.minimum(np.minimum(d_tl, d_tr), np.minimum(d_bl, d_br)))

        tol = float(max(tolerance, 5))
        softness = max(tol * 0.35, 4.0)
        
        # Alpha transfer function
        alpha = np.clip((min_dist - (tol - softness)) / (softness * 2.0), 0.0, 1.0) * 255.0

    alpha_u8 = alpha.astype(np.uint8)
    alpha_img = Image.fromarray(alpha_u8, mode="L")

    # Anti-aliasing / edge feathering
    if edge_feather > 0:
        alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=edge_feather))

    # Preserve any original alpha transparency if present
    if "A" in img.getbands():
        orig_alpha = np.array(img.getchannel("A"))
        combined_alpha = np.minimum(np.array(alpha_img), orig_alpha)
        alpha_img = Image.fromarray(combined_alpha, mode="L")

    rgba.putalpha(alpha_img)
    
    if defringe:
        rgba = _defringe_cutout(rgba)

    return rgba


def _defringe_cutout(rgba_img: Image.Image) -> Image.Image:
    """Eliminate color bleed and halo artifacts around semi-transparent cutout boundaries."""
    arr = np.array(rgba_img).copy()
    alpha = arr[:, :, 3]
    
    # Identify fringe region: semi-transparent pixels (e.g. alpha between 10 and 230)
    fringe_mask = (alpha > 10) & (alpha < 230)
    if not np.any(fringe_mask):
        return rgba_img

    # Desaturate fringe pixels slightly to avoid glowing border lines
    rgb = arr[:, :, :3].astype(np.float32)
    gray = np.dot(rgb, [0.299, 0.587, 0.114])[:, :, None]
    
    blend_factor = (1.0 - (alpha[fringe_mask].astype(np.float32) / 255.0))[:, None] * 0.4
    desaturated = (rgb[fringe_mask] * (1.0 - blend_factor) + gray[fringe_mask] * blend_factor)
    
    arr[fringe_mask, :3] = np.clip(desaturated, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGBA")


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
