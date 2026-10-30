"""Passport & Stamp Size Photo Studio View.

Generates official 300 DPI Passport and Stamp photos with AI face framing,
studio backdrop replacement, and printable 4R multi-photo sheets.
"""

from __future__ import annotations

import streamlit as st

from components.results import record_result
from components.upload import render_image_grid, render_uploader
from core.passport_studio import (
    OFFICIAL_BACKDROPS,
    PASSPORT_PRESETS,
    generate_passport_photo,
)
from utils.file_utils import format_bytes


def _on_remove(image_id: str) -> None:
    uploads: list = st.session_state.get("ps_uploads", [])
    st.session_state["ps_uploads"] = [u for u in uploads if u.id != image_id]
    st.session_state.get("ps_previews", set()).discard(image_id)
    st.session_state.get("ps_results", {}).pop(image_id, None)


def _apply_preset(preset_key: str) -> None:
    st.session_state["ps_preset"] = preset_key
    if "stamp" in preset_key:
        st.session_state["ps_sheet_layout"] = "12_copies"
    else:
        st.session_state["ps_sheet_layout"] = "6_copies"


def _get_passport_params() -> dict:
    preset_key = st.session_state.get("ps_preset", "passport_bd_global")
    bg_mode = st.session_state.get("ps_bg_mode", "white")
    custom_bg = st.session_state.get("ps_custom_bg", "#FFFFFF")
    auto_face = bool(st.session_state.get("ps_auto_face", True))
    zoom = float(st.session_state.get("ps_zoom", 1.0))
    offset_y = float(st.session_state.get("ps_offset_y", 0.0))
    offset_x = float(st.session_state.get("ps_offset_x", 0.0))
    border = bool(st.session_state.get("ps_border", True))
    sheet_layout = st.session_state.get("ps_sheet_layout", "6_copies")
    fmt = st.session_state.get("ps_format", "JPEG").lower()
    quality = int(st.session_state.get("ps_quality", 95))

    custom_w_mm = float(st.session_state.get("ps_custom_w_mm", 35.0))
    custom_h_mm = float(st.session_state.get("ps_custom_h_mm", 45.0))
    # 300 DPI: px = mm * 300 / 25.4
    custom_w_px = int(custom_w_mm * 300 / 25.4)
    custom_h_px = int(custom_h_mm * 300 / 25.4)

    return {
        "preset_key": preset_key,
        "custom_w_px": custom_w_px,
        "custom_h_px": custom_h_px,
        "custom_w_mm": custom_w_mm,
        "custom_h_mm": custom_h_mm,
        "bg_mode": bg_mode,
        "custom_bg_hex": custom_bg,
        "auto_face_framing": auto_face,
        "zoom": zoom,
        "offset_y": offset_y,
        "offset_x": offset_x,
        "add_border": border,
        "sheet_layout": sheet_layout,
        "output_format": fmt,
        "quality": quality,
    }


def _on_generate_all() -> None:
    uploads: list = st.session_state.get("ps_uploads", [])
    if not uploads:
        return
    params = _get_passport_params()

    progress = st.progress(0.0, text="Creating passport photos…")
    status = st.empty()
    results: dict = st.session_state.setdefault("ps_results", {})

    for index, upload in enumerate(uploads, start=1):
        status.markdown(f"**Processing {index} of {len(uploads)}** — {upload.filename}")
        progress.progress((index - 1) / len(uploads), text=f"Framing {index}/{len(uploads)}")
        result = generate_passport_photo(
            upload.data,
            filename=upload.filename,
            image_id=upload.id,
            **params,
        )
        results[upload.id] = result

    succeeded = sum(1 for u in uploads if results.get(u.id) and results[u.id].status == "success")
    progress.progress(1.0, text=f"✅ Passport photo generation complete — {succeeded} of {len(uploads)} ready.")
    status.empty()


def _on_generate_single(image_id: str) -> None:
    uploads: list = st.session_state.get("ps_uploads", [])
    upload = next((u for u in uploads if u.id == image_id), None)
    if upload is None:
        return
    params = _get_passport_params()
    result = generate_passport_photo(
        upload.data,
        filename=upload.filename,
        image_id=upload.id,
        **params,
    )
    st.session_state.setdefault("ps_results", {})[upload.id] = result


