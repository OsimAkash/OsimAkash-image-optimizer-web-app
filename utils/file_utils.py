"""File-related helpers: size formatting, safe naming, ZIP packaging and history persistence.

All functions here are pure Python (no Streamlit, no Pillow) so they can be reused
anywhere in the application and unit-tested in isolation.
"""

from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

logger = logging.getLogger(__name__)

# Lightweight, non-image history is persisted next to the project (see .gitignore).
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_FILE = DATA_DIR / "history.json"


def format_bytes(num: float) -> str:
    """Format a byte count as a short human-readable string (e.g. ``2.4 MB``)."""
    num = float(max(num, 0))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            return f"{int(num)} B" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def sanitize_filename(name: str, *, fallback: str = "image", max_stem: int = 64) -> str:
    """Return a filesystem-safe version of a filename.

    The original filename is never trusted: path components, control characters and
    unsafe characters are stripped, leading dots are removed and the length is capped.
    """
    name = (name or "").strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^\w.\-() ]+", "", name).strip(". ")
    name = re.sub(r"\s+", " ", name)
    if not name:
        return fallback
    stem, dot, ext = name.rpartition(".")
    if not dot:
        return name[:max_stem] or fallback
    return f"{stem[:max_stem].strip('. ') or fallback}.{ext.lower()}"


def unique_name(name: str, existing: Iterable[str]) -> str:
    """Return ``name`` adjusted with a numeric suffix so it is unique inside ``existing``."""
    if name not in existing:
        return name
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    counter = 1
    while True:
        candidate = f"{stem} ({counter}){('.' + ext) if ext else ''}"
        if candidate not in existing:
            return candidate
        counter += 1


def build_output_filename(original_name: str, new_ext: str, *, suffix: str = "-optimized") -> str:
    """Build the output filename for a processed image (extension always matches content)."""
    stem = sanitize_filename(original_name)
    stem = stem.rsplit(".", 1)[0] if "." in stem else stem
    ext = new_ext.lower().lstrip(".")
    return f"{stem or 'image'}{suffix}.{ext}"


def create_zip(files: Mapping[str, bytes] | list[tuple[str, bytes]]) -> bytes:
    """Package files into an in-memory ZIP archive and return the bytes.

    Duplicate names are resolved automatically. Raises :class:`RuntimeError` with a
    user-friendly message if the archive cannot be produced.
    """
    items = files.items() if isinstance(files, Mapping) else files
    buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            used: set[str] = set()
            for name, data in items:
                archive.writestr(unique_name(name, used), data)
                used.add(name)
    except (zipfile.BadZipFile, OSError, MemoryError, RuntimeError) as exc:
        logger.exception("ZIP creation failed")
        raise RuntimeError("Could not create the ZIP archive. Please try fewer images at once.") from exc
    return buffer.getvalue()


def timestamp() -> str:
    """Current local time formatted for history records."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_history(records: list[dict]) -> None:
    """Persist lightweight history records (no image binaries) to the local data folder."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(json.dumps(records), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not persist history: %s", exc)


def load_history() -> list[dict]:
    """Load persisted history records, tolerating a missing or corrupted file."""
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not load persisted history: %s", exc)
    return []
