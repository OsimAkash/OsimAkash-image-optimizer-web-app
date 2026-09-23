"""Fresh Color Editor & Enhancer page: one-click aesthetic presets, auto-levels and fine-tuning sliders."""

from __future__ import annotations

import streamlit as st

from components.results import record_result, render_dashboard
from components.upload import render_image_grid, render_uploader
from core.enhancer import COLOR_PRESETS, enhance_image

OUTPUT_FORMATS = {"Keep original": "original", "JPEG": "jpeg", "PNG": "png", "WEBP": "webp"}


def _apply_preset(name: str) -> None:
    preset = COLOR_PRESETS[name]
    st.session_state["enh_brightness"] = preset.brightness
    st.session_state["enh_contrast"] = preset.contrast
    st.session_state["enh_saturation"] = preset.saturation
    st.session_state["enh_sharpness"] = preset.sharpness
    st.session_state["enh_auto_contrast"] = preset.auto_contrast
    st.session_state["enh_tint"] = preset.tint


def _on_remove(image_id: str) -> None:
    uploads: list = st.session_state.get("enh_uploads", [])
    st.session_state["enh_uploads"] = [u for u in uploads if u.id != image_id]
    st.session_state.get("enh_previews", set()).discard(image_id)
    st.session_state.get("enh_results", {}).pop(image_id, None)


def _get_enh_params() -> tuple[float, float, float, float, bool, str, str, int]:
    b = float(st.session_state.get("enh_brightness", 1.0))
    c = float(st.session_state.get("enh_contrast", 1.0))
    s = float(st.session_state.get("enh_saturation", 1.0))
    sh = float(st.session_state.get("enh_sharpness", 1.0))
    auto_c = bool(st.session_state.get("enh_auto_contrast", False))
    tint = str(st.session_state.get("enh_tint", "none"))
    fmt = OUTPUT_FORMATS.get(st.session_state.get("enh_format", "Keep original"), "original")
    q = int(st.session_state.get("enh_quality", 92))
    return b, c, s, sh, auto_c, tint, fmt, q


def _on_enhance_all() -> None:
    uploads: list = st.session_state.get("enh_uploads", [])
    if not uploads:
        return
    b, c, s, sh, auto_c, tint, fmt, q = _get_enh_params()

    progress = st.progress(0.0, text="Preparing…")
    status = st.empty()
    results: dict = st.session_state.setdefault("enh_results", {})

    for index, upload in enumerate(uploads, start=1):
        status.markdown(f"**Enhancing colors {index} of {len(uploads)}** — {upload.filename}")
        progress.progress((index - 1) / len(uploads), text=f"Processing {index} of {len(uploads)} images")
        result = enhance_image(
            upload.data,
            brightness=b,
            contrast=c,
            saturation=s,
            sharpness=sh,
            auto_contrast=auto_c,
            tint=tint,
            output_format=fmt,
            quality=q,
            filename=upload.filename,
            image_id=upload.id,
        )
        record_result(result, "enh_results")

    succeeded = sum(1 for u in uploads if results.get(u.id) and results[u.id].status == "success")
    progress.progress(1.0, text=f"✅ Color enhancement finished — {succeeded} succeeded.")
    status.empty()


def _on_enhance_single(image_id: str) -> None:
    uploads: list = st.session_state.get("enh_uploads", [])
    upload = next((u for u in uploads if u.id == image_id), None)
    if upload is None:
        return
    b, c, s, sh, auto_c, tint, fmt, q = _get_enh_params()
    result = enhance_image(
        upload.data,
        brightness=b,
        contrast=c,
        saturation=s,
        sharpness=sh,
        auto_contrast=auto_c,
        tint=tint,
        output_format=fmt,
        quality=q,
        filename=upload.filename,
        image_id=upload.id,
    )
    record_result(result, "enh_results")


def render() -> None:
    st.markdown(
        "<div class='opt-section-title' style='margin-top:0.2rem'>🎨 Fresh Color Editor</div>"
        "<div class='opt-section-sub'>Make photos pop with one-click aesthetic filters, auto-levels, "
        "and studio tone &amp; clarity tuning.</div>",
        unsafe_allow_html=True,
    )

    cfg_max_mb = int(st.session_state.get("cfg_max_mb", 20))
    cfg_max_mp = int(st.session_state.get("cfg_max_mp", 60))
    uploads = render_uploader(
        cache_key="enh", uploads_key="enh_uploads",
        max_file_mb=cfg_max_mb, max_pixels=cfg_max_mp * 1_000_000,
    )

    with st.container(border=True):
        st.markdown("### ✨ Aesthetic Presets")
        preset_cols = st.columns(len(COLOR_PRESETS))
        for col, (name, preset) in zip(preset_cols, COLOR_PRESETS.items()):
            col.button(
                f"{preset.icon} {name}",
                key=f"preset_enh_{name}",
                on_click=_apply_preset,
                args=(name,),
                width="stretch",
                help=preset.description,
            )

        st.markdown("### 🎛️ Fine-Tune Color &amp; Tone")

        col1, col2 = st.columns(2)
        col1.slider("☀️ Brightness", 0.50, 1.80, 1.00, 0.02, key="enh_brightness")
        col2.slider("🌓 Contrast", 0.50, 1.80, 1.00, 0.02, key="enh_contrast")

        col3, col4 = st.columns(2)
        col3.slider("🌈 Saturation / Vibrance", 0.00, 2.20, 1.00, 0.05, key="enh_saturation")
        col4.slider("🔍 Sharpness / Clarity", 0.00, 2.50, 1.00, 0.05, key="enh_sharpness")

        c_opt1, c_opt2 = st.columns(2)
        c_opt1.checkbox("✨ Auto-Contrast (Stretch Dynamic Range)", key="enh_auto_contrast", value=False)
        c_opt2.selectbox(
            "Color Tint",
            ["none", "warm", "cool", "vintage"],
            format_func=lambda x: {"none": "None", "warm": "☀️ Warm Golden", "cool": "❄️ Cool Cyan", "vintage": "🎞️ Vintage Film"}.get(x, x),
            key="enh_tint",
        )

        f_col, q_col = st.columns(2)
        f_col.selectbox("Output Format", list(OUTPUT_FORMATS), key="enh_format")
        q_col.slider("Export Quality", 10, 100, 92, key="enh_quality")

    if not uploads:
        st.info("👆 **Add images above** to preview and apply fresh color enhancements.")
        st.button("🎨 Enhance Colors", type="primary", width="stretch", disabled=True)
        return

    render_image_grid(
        uploads,
        results_key="enh_results",
        previews_key="enh_previews",
        on_remove=_on_remove,
        on_optimize=_on_enhance_single,
        optimize_label="Enhance",
    )

    st.button(
        f"🎨 Apply Color Enhancements to {len(uploads)} image{'s' if len(uploads) != 1 else ''}",
        type="primary", width="stretch", on_click=_on_enhance_all,
    )

    live_ids = {u.id for u in uploads}
    results: dict = st.session_state.get("enh_results", {})
    st.session_state["enh_results"] = {k: v for k, v in results.items() if k in live_ids}
    ordered = [st.session_state["enh_results"][u.id] for u in uploads if u.id in st.session_state["enh_results"]]
    render_dashboard(ordered, key_prefix="enh", zip_name="enhanced-images.zip")
