"""Tests for Dalvik Executable (DEX) header parsing."""

from __future__ import annotations

import pytest
from pureapk.dex import DexHeader, MultiDexSummary


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
