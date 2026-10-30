"""Background Remover view: professional AI neural matting, smart chroma keying,
studio solid backdrop, aesthetic gradients, bokeh blur, and fine edge hair feathering.
"""

from __future__ import annotations

import streamlit as st

from components.results import record_result, render_dashboard
from components.upload import render_image_grid, render_uploader
from core.bg_remover import (
    AI_MODELS,
    GRADIENT_PRESETS,
    STUDIO_PALETTES,
    has_ai_remover,
    remove_background,
)

PALETTE_CATEGORIES = {
    "Minimal & Studio": [
        ("Studio White", "#FFFFFF"),
        ("Soft Gray", "#F3F4F6"),
        ("E-Commerce Cream", "#FDFBF7"),
        ("Warm Sand", "#F5EFEB"),
        ("Slate Charcoal", "#1E293B"),
        ("Midnight Blue", "#0F172A"),
        ("Onyx Black", "#0B0F19"),
        ("Cool Steel", "#94A3B8"),
    ],
    "Soft Pastels": [
        ("Rose Pink", "#FFE4E6"),
        ("Pastel Purple", "#EDE9FE"),
        ("Sky Azure", "#E0F2FE"),
        ("Mint Sage", "#ECFDF5"),
        ("Peach Sorbet", "#FFEDD5"),
        ("Lemon Butter", "#FEF9C3"),
        ("Lavender Dream", "#F3E8FF"),
    ],
    "Vibrant & Bold": [
        ("Electric Indigo", "#4F46E5"),
        ("Vibrant Crimson", "#E11D48"),
        ("Emerald Forest", "#059669"),
        ("Warm Amber", "#D97706"),
        ("Ocean Sapphire", "#0284C7"),
        ("Royal Magenta", "#9333EA"),
    ],
    "Chroma Screens": [
        ("Chroma Green", "#00FF00"),
        ("Chroma Blue", "#0000FF"),
    ],
}


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
        "Aesthetic Gradient": "gradient",
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
    grad_start = st.session_state.get("bg_grad_start", "#FF512F")
    grad_end = st.session_state.get("bg_grad_end", "#DD2476")
    grad_style = st.session_state.get("bg_grad_style", "vertical")

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
        "gradient_start": grad_start,
        "gradient_end": grad_end,
        "gradient_style": grad_style,
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
    elif preset_name == "studio_color":
        st.session_state["bg_mode"] = "Solid Studio Color"
        st.session_state["bg_color_picker"] = "#FFFFFF"
        st.session_state["bg_engine"] = "Auto (Neural AI if available)"
        st.session_state["bg_format"] = "PNG"
        st.session_state["bg_defringe"] = True
    elif preset_name == "gradient":
        st.session_state["bg_mode"] = "Aesthetic Gradient"
        st.session_state["bg_grad_start"] = "#FF512F"
        st.session_state["bg_grad_end"] = "#DD2476"
        st.session_state["bg_grad_style"] = "vertical"
        st.session_state["bg_engine"] = "Auto (Neural AI if available)"
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


def _instant_recolor(upload, result, new_mode: str, **kwargs) -> None:
    """Instant composite on already extracted cutout (<50ms)."""
    if not result or not getattr(result, "cutout_data", b""):
        return

    params = _get_bg_params()
    params.update(kwargs)
    params["mode"] = new_mode

    new_res = remove_background(
        upload.data,
        filename=upload.filename,
        image_id=upload.id,
        cached_cutout_bytes=result.cutout_data,
        **params,
    )
    record_result(new_res, "bg_results")


