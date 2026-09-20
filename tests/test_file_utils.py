"""Tests for file utilities: formatting, naming, ZIP creation, history persistence."""

from __future__ import annotations

import zipfile
from io import BytesIO

from utils.file_utils import (build_output_filename, create_zip, format_bytes,
                              load_history, save_history, unique_name)


def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(512) == "512 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(2.45 * 1024 * 1024) == "2.5 MB"


def test_build_output_filename():
    assert build_output_filename("holiday.png", "webp") == "holiday-optimized.webp"
    assert build_output_filename("photo.jpg", "jpg", suffix="") == "photo.jpg"
    assert build_output_filename("weird/../name", "png", suffix="") == "name.png"


def test_unique_name():
    assert unique_name("a.png", {"b.png"}) == "a.png"
    assert unique_name("a.png", {"a.png"}) == "a (1).png"
    assert unique_name("a.png", {"a.png", "a (1).png"}) == "a (2).png"


def test_create_zip_contains_files():
    data = create_zip([("one.txt", b"111"), ("two.txt", b"222")])
    assert data[:2] == b"PK"  # real ZIP magic
    with zipfile.ZipFile(BytesIO(data)) as archive:
        assert archive.namelist() == ["one.txt", "two.txt"]
        assert archive.read("two.txt") == b"222"


def test_create_zip_dedupes_names():
    data = create_zip([("same.png", b"a"), ("same.png", b"b")])
    with zipfile.ZipFile(BytesIO(data)) as archive:
        assert sorted(archive.namelist()) == ["same (1).png", "same.png"]


def test_history_roundtrip(tmp_path, monkeypatch):
    import utils.file_utils as fu
    monkeypatch.setattr(fu, "DATA_DIR", tmp_path)
    monkeypatch.setattr(fu, "HISTORY_FILE", tmp_path / "history.json")

    assert load_history() == []
    save_history([{"filename": "a.jpg", "saved_percent": 71.9}])
    assert load_history() == [{"filename": "a.jpg", "saved_percent": 71.9}]

    (tmp_path / "history.json").write_text("not json", encoding="utf-8")
    assert load_history() == []  # corrupted file tolerated
