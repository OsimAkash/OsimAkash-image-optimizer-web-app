"""Upload zone and image card grid shared by Optimizer / Converter / Resizer pages."""

from __future__ import annotations

import uuid
from typing import Callable

import streamlit as st

from core.analyzer import UploadedImage, analyze_image, make_thumbnail
from utils.validators import ValidationResult, validate_upload

SUPPORTED_LABEL = "JPG · JPEG · PNG · WEBP · BMP · TIFF"
UPLOADER_TYPES = ["jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif"]


def render_uploader(
    *,
    cache_key: str,
    uploads_key: str,
    max_file_mb: int,
    max_pixels: int,
    multiple: bool = True,
) -> list[UploadedImage]:
    """Render the drag-and-drop upload zone and return the validated session list.

    Validated images are cached by upload id so nothing is re-validated or
    re-decoded on reruns; removing a file in the widget removes it from the list.
    Validation failures are reported with friendly messages, never tracebacks.
    """
    st.markdown(
        "<p style='font-weight:700; font-size:1.02rem; margin-bottom:0.2rem'>"
        "Drag &amp; drop your images here</p>"
        "<p style='color:var(--muted); font-size:0.85rem; margin:0 0 0.6rem'>or click to browse</p>",
        unsafe_allow_html=True,
    )
    uploaded_files = st.file_uploader(
        "Drag & drop your images here, or click to browse",
        type=UPLOADER_TYPES,
        accept_multiple_files=multiple,
        label_visibility="collapsed",
        key=f"uploader_{cache_key}",
    )

    current = list(uploaded_files or [])
    current_ids = [str(getattr(f, "id", None) or f"{f.name}:{f.size}") for f in current]
    ids_key = f"{cache_key}_ids"
    cache: dict = st.session_state.setdefault(f"{cache_key}_cache", {})

    if st.session_state.get(ids_key) != current_ids:
        # The set of files in the uploader changed — validate once and rebuild the list.
        uploads: list[UploadedImage] = []
        errors: list[tuple[str, str]] = []
        for file_like, file_id in zip(current, current_ids):
            entry = cache.get(file_id)
            if entry is None:
                entry = _validate_and_wrap(file_like, file_id, max_file_mb, max_pixels)
                cache[file_id] = entry
            if isinstance(entry, UploadedImage):
                uploads.append(entry)
            else:
                errors.append(entry)

        # Keep the cache bounded so long sessions don't grow without limit.
        if len(cache) > 300:
            live = set(current_ids)
            st.session_state[f"{cache_key}_cache"] = {k: v for k, v in cache.items() if k in live}

        st.session_state[ids_key] = current_ids
        st.session_state[uploads_key] = uploads
        st.session_state[f"{cache_key}_errors"] = errors
    else:
        # Nothing changed in the uploader — reuse the session list untouched.
        uploads = st.session_state.get(uploads_key, [])
        errors = st.session_state.get(f"{cache_key}_errors", [])

    if errors:
        with st.container(border=True):
            st.markdown(f"⚠️ **{len(errors)} file(s) could not be added**")
            for name, message in errors:
                st.markdown(f"<div class='opt-meta-line'>📄 <strong>{name}</strong> — {message}</div>",
                            unsafe_allow_html=True)

    if not current:
        st.caption(f"Supported formats: {SUPPORTED_LABEL} — up to {max_file_mb} MB per image.")
    return uploads


def _validate_and_wrap(file_like, file_id: str, max_file_mb: int, max_pixels: int):
    """Validate one upload and either build an :class:`UploadedImage` or an error entry."""
    from utils.file_utils import sanitize_filename

    validation: ValidationResult = validate_upload(
        file_like, max_file_size=max_file_mb * 1024 * 1024, max_pixels=max_pixels
    )
    display_name = sanitize_filename(getattr(file_like, "name", "") or "image")
    if not validation.ok:
        return (display_name, validation.message)

    try:
        info = analyze_image(validation.data, filename=display_name)
    except Exception:  # noqa: BLE001 - validators already screened; belt and braces
        return (display_name, "Unable to read this image. The file may be corrupted.")

    return UploadedImage(
        id=file_id or uuid.uuid4().hex,
        filename=display_name,
        data=validation.data,
        thumb=make_thumbnail(validation.data),
        info=info,
        note=validation.note,
    )


