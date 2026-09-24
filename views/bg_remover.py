"""Background Remover view: professional AI neural matting, smart chroma keying,
studio solid backdrop, bokeh blur, and fine edge hair feathering.
"""

from __future__ import annotations

import streamlit as st

from components.results import record_result, render_dashboard
from components.upload import render_image_grid, render_uploader
from core.bg_remover import (
    AI_MODELS,
    STUDIO_PALETTES,
    has_ai_remover,
    remove_background,
)


def _on_remove(image_id: str) -> None:
    uploads: list = st.session_state.get("bg_uploads", [])
    st.session_state["bg_uploads"] = [u for u in uploads if u.id != image_id]
    st.session_state.get("bg_previews", set()).discard(image_id)
    st.session_state.get("bg_results", {}).pop(image_id, None)


def _get_bg_params() -> dict:
    """Collect all background removal parameters from session state."""
    mode_label = st.session_state.get("bg_mode", "Transparent Cutout")
    mode_map = {
        "Transparent Cutout": "transparent",
        "Solid Studio Color": "color",
        "Portrait Bokeh Blur": "blur",
        "Custom Image Backdrop": "custom_image",
        "Black & White Alpha Matte": "mask",
    }
    mode = mode_map.get(mode_label, "transparent")
    
    engine_label = st.session_state.get("bg_engine", "Auto (Neural AI if available)")
    engine_map = {
        "Auto (Neural AI if available)": "auto",
        "AI Neural Network (rembg)": "ai",
        "Smart Perceptual Keyer (Built-in)": "smart",
        "Chroma Keyer (Green/Blue Screen)": "chroma",
    }
    engine = engine_map.get(engine_label, "auto")

    model_name = st.session_state.get("bg_ai_model", "u2net")
    alpha_matting = bool(st.session_state.get("bg_alpha_matting", False))
    af_thresh = int(st.session_state.get("bg_af_thresh", 240))
    ab_thresh = int(st.session_state.get("bg_ab_thresh", 10))
    erode_size = int(st.session_state.get("bg_erode_size", 10))
    post_process = bool(st.session_state.get("bg_post_process", True))

    color = st.session_state.get("bg_color_picker", "#FFFFFF")
    blur_radius = int(st.session_state.get("bg_blur_radius", 25))
    tolerance = int(st.session_state.get("bg_tolerance", 35))
    feather = int(st.session_state.get("bg_feather", 2))
    defringe = bool(st.session_state.get("bg_defringe", True))
    fmt = st.session_state.get("bg_format", "PNG")
    quality = int(st.session_state.get("bg_quality", 92))

    bg_custom_bytes = st.session_state.get("bg_custom_image_bytes", b"")

    return {
        "mode": mode,
        "bg_color": color,
        "blur_radius": blur_radius,
        "bg_image_data": bg_custom_bytes,
        "engine": engine,
        "model_name": model_name,
        "alpha_matting": alpha_matting,
        "alpha_matting_foreground_threshold": af_thresh,
        "alpha_matting_background_threshold": ab_thresh,
        "alpha_matting_erode_size": erode_size,
        "post_process_mask": post_process,
        "tolerance": tolerance,
        "edge_feather": feather,
        "defringe": defringe,
        "output_format": fmt,
        "quality": quality,
    }


