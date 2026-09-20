"""Image Resizer page: width / height / percentage scaling with preset widths
and a live dimension preview before processing."""

from __future__ import annotations

import streamlit as st

from components.results import record_result, render_dashboard
from components.upload import render_image_grid, render_uploader
from core.resizer import PRESET_WIDTHS, compute_resize_dimensions, resize_data

MODES = {"By Width": "width", "By Height": "height", "By Percentage": "percent"}
OUTPUT_FORMATS = {"Keep original": "original", "JPEG": "jpeg", "PNG": "png", "WEBP": "webp"}


def _on_remove(image_id: str) -> None:
    uploads: list = st.session_state.get("rz_uploads", [])
    st.session_state["rz_uploads"] = [u for u in uploads if u.id != image_id]
    st.session_state.get("rz_previews", set()).discard(image_id)
    st.session_state.get("rz_results", {}).pop(image_id, None)


def _preset_width(width: int) -> None:
    st.session_state["rz_mode"] = "By Width"
    st.session_state["rz_value"] = width


def _resize_mode_changed() -> None:
    """Selectbox callback: reset the value to a valid default for the new mode."""
    mode = MODES.get(st.session_state.get("rz_mode", "By Width"))
    st.session_state["rz_value"] = 100 if mode == "percent" else 1600


def _current_params() -> tuple[str, int, bool]:
    mode = MODES.get(st.session_state.get("rz_mode", "By Width"), "width")
    value = int(st.session_state.get("rz_value", 1600) or 1600)
    maintain = bool(st.session_state.get("rz_aspect", True))
    return mode, value, maintain


def _on_resize_all() -> None:
    uploads: list = st.session_state.get("rz_uploads", [])
    if not uploads:
        return
    mode, value, maintain = _current_params()
    target = OUTPUT_FORMATS.get(st.session_state.get("rz_format", "Keep original"), "original")
    quality = int(st.session_state.get("rz_quality", 90)) if target in ("jpeg", "webp", "original") else 90

    progress = st.progress(0.0, text="Preparing…")
    status = st.empty()
    results: dict = st.session_state.setdefault("rz_results", {})

    for index, upload in enumerate(uploads, start=1):
        status.markdown(f"**Resizing {index} of {len(uploads)} images** — {upload.filename}")
        progress.progress((index - 1) / len(uploads), text=f"Resizing {index} of {len(uploads)} images")
        result = resize_data(
            upload.data, mode, value, maintain_aspect=maintain,
            output_format=target, quality=quality, filename=upload.filename,
        )
        result.image_id = upload.id
        record_result(result, "rz_results")

    succeeded = sum(1 for u in uploads if results.get(u.id) and results[u.id].status == "success")
    progress.progress(1.0, text=f"✅ Resizing finished — {succeeded} succeeded, {len(uploads) - succeeded} failed.")
    status.empty()


def _on_resize_single(image_id: str) -> None:
    uploads: list = st.session_state.get("rz_uploads", [])
    upload = next((u for u in uploads if u.id == image_id), None)
    if upload is None:
        return
    mode, value, maintain = _current_params()
    target = OUTPUT_FORMATS.get(st.session_state.get("rz_format", "Keep original"), "original")
    quality = int(st.session_state.get("rz_quality", 90)) if target in ("jpeg", "webp", "original") else 90
    result = resize_data(upload.data, mode, value, maintain_aspect=maintain,
                         output_format=target, quality=quality, filename=upload.filename)
    result.image_id = upload.id
    record_result(result, "rz_results")


def render() -> None:
    st.markdown(
        "<div class='opt-section-title' style='margin-top:0.2rem'>📐 Image Resizer</div>"
        "<div class='opt-section-sub'>Scale images precisely — by width, height or percentage, "
        "always with high-quality LANCZOS resampling.</div>",
        unsafe_allow_html=True,
    )

    cfg_max_mb = int(st.session_state.get("cfg_max_mb", 20))
    cfg_max_mp = int(st.session_state.get("cfg_max_mp", 60))
    uploads = render_uploader(
        cache_key="rz", uploads_key="rz_uploads",
        max_file_mb=cfg_max_mb, max_pixels=cfg_max_mp * 1_000_000,
    )
    # Settings widgets render on every visit so their seeded session keys bind
    # before any upload interaction (Streamlit late-creation binding quirk).
    with st.container(border=True):
        st.markdown("### ⚙️ Resize settings")

        preset_cols = st.columns(len(PRESET_WIDTHS) + 1)
        preset_cols[0].markdown("**Width presets**")
        for col, width in zip(preset_cols[1:], PRESET_WIDTHS):
            col.button(f"{width} px", key=f"preset_w_{width}", on_click=_preset_width, args=(width,),
                       width="stretch")

        mode_col, value_col = st.columns(2)
        mode_col.selectbox("Resize mode", list(MODES), key="rz_mode", on_change=_resize_mode_changed)
        mode_key = MODES.get(st.session_state.get("rz_mode", "By Width"))
        if mode_key == "percent":
            value_col.number_input("Scale (%)", min_value=1, max_value=400, value=100, key="rz_value")
        else:
            value_col.number_input(f"Target {mode_key} (px)", min_value=16, max_value=12000,
                                   value=1600, key="rz_value")

        aspect_col, format_col = st.columns(2)
        if mode_key != "percent":
            aspect_col.checkbox(
                "Maintain aspect ratio", key="rz_aspect", value=True,
                help="When unchecked, the other dimension stays at its original value.",
            )
        else:
            aspect_col.caption("Percentage scaling always keeps the aspect ratio.")
        format_col.selectbox("Output format", list(OUTPUT_FORMATS), key="rz_format")
        if OUTPUT_FORMATS.get(st.session_state.get("rz_format", "Keep original")) in ("jpeg", "webp", "original"):
            st.slider("Re-encode quality", 10, 100, 90, key="rz_quality",
                      help="Applies when the output is a lossy format (JPEG/WebP).")

        if uploads:
            st.markdown("**Dimension preview**")
            mode, value, maintain = _current_params()
            for upload in uploads[:8]:
                new_w, new_h = compute_resize_dimensions(upload.width, upload.height, mode, value,
                                                        maintain_aspect=maintain)
                st.markdown(
                    f"<div class='opt-meta-line'>📄 <strong>{upload.filename}</strong>"
                    f"&nbsp;&nbsp;{upload.width} × {upload.height} → <strong>{new_w} × {new_h}</strong></div>",
                    unsafe_allow_html=True,
                )
            if len(uploads) > 8:
                st.caption(f"+ {len(uploads) - 8} more images.")

    if not uploads:
        st.info("👆 **Add images above** to see original → new dimensions before you resize.")
        st.button("📐 Resize", type="primary", width="stretch", disabled=True)
        return

    from components.upload import render_image_grid
    render_image_grid(
        uploads,
        results_key="rz_results",
        previews_key="rz_previews",
        on_remove=_on_remove,
        on_optimize=_on_resize_single,
        optimize_label="Resize",
    )

    st.button(
        f"📐 Resize {len(uploads)} image{'s' if len(uploads) != 1 else ''}",
        type="primary", width="stretch", on_click=_on_resize_all,
    )

    live_ids = {u.id for u in uploads}
    results: dict = st.session_state.get("rz_results", {})
    st.session_state["rz_results"] = {k: v for k, v in results.items() if k in live_ids}
    ordered = [st.session_state["rz_results"][u.id] for u in uploads if u.id in st.session_state["rz_results"]]
    render_dashboard(ordered, key_prefix="rz", zip_name="resized-images.zip")