def render() -> None:
    st.markdown(
        "<div class='opt-section-title' style='margin-top:0.2rem'>📸 Passport & Stamp Size Photo Studio</div>"
        "<div class='opt-section-sub'>Convert any photo into official 300 DPI Passport and Stamp sizes with smart face framing, "
        "studio backdrops, and ready-to-print 4R photo sheets.</div>",
        unsafe_allow_html=True,
    )

    # 1-Click Quick Presets Bar
    st.markdown("<p style='font-weight:600; font-size:0.9rem; margin-bottom:0.4rem'>⚡ Quick Standard Presets</p>", unsafe_allow_html=True)
    p_cols = st.columns(4)
    if p_cols[0].button("🇧🇩 Passport (35×45 mm)", key="pbtn_bd", width="stretch"):
        _apply_preset("passport_bd_global")
        st.rerun()
    if p_cols[1].button("🔖 Stamp Size (20×25 mm)", key="pbtn_stamp", width="stretch"):
        _apply_preset("stamp_standard")
        st.rerun()
    if p_cols[2].button("🇺🇸 US Visa / 2×2 inch", key="pbtn_visa", width="stretch"):
        _apply_preset("passport_us_visa")
        st.rerun()
    if p_cols[3].button("🏷️ Stamp Large (25×30 mm)", key="pbtn_stamplay", width="stretch"):
        _apply_preset("stamp_large")
        st.rerun()

    cfg_max_mb = int(st.session_state.get("cfg_max_mb", 20))
    cfg_max_mp = int(st.session_state.get("cfg_max_mp", 60))
    uploads = render_uploader(
        cache_key="ps", uploads_key="ps_uploads",
        max_file_mb=cfg_max_mb, max_pixels=cfg_max_mp * 1_000_000,
    )

    with st.container(border=True):
        st.markdown("### ⚙️ Photo dimensions & studio configuration")

        preset_options = list(PASSPORT_PRESETS.keys()) + ["custom"]
        preset_labels = [PASSPORT_PRESETS[k].name for k in PASSPORT_PRESETS] + ["⚙️ Custom Dimensions (mm)"]

        curr_preset = st.session_state.get("ps_preset", "passport_bd_global")
        preset_idx = preset_options.index(curr_preset) if curr_preset in preset_options else 0

        p_col1, p_col2 = st.columns([1.5, 1])
        selected_lbl = p_col1.selectbox("Standard Size Preset", preset_labels, index=preset_idx)
        st.session_state["ps_preset"] = preset_options[preset_labels.index(selected_lbl)]

        active_preset_key = st.session_state["ps_preset"]
        if active_preset_key in PASSPORT_PRESETS:
            preset_obj = PASSPORT_PRESETS[active_preset_key]
            p_col2.markdown(
                f"<div style='background:rgba(99,102,241,0.08); padding:0.55rem 0.8rem; border-radius:6px; font-size:0.85rem; margin-top:20px;'>"
                f"📐 <strong>{preset_obj.width_mm} × {preset_obj.height_mm} mm</strong> ({preset_obj.width_px} × {preset_obj.height_px} px @ 300 DPI)<br>"
                f"<span style='color:#666;'>{preset_obj.description}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            cust_c1, cust_c2 = p_col2.columns(2)
            cust_c1.number_input("Width (mm)", min_value=10.0, max_value=200.0, value=35.0, step=1.0, key="ps_custom_w_mm")
            cust_c2.number_input("Height (mm)", min_value=10.0, max_value=200.0, value=45.0, step=1.0, key="ps_custom_h_mm")

        st.markdown("<hr style='margin:0.8rem 0'>", unsafe_allow_html=True)
        st.markdown("<p style='font-weight:600; font-size:0.9rem; margin-bottom:0.4rem'>🎨 Official Background Color</p>", unsafe_allow_html=True)

        bg_col1, bg_col2 = st.columns([1.5, 1])
        bg_choices = [
            ("white", "⚪ Official Pure White (Standard US / EU / Online)"),
            ("light_blue", "🔵 Passport Light Blue (Standard BD / ID / Admissions)"),
            ("govt_blue", "🔷 Govt Sky Blue (Driving License / Passports)"),
            ("gray", "🔘 Studio Soft Gray (Neutral Studio Backdrop)"),
            ("custom_color", "🎨 Custom Color"),
            ("keep_original", "🖼️ Keep Original Photo Background"),
        ]
        bg_keys = [k for k, _ in bg_choices]
        bg_lbls = [l for _, l in bg_choices]
        curr_bg_mode = st.session_state.get("ps_bg_mode", "white")
        bg_idx = bg_keys.index(curr_bg_mode) if curr_bg_mode in bg_keys else 0

        chosen_bg_lbl = bg_col1.selectbox("Select Backdrop", bg_lbls, index=bg_idx)
        st.session_state["ps_bg_mode"] = bg_keys[bg_lbls.index(chosen_bg_lbl)]

        if st.session_state["ps_bg_mode"] == "custom_color":
            bg_col2.color_picker("Pick Custom Color", value=st.session_state.get("ps_custom_bg", "#FFFFFF"), key="ps_custom_bg")
        elif st.session_state["ps_bg_mode"] != "keep_original":
            color_map = {
                "white": "#FFFFFF",
                "light_blue": OFFICIAL_BACKDROPS["Passport Light Blue"],
                "govt_blue": OFFICIAL_BACKDROPS["Govt Sky Blue"],
                "gray": OFFICIAL_BACKDROPS["Studio Soft Gray"],
            }
            display_hex = color_map.get(st.session_state["ps_bg_mode"], "#FFFFFF")
            bg_col2.markdown(
                f"<div style='display:flex; align-items:center; gap:10px; margin-top:24px;'>"
                f"<div style='width:32px; height:32px; border-radius:6px; background:{display_hex}; border:1px solid #ccc; box-shadow:0 1px 2px rgba(0,0,0,0.1);'></div>"
                f"<span style='font-weight:600; font-family:monospace;'>{display_hex}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Smart Portrait Framing & Tuning
        with st.expander("👤 Framing & Head Positioning (Zoom, Pan, Border)", expanded=True):
            st.checkbox(
                "✨ Smart AI Head Centering (Automatically frames head & upper body at official 10% headroom)",
                value=bool(st.session_state.get("ps_auto_face", True)),
                key="ps_auto_face",
            )
            sc1, sc2, sc3 = st.columns(3)
            sc1.slider("Zoom (Head Scale)", 0.6, 2.2, float(st.session_state.get("ps_zoom", 1.0)), 0.05, key="ps_zoom",
                       help="Adjust framing closer to head or wider to include shoulders.")
            sc2.slider("Vertical Pan (Up/Down)", -0.4, 0.4, float(st.session_state.get("ps_offset_y", 0.0)), 0.02, key="ps_offset_y",
                       help="Shift crop window up or down.")
            sc3.slider("Horizontal Pan (Left/Right)", -0.4, 0.4, float(st.session_state.get("ps_offset_x", 0.0)), 0.02, key="ps_offset_x",
                       help="Shift crop window left or right.")

            bc1, bc2 = st.columns(2)
            bc1.checkbox("Add 1px subtle cutting guide border", value=bool(st.session_state.get("ps_border", True)), key="ps_border",
                         help="Draws a subtle 1px border so you can easily cut the printed photo with scissors.")

        # Print Sheet & Output Settings
        with st.expander("🖨️ Printable Multi-Photo Sheet Layout (4R Photo Paper)", expanded=False):
            st.caption("Generate a standard 4×6 inch (4R) sheet with multiple copies ready to print at any studio or lab:")
            sheet_options = [
                ("single", "Single Photo Only (For online submissions / web forms)"),
                ("4_copies", "4 Copies on 4R Sheet (2 × 2 grid)"),
                ("6_copies", "6 Copies on 4R Sheet (2 × 3 grid — Standard Bangladesh studio layout)"),
                ("8_copies", "8 Copies on 4R Sheet (2 × 4 grid)"),
                ("12_copies", "12 Copies on 4R Sheet (3 × 4 grid — Ideal for Stamp size)"),
            ]
            sh_keys = [k for k, _ in sheet_options]
            sh_lbls = [l for _, l in sheet_options]
            curr_sh = st.session_state.get("ps_sheet_layout", "6_copies")
            sh_idx = sh_keys.index(curr_sh) if curr_sh in sh_keys else 2
            selected_sh_lbl = st.selectbox("Multi-Photo Sheet Option", sh_lbls, index=sh_idx)
            st.session_state["ps_sheet_layout"] = sh_keys[sh_lbls.index(selected_sh_lbl)]

            fmt_c1, fmt_c2 = st.columns(2)
            fmt_c1.selectbox("Export Format", ["JPEG", "PNG"], key="ps_format", index=0)
            fmt_c2.slider("Image Quality", 85, 100, 95, key="ps_quality")

    if not uploads:
        st.info("👆 **Add images above** to create perfectly sized Passport & Stamp photos.")
        st.button("📸 Generate Passport / Stamp Photo", type="primary", width="stretch", disabled=True)
        return

    render_image_grid(
        uploads,
        results_key="ps_results",
        previews_key="ps_previews",
        on_remove=_on_remove,
        on_optimize=_on_generate_single,
        optimize_label="Make Passport",
    )

    st.button(
        f"📸 Generate Passport / Stamp Photo for {len(uploads)} image{'s' if len(uploads) != 1 else ''}",
        type="primary", width="stretch", on_click=_on_generate_all,
    )

    # Render Results Dashboard
    live_ids = {u.id for u in uploads}
    results: dict = st.session_state.get("ps_results", {})
    st.session_state["ps_results"] = {k: v for k, v in results.items() if k in live_ids}
    ordered = [st.session_state["ps_results"][u.id] for u in uploads if u.id in st.session_state["ps_results"]]

    if ordered:
        st.markdown("<hr style='margin:1.2rem 0'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='opt-section-title'>🖼️ Generated Passport & Stamp Photos</div>"
            "<div class='opt-section-sub'>Each image is rendered at true 300 DPI with exact millimeter dimensions.</div>",
            unsafe_allow_html=True,
        )

        for res in ordered:
            if res.status != "success":
                st.error(f"❌ Failed to process {res.original_filename}: {res.error}")
                continue

            with st.container(border=True):
                col_left, col_mid, col_right = st.columns([1, 1.2, 1.2], vertical_alignment="center")

                with col_left:
                    st.markdown("**Original Photo**")
                    if res.original_thumb:
                        st.image(res.original_thumb, width="stretch")
                    st.caption(f"{res.original_filename} · {format_bytes(res.original_size)}")

                with col_mid:
                    st.markdown(f"**{res.preset_name}**")
                    st.image(res.data, width="stretch")
                    st.markdown(
                        f"<div class='opt-caption' style='margin-top:6px;'>"
                        f"📏 <strong>{res.width_mm} × {res.height_mm} mm</strong> ({res.width_px} × {res.height_px} px @ {res.dpi} DPI)<br>"
                        f"📦 {format_bytes(res.optimized_size)} · ⚡ {res.processing_time * 1000:.0f} ms"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.download_button(
                        f"⬇ Download Single Photo ({res.width_mm:.0f}×{res.height_mm:.0f}mm)",
                        data=res.data,
                        file_name=res.output_filename,
                        mime="image/jpeg",
                        key=f"dl_single_{res.image_id}",
                        type="primary",
                        width="stretch",
                    )

                with col_right:
                    if res.sheet_data:
                        st.markdown(f"**🖨️ 4R Printable Sheet ({res.sheet_copies} Copies)**")
                        st.image(res.sheet_data, width="stretch")
                        st.caption(f"Standard 4×6 inch (4R) sheet with cutting crosshairs · {format_bytes(len(res.sheet_data))}")
                        st.download_button(
                            f"🖨️ Download 4R Print Sheet ({res.sheet_copies} Photos)",
                            data=res.sheet_data,
                            file_name=res.sheet_filename,
                            mime="image/jpeg",
                            key=f"dl_sheet_{res.image_id}",
                            width="stretch",
                        )
                    else:
                        st.info("ℹ️ Single photo mode selected. Enable 'Multi-Photo Sheet' in settings if you want to print 4, 6, 8, or 12 copies on a single 4×6 inch page.")