def render() -> None:
    st.markdown(
        "<div class='opt-section-title' style='margin-top:0.2rem'>🪄 AI & Professional Background Studio</div>"
        "<div class='opt-section-sub'>Extract clean subjects with deep learning AI matting, "
        "and customize behind them with studio colors, modern aesthetic gradients, or DSLR bokeh blur.</div>",
        unsafe_allow_html=True,
    )

    # 1-Click Workflow Presets Bar
    st.markdown("<p style='font-weight:600; font-size:0.9rem; margin-bottom:0.4rem'>⚡ Quick Workflow Presets</p>", unsafe_allow_html=True)
    p_cols = st.columns(8)
    if p_cols[0].button("✨ Auto AI", key="preset_auto", width="stretch"):
        _apply_preset("auto_ai")
        st.rerun()
    if p_cols[1].button("👤 Portrait", key="preset_portrait", width="stretch"):
        _apply_preset("portrait")
        st.rerun()
    if p_cols[2].button("🎨 Studio Color", key="preset_studio_color", width="stretch"):
        _apply_preset("studio_color")
        st.rerun()
    if p_cols[3].button("🌈 Gradient", key="preset_gradient", width="stretch"):
        _apply_preset("gradient")
        st.rerun()
    if p_cols[4].button("📦 E-Commerce", key="preset_ecom", width="stretch"):
        _apply_preset("ecommerce")
        st.rerun()
    if p_cols[5].button("📸 Bokeh Blur", key="preset_bokeh", width="stretch"):
        _apply_preset("bokeh")
        st.rerun()
    if p_cols[6].button("🎬 Green Screen", key="preset_chroma", width="stretch"):
        _apply_preset("chroma")
        st.rerun()
    if p_cols[7].button("✍️ Graphic/Logo", key="preset_logo", width="stretch"):
        _apply_preset("logo")
        st.rerun()

    cfg_max_mb = int(st.session_state.get("cfg_max_mb", 20))
    cfg_max_mp = int(st.session_state.get("cfg_max_mp", 60))
    uploads = render_uploader(
        cache_key="bg", uploads_key="bg_uploads",
        max_file_mb=cfg_max_mb, max_pixels=cfg_max_mp * 1_000_000,
    )

    with st.container(border=True):
        st.markdown("### ⚙️ Background styling & extraction configuration")

        mode_col, format_col = st.columns([1.4, 1])
        mode_col.selectbox(
            "Backdrop Style",
            [
                "Transparent Cutout",
                "Solid Studio Color",
                "Aesthetic Gradient",
                "Portrait Bokeh Blur",
                "Custom Image Backdrop",
                "Black & White Alpha Matte",
            ],
            key="bg_mode",
            help="Choose between transparent alpha cutout, solid backdrop color, smooth aesthetic gradient, DSLR bokeh blur, custom background image, or alpha matte.",
        )
        format_col.selectbox(
            "Export format",
            ["PNG", "WEBP", "JPEG"],
            key="bg_format",
            index=0,
            help="PNG and WebP support full transparency. JPEG flattens with background.",
        )

        current_mode = st.session_state.get("bg_mode", "Transparent Cutout")

        # 1. Solid Studio Color Backdrop
        if current_mode == "Solid Studio Color":
            st.markdown("<p style='font-weight:600; font-size:0.9rem; margin-top:0.4rem'>🎨 Choose Background Color</p>", unsafe_allow_html=True)

            cat_tabs = st.tabs(list(PALETTE_CATEGORIES.keys()))
            for tab_idx, (cat_name, colors) in enumerate(PALETTE_CATEGORIES.items()):
                with cat_tabs[tab_idx]:
                    cols = st.columns(len(colors))
                    for c_idx, (c_name, c_hex) in enumerate(colors):
                        if cols[c_idx].button(
                            f"{c_name}",
                            key=f"palette_{cat_name}_{c_name}",
                            width="stretch",
                        ):
                            st.session_state["bg_color_picker"] = c_hex
                            st.rerun()

            c_cols = st.columns([1, 2])
            curr_col = st.session_state.get("bg_color_picker", "#FFFFFF")
            new_color = c_cols[0].color_picker("Custom Backdrop Color", value=curr_col, key="bg_color_picker")
            c_cols[1].markdown(
                f"<div style='display:flex; align-items:center; gap:12px; margin-top:22px;'>"
                f"<div style='width:36px; height:36px; border-radius:6px; background:{new_color}; border:1px solid #ccc; box-shadow:0 1px 3px rgba(0,0,0,0.1);'></div>"
                f"<span style='font-family:monospace; font-size:0.95rem; font-weight:600;'>{new_color.upper()}</span>"
                f"<span style='color:#666; font-size:0.85rem;'>— Pick any exact RGB or HEX shade.</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # 2. Aesthetic Gradient Backdrop
        elif current_mode == "Aesthetic Gradient":
            st.markdown("<p style='font-weight:600; font-size:0.9rem; margin-top:0.4rem'>🌈 Aesthetic Gradient Presets</p>", unsafe_allow_html=True)
            g_cols = st.columns(5)
            preset_items = list(GRADIENT_PRESETS.items())
            for idx, (g_name, (g_c1, g_c2, g_style)) in enumerate(preset_items[:5]):
                if g_cols[idx].button(g_name, key=f"gpreset_top_{g_name}", width="stretch"):
                    st.session_state["bg_grad_start"] = g_c1
                    st.session_state["bg_grad_end"] = g_c2
                    st.session_state["bg_grad_style"] = g_style
                    st.rerun()

            g_cols2 = st.columns(5)
            for idx, (g_name, (g_c1, g_c2, g_style)) in enumerate(preset_items[5:]):
                if g_cols2[idx].button(g_name, key=f"gpreset_bot_{g_name}", width="stretch"):
                    st.session_state["bg_grad_start"] = g_c1
                    st.session_state["bg_grad_end"] = g_c2
                    st.session_state["bg_grad_style"] = g_style
                    st.rerun()

            st.markdown("<p style='font-weight:600; font-size:0.85rem; margin-top:0.8rem'>🛠️ Custom Gradient Tuning</p>", unsafe_allow_html=True)
            gc1, gc2, gc3 = st.columns([1, 1, 1.2])
            g_start = gc1.color_picker("Start Color", value=st.session_state.get("bg_grad_start", "#FF512F"), key="bg_grad_start")
            g_end = gc2.color_picker("End Color", value=st.session_state.get("bg_grad_end", "#DD2476"), key="bg_grad_end")

            style_options = ["vertical", "horizontal", "diagonal", "radial"]
            style_labels = ["Vertical (Top → Bottom)", "Horizontal (Left → Right)", "Diagonal (Corner → Corner)", "Radial Spotlight (Center Glow)"]
            curr_style = st.session_state.get("bg_grad_style", "vertical")
            curr_idx = style_options.index(curr_style) if curr_style in style_options else 0
            selected_style_lbl = gc3.selectbox("Gradient Flow", style_labels, index=curr_idx)
            st.session_state["bg_grad_style"] = style_options[style_labels.index(selected_style_lbl)]

            # Live Gradient Preview Box
            css_direction = "to bottom"
            if "horizontal" in st.session_state["bg_grad_style"]:
                css_direction = "to right"
            elif "diagonal" in st.session_state["bg_grad_style"]:
                css_direction = "to bottom right"
            elif "radial" in st.session_state["bg_grad_style"]:
                css_bg = f"radial-gradient(circle at center, {g_start} 0%, {g_end} 100%)"
            else:
                css_bg = f"linear-gradient({css_direction}, {g_start}, {g_end})"

            if "radial" not in st.session_state["bg_grad_style"]:
                css_bg = f"linear-gradient({css_direction}, {g_start}, {g_end})"

            st.markdown(
                f"<div style='height:42px; border-radius:8px; margin-top:6px; background:{css_bg}; "
                f"border:1px solid rgba(0,0,0,0.15); display:flex; align-items:center; justify-content:center; color:#fff; font-weight:600; text-shadow:0 1px 3px rgba(0,0,0,0.5); font-size:0.85rem'>"
                f"Gradient Preview ({g_start} → {g_end})"
                f"</div>",
                unsafe_allow_html=True,
            )

        # 3. Portrait Bokeh Blur
        elif current_mode == "Portrait Bokeh Blur":
            st.slider(
                "DSLR Lens Blur Radius (px)",
                min_value=5, max_value=60, value=int(st.session_state.get("bg_blur_radius", 25)), step=5,
                key="bg_blur_radius",
                help="Higher radius produces a deeper depth-of-field DSLR bokeh blur behind the sharp subject.",
            )

        # 4. Custom Image Backdrop
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

        # Engine & AI Matting Section
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

        selected_engine = st.session_state.get("bg_engine", "Auto (Neural AI if available)")

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
            for k, v in AI_MODELS.items():
                if v == selected_label:
                    st.session_state["bg_ai_model"] = k
                    break

            st.markdown(
                "<div style='background:rgba(16,185,129,0.08); border-left:4px solid #10B981; padding:0.5rem 0.8rem; border-radius:4px; font-size:0.85rem; margin-top:0.4rem'>"
                "🟢 <strong>Deep Learning AI Matting Active:</strong> Intelligently segments people, clothing, hair, and complex objects without inverted or washed-out artifacts."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            eng_col2.markdown(
                "<div style='background:rgba(99,102,241,0.08); padding:0.6rem 0.8rem; border-radius:6px; font-size:0.85rem'>"
                "✨ <strong>Want Deep Learning AI Matting?</strong><br>"
                "Run <code>pip install rembg onnxruntime</code> in your environment for automated human & product segmentation."
                "</div>",
                unsafe_allow_html=True,
            )

        if "Smart Perceptual" in selected_engine:
            st.warning(
                "⚠️ **Smart Perceptual Keyer Notice:** The built-in keyer uses naive color difference and only works on simple solid/white studio backdrops. "
                "For photos with people, outdoors, or complex scenes, keep **Auto** or **AI Neural Network** enabled to prevent inverted/negative artifacts."
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
        st.info("👆 **Add images above** to extract subjects or change backgrounds.")
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

    # Instant Backdrop Color Switcher Studio for Processed Cutouts
    successful_cutouts = [
        (u, st.session_state["bg_results"][u.id])
        for u in uploads
        if u.id in st.session_state["bg_results"]
        and st.session_state["bg_results"][u.id].status == "success"
        and getattr(st.session_state["bg_results"][u.id], "cutout_data", b"")
    ]

    if successful_cutouts:
        with st.container(border=True):
            st.markdown("### 🎨 Instant Backdrop Re-Coloring Studio")
            st.caption("Change colors or gradients on your extracted subject **instantly** without waiting for AI to re-process!")

            pick_u, pick_res = successful_cutouts[0]
            if len(successful_cutouts) > 1:
                target_names = [u.filename for u, _ in successful_cutouts]
                chosen_fn = st.selectbox("Select Image to re-color", target_names, key="recolor_target_fn")
                match_pair = next(((u, r) for u, r in successful_cutouts if u.filename == chosen_fn), None)
                if match_pair:
                    pick_u, pick_res = match_pair

            rc_col1, rc_col2, rc_col3 = st.columns([1, 1, 1])

            with rc_col1:
                st.markdown("**1. Transparent Cutout**")
                if st.button("⚪ Make Transparent", key="rc_btn_trans", width="stretch"):
                    _instant_recolor(pick_u, pick_res, "transparent")
                    st.rerun()

            with rc_col2:
                st.markdown("**2. Solid Colors**")
                rc_color = st.color_picker("Pick Color", value=st.session_state.get("bg_color_picker", "#FFFFFF"), key="rc_solid_picker")
                if st.button("✨ Apply Solid Color", key="rc_btn_solid", width="stretch"):
                    _instant_recolor(pick_u, pick_res, "color", bg_color=rc_color)
                    st.rerun()

            with rc_col3:
                st.markdown("**3. Modern Gradient**")
                g_choice = st.selectbox("Preset Gradient", list(GRADIENT_PRESETS.keys()), key="rc_grad_preset_choice")
                c1, c2, sty = GRADIENT_PRESETS[g_choice]
                if st.button(f"✨ Apply {g_choice}", key="rc_btn_grad", width="stretch"):
                    _instant_recolor(pick_u, pick_res, "gradient", gradient_start=c1, gradient_end=c2, gradient_style=sty)
                    st.rerun()

    render_dashboard(ordered, key_prefix="bg", zip_name="cutout-images.zip")