def _apply_preset(preset_name: str) -> None:
    """Quick 1-click preset configurations."""
    if preset_name == "auto_ai":
        st.session_state["bg_mode"] = "Transparent Cutout"
        st.session_state["bg_engine"] = "Auto (Neural AI if available)"
        st.session_state["bg_ai_model"] = "u2net"
        st.session_state["bg_alpha_matting"] = False
        st.session_state["bg_format"] = "PNG"
        st.session_state["bg_defringe"] = True
    elif preset_name == "portrait":
        st.session_state["bg_mode"] = "Transparent Cutout"
        st.session_state["bg_engine"] = "AI Neural Network (rembg)" if has_ai_remover() else "Auto (Neural AI if available)"
        st.session_state["bg_ai_model"] = "u2net_human_seg"
        st.session_state["bg_alpha_matting"] = True
        st.session_state["bg_feather"] = 2
        st.session_state["bg_format"] = "PNG"
        st.session_state["bg_defringe"] = True
    elif preset_name == "ecommerce":
        st.session_state["bg_mode"] = "Solid Studio Color"
        st.session_state["bg_color_picker"] = "#FFFFFF"
        st.session_state["bg_engine"] = "Auto (Neural AI if available)"
        st.session_state["bg_ai_model"] = "isnet-general-use" if has_ai_remover() else "u2net"
        st.session_state["bg_feather"] = 1
        st.session_state["bg_format"] = "JPEG"
        st.session_state["bg_quality"] = 92
        st.session_state["bg_defringe"] = True
    elif preset_name == "bokeh":
        st.session_state["bg_mode"] = "Portrait Bokeh Blur"
        st.session_state["bg_blur_radius"] = 25
        st.session_state["bg_engine"] = "Auto (Neural AI if available)"
        st.session_state["bg_ai_model"] = "u2net_human_seg" if has_ai_remover() else "u2net"
        st.session_state["bg_format"] = "JPEG"
        st.session_state["bg_quality"] = 92
    elif preset_name == "chroma":
        st.session_state["bg_mode"] = "Transparent Cutout"
        st.session_state["bg_engine"] = "Chroma Keyer (Green/Blue Screen)"
        st.session_state["bg_tolerance"] = 40
        st.session_state["bg_feather"] = 2
        st.session_state["bg_defringe"] = True
        st.session_state["bg_format"] = "PNG"
    elif preset_name == "logo":
        st.session_state["bg_mode"] = "Transparent Cutout"
        st.session_state["bg_engine"] = "Smart Perceptual Keyer (Built-in)"
        st.session_state["bg_tolerance"] = 25
        st.session_state["bg_feather"] = 1
        st.session_state["bg_defringe"] = False
        st.session_state["bg_format"] = "PNG"


def _on_remove_bg_all() -> None:
    uploads: list = st.session_state.get("bg_uploads", [])
    if not uploads:
        return
    params = _get_bg_params()

    progress = st.progress(0.0, text="Extracting subjects…")
    status = st.empty()
    results: dict = st.session_state.setdefault("bg_results", {})

    for index, upload in enumerate(uploads, start=1):
        status.markdown(f"**Processing {index} of {len(uploads)}** — {upload.filename}")
        progress.progress((index - 1) / len(uploads), text=f"Removing background {index}/{len(uploads)}")
        result = remove_background(
            upload.data,
            filename=upload.filename,
            image_id=upload.id,
            **params,
        )
        record_result(result, "bg_results")

    succeeded = sum(1 for u in uploads if results.get(u.id) and results[u.id].status == "success")
    progress.progress(1.0, text=f"✅ Background removal complete — {succeeded} of {len(uploads)} processed.")
    status.empty()


def _on_remove_bg_single(image_id: str) -> None:
    uploads: list = st.session_state.get("bg_uploads", [])
    upload = next((u for u in uploads if u.id == image_id), None)
    if upload is None:
        return
    params = _get_bg_params()
    result = remove_background(
        upload.data,
        filename=upload.filename,
        image_id=upload.id,
        **params,
    )
    record_result(result, "bg_results")


