"""Optimizer settings panel: presets, compression mode, quality, format, resize,
Smart Optimize recommendations and size estimation."""

from __future__ import annotations

import streamlit as st

from core.analyzer import UploadedImage, estimate_output_size
from core.optimizer import MODE_QUALITY, PRESETS, OptimizationSettings
from utils.file_utils import format_bytes

RESIZE_MODE_LABELS = ["Original", "Custom Width", "Custom Height", "Percentage"]
_FORMAT_LABEL_TO_KEY = {"Original": "original", "JPEG": "jpeg", "PNG": "png", "WEBP": "webp"}
_RESIZE_LABEL_TO_KEY = {"Original": "original", "Custom Width": "width",
                        "Custom Height": "height", "Percentage": "percent"}
_FORMAT_KEY_TO_LABEL = {v: k for k, v in _FORMAT_LABEL_TO_KEY.items()}
_RESIZE_KEY_TO_LABEL = {v: k for k, v in _RESIZE_LABEL_TO_KEY.items()}


def apply_preset(preset_name: str) -> None:
    """Button callback: write a preset straight into the widget-backed session keys."""
    preset = PRESETS[preset_name]
    st.session_state["opt_mode"] = preset.mode
    st.session_state["opt_quality"] = preset.quality
    st.session_state["opt_format"] = _FORMAT_KEY_TO_LABEL.get(preset.output_format, "Original")
    st.session_state["opt_resize_mode"] = "Original"
    st.session_state["opt_resize_value"] = 100


def mode_changed() -> None:
    """Selectbox callback: switching modes snaps the quality slider to the mode default."""
    mode = st.session_state.get("opt_mode", "Balanced")
    if mode in MODE_QUALITY:
        st.session_state["opt_quality"] = MODE_QUALITY[mode]


def resize_mode_changed() -> None:
    """Selectbox callback: reset the resize value to a sane default for the new mode."""
    mode = st.session_state.get("opt_resize_mode", "Original")
    st.session_state["opt_resize_value"] = {"Custom Width": 1600, "Custom Height": 1200}.get(mode, 100)


def render_settings_panel(uploads: list[UploadedImage]) -> None:
    """Render the full optimizer settings panel (widget keys live in session state)."""
    with st.container(border=True):
        st.markdown("### ⚙️ Optimization settings")

        smart = st.toggle(
            "✨ Smart Optimize",
            key="smart",
            help="Automatically choose the best format and quality for each image "
                 "based on its format, size, dimensions and transparency.",
        )
        if smart and uploads:
            _render_recommendations(uploads)

        st.markdown("**Presets**")
        preset_cols = st.columns(len(PRESETS))
        for col, (name, preset) in zip(preset_cols, PRESETS.items()):
            col.button(name, key=f"preset_{name}", on_click=apply_preset, args=(name,),
                       width="stretch",
                       help=f"Quality {preset.quality} · {preset.output_format.replace('original', 'keep original format')}")

        mode_col, format_col = st.columns(2)
        mode_col.selectbox(
            "Compression mode", list(MODE_QUALITY) + ["Custom"],
            index=1, key="opt_mode", on_change=mode_changed,
            help="Modes map to fixed quality levels; Custom uses the slider below.",
        )
        format_col.radio(
            "Output format", list(_FORMAT_LABEL_TO_KEY), horizontal=True, key="opt_format",
            help="JPEG does not support transparency — transparent pixels get a white background.",
        )

        st.slider("Quality", min_value=10, max_value=100, value=80, key="opt_quality",
                  disabled=st.session_state.get("opt_mode") != "Custom",
                  help="Higher values keep more detail but produce larger files.")

        st.markdown("**Resize before optimization**")
        resize_col, value_col = st.columns([1.3, 1])
        resize_col.selectbox("Resize", RESIZE_MODE_LABELS, key="opt_resize_mode",
                             on_change=resize_mode_changed)
        mode_key = _RESIZE_LABEL_TO_KEY.get(st.session_state.get("opt_resize_mode", "Original"))
        if mode_key == "percent":
            value_col.number_input("Scale (%)", min_value=1, max_value=400, value=100, key="opt_resize_value")
        elif mode_key in ("width", "height"):
            value_col.number_input("Pixels", min_value=16, max_value=12000, value=1600, key="opt_resize_value")
        else:
            value_col.caption("No resizing — the original dimensions are kept.")

        st.checkbox("Maintain aspect ratio", key="opt_aspect", value=True)
        st.checkbox(
            "Remove Metadata", key="opt_meta", value=True,
            help="Strip EXIF/ICC metadata (GPS, camera, software) for improved privacy.",
        )


