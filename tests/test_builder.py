"""Tests for APKBuilder and packaging functionality."""

from __future__ import annotations

from pathlib import Path
import zipfile
import pytest
from pureapk.apk import APK
from pureapk.builder import APKBuilder, pack


def test_builder_basic(tmp_path: Path) -> None:
    out_apk = tmp_path / "built.apk"
    builder = APKBuilder(out_apk)
    builder.add_bytes("AndroidManifest.xml", b"<manifest />")
    builder.add_bytes("resources.arsc", b"RESOURCES", compress=False)
    builder.add_bytes("classes.dex", b"DEX_DATA", compress=True)
    builder.build()

    assert out_apk.exists()

    with zipfile.ZipFile(out_apk) as zf:
        infolist = {info.filename: info for info in zf.infolist()}
        assert "AndroidManifest.xml" in infolist
        assert "resources.arsc" in infolist
        assert "classes.dex" in infolist

        # resources.arsc should be stored (uncompressed)
        assert infolist["resources.arsc"].compress_type == zipfile.ZIP_STORED
        # classes.dex should be deflated (compressed)
        assert infolist["classes.dex"].compress_type == zipfile.ZIP_DEFLATED


def test_builder_pack_directory(tmp_path: Path) -> None:
    src_dir = tmp_path / "app_src"
    src_dir.mkdir()
    (src_dir / "AndroidManifest.xml").write_bytes(b"<manifest package='test' />")
    (src_dir / "res").mkdir()
    (src_dir / "res" / "icon.png").write_bytes(b"PNG_DATA")

    out_apk = tmp_path / "output.apk"
    pack(src_dir, out_apk)

    assert out_apk.exists()

    with APK(out_apk) as apk:
        assert "AndroidManifest.xml" in apk.filenames
        assert "res/icon.png" in apk.filenames
        assert apk.read("res/icon.png") == b"PNG_DATA"