def render() -> None:
    st.markdown(
        "<div class='opt-section-title' style='margin-top:0.2rem'>🪄 AI & Professional Background Remover</div>"
        "<div class='opt-section-sub'>Extract crisp subjects, hair & fur matting, replace with studio backdrops, "
        "or create DSLR portrait bokeh blur effects.</div>",
        unsafe_allow_html=True,
    )

    # 1-Click Workflow Presets Bar
    st.markdown("<p style='font-weight:600; font-size:0.9rem; margin-bottom:0.4rem'>⚡ Quick Workflow Presets</p>", unsafe_allow_html=True)
    p_cols = st.columns(6)
    if p_cols[0].button("✨ Auto AI", key="preset_auto", width="stretch"):
        _apply_preset("auto_ai")
        st.rerun()
    if p_cols[1].button("👤 Portrait & Hair", key="preset_portrait", width="stretch"):
        _apply_preset("portrait")
        st.rerun()
    if p_cols[2].button("📦 E-Commerce", key="preset_ecom", width="stretch"):
        _apply_preset("ecommerce")
        st.rerun()
    if p_cols[3].button("📸 Bokeh Blur", key="preset_bokeh", width="stretch"):
        _apply_preset("bokeh")
        st.rerun()
    if p_cols[4].button("🎬 Green Screen", key="preset_chroma", width="stretch"):
        _apply_preset("chroma")
        st.rerun()
    if p_cols[5].button("✍️ Logo / Graphic", key="preset_logo", width="stretch"):
        _apply_preset("logo")
        st.rerun()

    cfg_max_mb = int(st.session_state.get("cfg_max_mb", 20))
    cfg_max_mp = int(st.session_state.get("cfg_max_mp", 60))
    uploads = render_uploader(
        cache_key="bg", uploads_key="bg_uploads",
        max_file_mb=cfg_max_mb, max_pixels=cfg_max_mp * 1_000_000,
    )

    with st.container(border=True):
        st.markdown("### ⚙️ Background removal & studio configuration")

        mode_col, format_col = st.columns([1.3, 1])
        mode_col.selectbox(
            "Output Mode",
            [
                "Transparent Cutout",
                "Solid Studio Color",
                "Portrait Bokeh Blur",
                "Custom Image Backdrop",
                "Black & White Alpha Matte",
            ],
            key="bg_mode",
            help="Choose between transparent alpha cutout, solid backdrop, DSLR bokeh blur, custom background image, or alpha matte.",
        )
        format_col.selectbox(
            "Export format",
            ["PNG", "WEBP", "JPEG"],
            key="bg_format",
            index=0,
            help="PNG and WebP support full alpha transparency. JPEG flattens with background.",
        )

        current_mode = st.session_state.get("bg_mode", "Transparent Cutout")

        # Mode Specific Settings
        if current_mode == "Solid Studio Color":
            st.markdown("<p style='font-weight:600; font-size:0.85rem; margin-top:0.4rem'>🎨 Studio Color Palette</p>", unsafe_allow_html=True)
            chip_cols = st.columns(len(STUDIO_PALETTES))
            for idx, (p_name, p_hex) in enumerate(STUDIO_PALETTES.items()):
                if chip_cols[idx].button(p_name, key=f"chip_{p_name}", width="stretch"):
                    st.session_state["bg_color_picker"] = p_hex
                    st.rerun()

            c_cols = st.columns([1, 2])
            c_cols[0].color_picker("Custom Backdrop Color", value=st.session_state.get("bg_color_picker", "#FFFFFF"), key="bg_color_picker")
            c_cols[1].caption("Pick any custom RGB/HEX shade for the solid background.")

        elif current_mode == "Portrait Bokeh Blur":
            st.slider(
                "DSLR Lens Blur Radius (px)",
                min_value=5, max_value=60, value=int(st.session_state.get("bg_blur_radius", 25)), step=5,
                key="bg_blur_radius",
                help="Higher radius produces a deeper depth-of-field DSLR bokeh blur behind the sharp subject.",
            )

        elif current_mode == "Custom Image Backdrop":
            st.caption("Upload a scenic background, office, or texture image to place behind your cutout subject:")
            bg_file = st.file_uploader(
                "Upload Background Image",
                type=["jpg", "jpeg", "png", "webp"],
                key="bg_custom_uploader",
            )
            if bg_file is not None:
                st.session_state["bg_custom_image_bytes"] = bg_file.getvalue()
                st.success(f"Loaded background image: {bg_file.name}")

        # Engine & Matting Section
        st.markdown("<hr style='margin:0.8rem 0'>", unsafe_allow_html=True)
        eng_col1, eng_col2 = st.columns(2)

        eng_col1.selectbox(
            "Extraction Engine",
            [
                "Auto (Neural AI if available)",
                "AI Neural Network (rembg)",
                "Smart Perceptual Keyer (Built-in)",
                "Chroma Keyer (Green/Blue Screen)",
            ],
            key="bg_engine",
            help="Select between deep learning neural AI matting or zero-dependency smart color/edge keyers.",
        )

        if has_ai_remover():
            model_keys = list(AI_MODELS.keys())
            model_labels = list(AI_MODELS.values())
            curr_model = st.session_state.get("bg_ai_model", "u2net")
            model_idx = model_keys.index(curr_model) if curr_model in model_keys else 0
            
            selected_label = eng_col2.selectbox(
                "AI Neural Model Architecture",
                model_labels,
                index=model_idx,
                help="U2Net Human Seg is tuned for people and portraits. ISNet provides ultra-fine edge precision.",
            )
            # Find matching key
            for k, v in AI_MODELS.items():
                if v == selected_label:
                    st.session_state["bg_ai_model"] = k
                    break
        else:
            eng_col2.markdown(
                "<div style='background:rgba(99,102,241,0.08); padding:0.6rem 0.8rem; border-radius:6px; font-size:0.85rem'>"
                "✨ <strong>Want Deep Learning AI Matting?</strong><br>"
                "Run <code>pip install rembg onnxruntime</code> in your environment for automated human & product segmentation."
                "</div>",
                unsafe_allow_html=True,
            )

        # Advanced Refinement Expander
        with st.expander("🛠️ Advanced Edge & Matting Refinement (Hair, Feathering, Despill)", expanded=False):
            ref_col1, ref_col2 = st.columns(2)
            
            ref_col1.slider(
                "Tolerance sensitivity",
                min_value=5, max_value=90, value=int(st.session_state.get("bg_tolerance", 35)), step=5,
                key="bg_tolerance",
                help="Sensitivity of color separation from the backdrop.",
            )
            ref_col2.slider(
                "Edge softness (feather)",
                min_value=0, max_value=8, value=int(st.session_state.get("bg_feather", 2)), step=1,
                key="bg_feather",
                help="Blurs boundary alpha slightly for smooth anti-aliased cutout edges.",
            )

            tog_col1, tog_col2 = st.columns(2)
            tog_col1.checkbox(
                "Defringe / Despill halo removal",
                value=bool(st.session_state.get("bg_defringe", True)),
                key="bg_defringe",
                help="Neutralizes background color reflections around semi-transparent edges.",
            )
            tog_col2.checkbox(
                "Clean stray pixel islands (Post-process mask)",
                value=bool(st.session_state.get("bg_post_process", True)),
                key="bg_post_process",
                help="Removes isolated background noise speckles and fills tiny holes.",
            )

            if has_ai_remover():
                st.checkbox(
                    "Enable Fine-Detail Alpha Matting (Hair / Fur / Translucent fabric)",
                    value=bool(st.session_state.get("bg_alpha_matting", False)),
                    key="bg_alpha_matting",
                    help="Uses trimap erosion & confidence thresholds for fine strands of hair.",
                )
                if st.session_state.get("bg_alpha_matting"):
                    am_col1, am_col2, am_col3 = st.columns(3)
                    am_col1.number_input("Foreground Threshold", 100, 255, 240, step=5, key="bg_af_thresh")
                    am_col2.number_input("Background Threshold", 0, 100, 10, step=5, key="bg_ab_thresh")
                    am_col3.number_input("Erode Kernel Size", 1, 40, 10, step=1, key="bg_erode_size")

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