def render_image_grid(
    uploads: list[UploadedImage],
    *,
    results_key: str,
    previews_key: str,
    on_remove: Callable[[str], None],
    on_optimize: Callable[[str], None] | None = None,
    optimize_label: str = "Optimize",
) -> None:
    """Render responsive cards with thumbnail, metadata and per-image actions."""
    if not uploads:
        return

    st.markdown(
        f"<div class='opt-section-title'>📷 Your images</div>"
        f"<div class='opt-section-sub'>{len(uploads)} image(s) ready — remove, preview or process each one.</div>",
        unsafe_allow_html=True,
    )

    results: dict = st.session_state.get(results_key, {})
    previews: set = st.session_state.setdefault(previews_key, set())
    columns_per_row = 3

    for row_start in range(0, len(uploads), columns_per_row):
        row = uploads[row_start:row_start + columns_per_row]
        cols = st.columns(columns_per_row, gap="medium")
        for col, upload in zip(cols, row):
            with col:
                _render_card(upload, results, previews, on_remove, on_optimize, optimize_label,
                             results_key, previews_key)


def _render_card(
    upload: UploadedImage,
    results: dict,
    previews: set,
    on_remove,
    on_optimize,
    optimize_label: str,
    results_key: str,
    previews_key: str,
) -> None:
    with st.container(border=True):
        preview_data = upload.thumb or upload.data
        if preview_data:
            st.image(preview_data, width="stretch")
        alpha_pill = '<span class="opt-pill-green opt-pill">ALPHA</span>' if upload.has_alpha else ""
        st.markdown(
            f"<div class='opt-file-name' title='{upload.filename}'>{upload.filename}</div>"
            f"<span class='opt-pill'>{upload.format}</span>{alpha_pill}"
            f"<div class='opt-meta-line'>"
            f"{upload.width} × {upload.height} px · {upload.mode}<br>"
            f"Original size: <strong>{_fmt(upload.size)}</strong></div>",
            unsafe_allow_html=True,
        )

        button_cols = st.columns(3)
        button_cols[0].button("Remove", key=f"rm_{results_key}_{upload.id}",
                              on_click=on_remove, args=(upload.id,), width="stretch")
        preview_label = "Hide" if upload.id in previews else "Preview"
        button_cols[1].button(preview_label, key=f"pv_{results_key}_{upload.id}",
                              on_click=_toggle_preview, args=(previews_key, upload.id),
                              width="stretch")
        if on_optimize is not None:
            button_cols[2].button(optimize_label, key=f"go_{results_key}_{upload.id}",
                                  on_click=on_optimize, args=(upload.id,),
                                  type="primary", width="stretch")

        if upload.id in previews:
            with st.expander("Full preview & details", expanded=True):
                st.image(upload.data, width="stretch")
                info = upload.info
                st.caption(
                    f"{info.format} · {info.width}×{info.height} · {info.mode} · "
                    f"{info.megapixels} MP · {_fmt(info.size_bytes)}"
                )
                if info.has_alpha:
                    st.caption("Contains transparency.")
                if upload.note:
                    st.caption(f"ℹ️ {upload.note}")

        result = results.get(upload.id)
        if result is not None:
            _render_inline_result(result, results_key)


def _render_inline_result(result, results_key: str) -> None:
    if result.status == "failed":
        st.error(f"Failed: {result.error}")
        return
    saved = result.saved_percent
    size_line = f"{_fmt(result.original_size)} → <strong>{_fmt(result.optimized_size)}</strong>"
    if saved > 0:
        badge = f"<span class='opt-saved-badge'>{saved:.1f}% smaller</span>"
    elif saved < 0:
        badge = f"<span class='opt-pill' style='background:var(--danger-soft);color:var(--danger)'>{abs(saved):.1f}% larger</span>"
    else:
        badge = "<span class='opt-pill opt-pill-muted'>No change in size</span>"
    st.markdown(
        f"<div style='margin-top:0.5rem'>{badge}</div>"
        f"<div class='opt-meta-line'>{size_line} · {result.output_format}"
        f" · {result.new_width}×{result.new_height}</div>",
        unsafe_allow_html=True,
    )
    if result.note:
        st.caption(f"ℹ️ {result.note}")
    st.download_button(
        "⬇ Download",
        data=result.data,
        file_name=result.output_filename,
        mime=_mime(result.output_format),
        key=f"dl_{results_key}_{result.image_id}",
        width="stretch",
    )


def _toggle_preview(previews_key: str, image_id: str) -> None:
    previews: set = st.session_state.setdefault(previews_key, set())
    previews.symmetric_difference_update({image_id})


def _fmt(size_bytes: int) -> str:
    from utils.file_utils import format_bytes
    return format_bytes(size_bytes)


def _mime(output_format: str) -> str:
    from core.converter import MIME_TYPES
    return MIME_TYPES.get(output_format.lower(), "application/octet-stream")