def _render_recommendations(uploads: list[UploadedImage]) -> None:
    """Show the Smart Optimize recommendation for each uploaded image."""
    from core.optimizer import recommend_settings

    st.markdown("**Smart recommendations**")
    for upload in uploads[:6]:
        settings, reason = recommend_settings(upload.info)
        quality_text = f" + {settings.effective_quality}% quality" if settings.output_format != "png" else ""
        target_label = _FORMAT_KEY_TO_LABEL.get(settings.output_format, "Original")
        st.markdown(
            f"<div class='opt-rec'><strong>{upload.filename} — Recommended: "
            f"{target_label}{quality_text}</strong><span>{reason}</span></div>",
            unsafe_allow_html=True,
        )
    if len(uploads) > 6:
        st.caption(f"+ {len(uploads) - 6} more images will get individual recommendations.")


def build_settings_from_state(prefix: str = "opt") -> OptimizationSettings:
    """Collect the settings widgets' session values into an :class:`OptimizationSettings`."""
    state = st.session_state
    return OptimizationSettings(
        mode=state.get(f"{prefix}_mode", "Balanced"),
        quality=int(state.get(f"{prefix}_quality", 80)),
        output_format=_FORMAT_LABEL_TO_KEY.get(state.get(f"{prefix}_format", "Original"), "original"),
        resize_mode=_RESIZE_LABEL_TO_KEY.get(state.get(f"{prefix}_resize_mode", "Original"), "original"),
        resize_value=int(state.get(f"{prefix}_resize_value", 100)),
        maintain_aspect=bool(state.get(f"{prefix}_aspect", True)),
        remove_metadata=bool(state.get(f"{prefix}_meta", True)),
    )


def render_estimates_section(uploads: list[UploadedImage]) -> None:
    """Estimate-and-display potential savings (clearly labeled as estimates)."""
    st.markdown(
        "<div class='opt-section-title'>🔮 Size estimation</div>"
        "<div class='opt-section-sub'>A rough preview of what the current settings would produce.</div>",
        unsafe_allow_html=True,
    )
    if st.button("✨ Estimate potential savings", type="secondary",
                 disabled=not uploads, width="stretch"):
        st.session_state["show_estimates"] = True

    if not st.session_state.get("show_estimates") or not uploads:
        return

    smart = st.session_state.get("smart", False)
    settings = build_settings_from_state() if not smart else None
    rows = []
    for upload in uploads[:10]:
        if smart:
            from core.optimizer import recommend_settings
            per_image, _ = recommend_settings(upload.info)
        else:
            per_image = settings
        estimate = estimate_output_size(
            upload.data,
            target_format=per_image.output_format,
            quality=per_image.effective_quality,
            resize_mode=per_image.resize_mode,
            resize_value=per_image.resize_value,
            maintain_aspect=per_image.maintain_aspect,
        )
        rows.append({
            "Image": upload.filename,
            "Current": format_bytes(upload.size),
            "Estimated": f"{format_bytes(estimate.low_bytes)} – {format_bytes(estimate.high_bytes)}",
            "Potential savings": f"~{estimate.savings_low:.0f}–{estimate.savings_high:.0f}%",
        })

    if len(uploads) > 10:
        rows.append({"Image": f"… +{len(uploads) - 10} more", "Current": "—",
                     "Estimated": "—", "Potential savings": "—"})

    import pandas as pd
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption(estimate_note())


def estimate_note() -> str:
    return ("ℹ️ These are estimates only — a small sample of each image is encoded with the chosen "
            "settings and extrapolated. The actual result depends on image content.")
