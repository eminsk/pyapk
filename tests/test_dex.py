"""Tests for Dalvik Executable (DEX) header parsing."""

from __future__ import annotations

import pytest
from pureapk.dex import DexBuilder, DexHeader, MultiDexSummary


def test_dex_header_parsing(sample_dex_bytes: bytes) -> None:
    header = DexHeader.from_bytes(sample_dex_bytes)
    assert header.is_valid is True
    assert header.version == "035"
    assert header.checksum == 0xA1B2C3D4
    assert header.class_defs_size == 12
    assert header.method_ids_size == 55
    assert header.field_ids_size == 30
    assert header.string_ids_size == 100
    assert len(header.signature_hex) == 40

    d = header.as_dict()
    assert d["classes_count"] == 12
    assert d["methods_count"] == 55
    assert d["fields_count"] == 30
    assert d["is_valid"] is True


def test_dex_invalid_short_bytes() -> None:
    header = DexHeader.from_bytes(b"short")
    assert header.is_valid is False
    assert header.file_size == 0
    assert header.class_defs_size == 0


def test_dex_invalid_magic() -> None:
    bad_bytes = b"badmagic" + b"\x00" * 104
    header = DexHeader.from_bytes(bad_bytes)
    assert header.is_valid is False


def test_multidex_summary(sample_dex_bytes: bytes) -> None:
    h1 = DexHeader.from_bytes(sample_dex_bytes)
    h2 = DexHeader.from_bytes(sample_dex_bytes)
    summary = MultiDexSummary([h1, h2])

    assert summary.dex_count == 2
    assert summary.total_classes == 24
    assert summary.total_methods == 110
    assert summary.total_fields == 60
    assert summary.total_strings == 200

    d = summary.as_dict()
    assert d["dex_count"] == 2
    assert d["total_classes"] == 24
    assert len(d["files"]) == 2


def test_dex_builder_bootstrap() -> None:
    # 1. Real valid Dalvik DEX generation with bytecode
    dex_bytes = DexBuilder.generate_bootstrap_dex(classes_count=5, methods_count=10)
    assert len(dex_bytes) > 112
    assert dex_bytes.startswith(b"dex\n035\x00")

    header = DexHeader.from_bytes(dex_bytes)
    assert header.is_valid is True
    assert header.version == "035"
    assert header.class_defs_size == 5
    assert header.file_size == len(dex_bytes)

    # Verify extracted classes
    classes = DexBuilder.extract_class_names(dex_bytes)
    assert len(classes) == 5
    assert "MainActivity0" in classes

    # Default launcher bootstrap classes
    default_dex = DexBuilder.generate_bootstrap_dex()
    default_hdr = DexHeader.from_bytes(default_dex)
    assert default_hdr.is_valid is True
    default_classes = DexBuilder.extract_class_names(default_dex)
    assert "org.kivy.android.PythonActivity" in default_classes
    assert "org.renpy.android.PythonSDLActivity" in default_classes
    assert "io.flet.FletActivity" in default_classes
    assert "org.beeware.android.MainActivity" in default_classes
    assert "com.webview.app.MainActivity" in default_classes
    assert "org.qtproject.qt.android.bindings.QtActivity" in default_classes

    # 2. Raw stub generation (when explicitly requested)
    stub_bytes = DexBuilder.generate_bootstrap_dex(classes_count=5, methods_count=10, raw_stub=True)
    assert len(stub_bytes) == 112
    assert stub_bytes.startswith(b"dex\n035\x00")
    stub_hdr = DexHeader.from_bytes(stub_bytes)
    assert stub_hdr.is_valid is True
    assert stub_hdr.class_defs_size == 5
    assert stub_hdr.method_ids_size == 10

