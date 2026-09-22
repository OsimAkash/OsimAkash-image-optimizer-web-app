"""Background Remover page: transparent cutout, solid backdrop replacement, and edge tuning."""

from __future__ import annotations

import streamlit as st

from components.results import record_result, render_dashboard
from components.upload import render_image_grid, render_uploader
from core.bg_remover import has_ai_remover, remove_background


def _on_remove(image_id: str) -> None:
    uploads: list = st.session_state.get("bg_uploads", [])
    st.session_state["bg_uploads"] = [u for u in uploads if u.id != image_id]
    st.session_state.get("bg_previews", set()).discard(image_id)
    st.session_state.get("bg_results", {}).pop(image_id, None)


def _get_bg_params() -> tuple[str, str, int, int, str]:
    mode_label = st.session_state.get("bg_mode", "Transparent Cutout")
    mode = "transparent" if mode_label == "Transparent Cutout" else "color"
    color = st.session_state.get("bg_color_picker", "#FFFFFF")
    tolerance = int(st.session_state.get("bg_tolerance", 35))
    feather = int(st.session_state.get("bg_feather", 2))
    fmt = st.session_state.get("bg_format", "PNG")
    return mode, color, tolerance, feather, fmt


def _on_remove_bg_all() -> None:
    uploads: list = st.session_state.get("bg_uploads", [])
    if not uploads:
        return
    mode, color, tolerance, feather, fmt = _get_bg_params()

    progress = st.progress(0.0, text="Preparing…")
    status = st.empty()
    results: dict = st.session_state.setdefault("bg_results", {})

    for index, upload in enumerate(uploads, start=1):
        status.markdown(f"**Removing background {index} of {len(uploads)}** — {upload.filename}")
        progress.progress((index - 1) / len(uploads), text=f"Processing {index} of {len(uploads)} images")
        result = remove_background(
            upload.data,
            mode=mode,
            bg_color=color,
            tolerance=tolerance,
            edge_feather=feather,
            output_format=fmt,
            filename=upload.filename,
            image_id=upload.id,
        )
        record_result(result, "bg_results")

    succeeded = sum(1 for u in uploads if results.get(u.id) and results[u.id].status == "success")
    progress.progress(1.0, text=f"✅ Background removal finished — {succeeded} succeeded.")
    status.empty()


def _on_remove_bg_single(image_id: str) -> None:
    uploads: list = st.session_state.get("bg_uploads", [])
    upload = next((u for u in uploads if u.id == image_id), None)
    if upload is None:
        return
    mode, color, tolerance, feather, fmt = _get_bg_params()
    result = remove_background(
        upload.data,
        mode=mode,
        bg_color=color,
        tolerance=tolerance,
        edge_feather=feather,
        output_format=fmt,
        filename=upload.filename,
        image_id=upload.id,
    )
    record_result(result, "bg_results")


def render() -> None:
    st.markdown(
        "<div class='opt-section-title' style='margin-top:0.2rem'>🪄 Background Remover</div>"
        "<div class='opt-section-sub'>Extract subjects, create transparent cutouts, or replace backgrounds "
        "with studio solid colors and smooth edge feathering.</div>",
        unsafe_allow_html=True,
    )

    cfg_max_mb = int(st.session_state.get("cfg_max_mb", 20))
    cfg_max_mp = int(st.session_state.get("cfg_max_mp", 60))
    uploads = render_uploader(
        cache_key="bg", uploads_key="bg_uploads",
        max_file_mb=cfg_max_mb, max_pixels=cfg_max_mp * 1_000_000,
    )

    with st.container(border=True):
        st.markdown("### ⚙️ Background removal settings")

        mode_col, format_col = st.columns(2)
        mode_col.radio(
            "Output background",
            ["Transparent Cutout", "Custom Color Replacement"],
            key="bg_mode",
            horizontal=True,
            help="Transparent Cutout produces alpha PNG/WebP. Custom Color replaces background with a solid studio shade.",
        )
        format_col.selectbox(
            "Export format",
            ["PNG", "WEBP", "JPEG"],
            key="bg_format",
            index=0,
            help="PNG and WebP support full alpha transparency. JPEG will flatten with the background color.",
        )

        if st.session_state.get("bg_mode") == "Custom Color Replacement":
            c_cols = st.columns([1, 2])
            c_cols[0].color_picker("Background color", "#FFFFFF", key="bg_color_picker")
            c_cols[1].caption("Pick a color for the new solid background.")

        t_col, f_col = st.columns(2)
        t_col.slider(
            "Tolerance sensitivity",
            min_value=5, max_value=90, value=35, step=5,
            key="bg_tolerance",
            help="Higher tolerance removes more background around the subject edges.",
        )
        f_col.slider(
            "Edge softness (feather)",
            min_value=0, max_value=8, value=2, step=1,
            key="bg_feather",
            help="Blurs the boundary mask slightly for clean, anti-aliased cutout edges.",
        )

        if has_ai_remover():
            st.caption("✨ Neural AI Matting is active for automatic subject extraction.")
        else:
            st.caption("ℹ️ Smart color & edge keying engine active.")

    if not uploads:
        st.info("👆 **Add images above** to extract subjects or remove backgrounds.")
        st.button("🪄 Remove Background", type="primary", width="stretch", disabled=True)
        return

    render_image_grid(
        uploads,
        results_key="bg_results",
        previews_key="bg_previews",
        on_remove=_on_remove,
        on_optimize=_on_remove_bg_single,
        optimize_label="Remove BG",
    )

    st.button(
        f"🪄 Remove Background for {len(uploads)} image{'s' if len(uploads) != 1 else ''}",
        type="primary", width="stretch", on_click=_on_remove_bg_all,
    )

    live_ids = {u.id for u in uploads}
    results: dict = st.session_state.get("bg_results", {})
    st.session_state["bg_results"] = {k: v for k, v in results.items() if k in live_ids}
    ordered = [st.session_state["bg_results"][u.id] for u in uploads if u.id in st.session_state["bg_results"]]
    render_dashboard(ordered, key_prefix="bg", zip_name="cutout-images.zip")
