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



def test_builder_16kb_page_alignment(tmp_path: Path) -> None:
    out_apk = tmp_path / "aligned_16k.apk"
    builder = APKBuilder(out_apk)
    builder.add_bytes("AndroidManifest.xml", b"<manifest package='test' />", compress=True)
    builder.add_bytes("lib/arm64-v8a/libtest.so", b"\x7fELF" + b"\x00" * 200, compress=False)
    builder.add_bytes("resources.arsc", b"RESOURCES", compress=False)
    builder.build()

    assert out_apk.exists()

    with APK(out_apk) as apk:
        align = apk.check_alignment(so_alignment=16384, file_alignment=4)
        assert align["is_aligned"] is True
        assert align["so_16k_compliant"] is True
        assert align["total_so_files"] == 1
        assert align["aligned_so_files"] == 1
        assert apk.is_aligned_16k is True


def test_zipalign_function_and_cli(tmp_path: Path) -> None:
    from pureapk.builder import zipalign
    from pureapk.cli import main

    unaligned_zip = tmp_path / "unaligned.apk"
    with zipfile.ZipFile(unaligned_zip, "w") as zf:
        zf.writestr("AndroidManifest.xml", b"<manifest />")
        info = zipfile.ZipInfo("lib/arm64-v8a/libfoo.so")
        info.compress_type = zipfile.ZIP_STORED
        zf.writestr(info, b"\x7fELF" + b"\x00" * 100)

    with APK(unaligned_zip) as apk:
        align = apk.check_alignment()
        assert align["is_aligned"] is False

    aligned_apk = tmp_path / "aligned.apk"
    zipalign(unaligned_zip, aligned_apk, so_alignment=16384, file_alignment=4)

    with APK(aligned_apk) as apk:
        align = apk.check_alignment()
        assert align["is_aligned"] is True
        assert apk.is_aligned_16k is True

    code = main(["zipalign", str(aligned_apk), "--check", "--json"])
    assert code == 0
