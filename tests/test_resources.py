"""Tests for Android binary resource table (resources.arsc) generation and validation."""

from __future__ import annotations

import struct
from pureapk.frameworks import patch_arsc_private_version
from pureapk.resources import ArscBuilder


def test_minimal_arsc_generation() -> None:
    arsc_bytes = ArscBuilder.generate_minimal_arsc(
        package_name="org.kivy.calculator",
        app_name="Calculator Pro",
    )
    assert len(arsc_bytes) >= 300
    assert arsc_bytes.startswith(b"\x02\x00\x0c\x00")

    # Validate with ArscBuilder
    assert ArscBuilder.is_valid_arsc(arsc_bytes) is True

    # Parse summary
    summary = ArscBuilder.parse_summary(arsc_bytes)
    assert summary["valid"] is True
    assert summary["package_count"] == 1
    assert summary["table_size"] == len(arsc_bytes)


def test_invalid_and_stub_arsc_rejection() -> None:
    # 12-byte stub placeholder from older pureapk
    stub_12b = struct.pack("<HHII", 0x0002, 12, 12, 0)
    assert ArscBuilder.is_valid_arsc(stub_12b) is False
    assert ArscBuilder.parse_summary(stub_12b)["valid"] is False

    # Corrupt or truncated bytes
    assert ArscBuilder.is_valid_arsc(b"") is False
    assert ArscBuilder.is_valid_arsc(b"random garbage data that is short") is False


def test_patch_private_version_in_generated_arsc() -> None:
    arsc_bytes = ArscBuilder.generate_minimal_arsc(
        package_name="org.kivy.app",
        app_name="Test App",
    )
    assert ArscBuilder.is_valid_arsc(arsc_bytes) is True

    # Patch with 40-character SHA1 hex
    test_sha1 = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
    patched = patch_arsc_private_version(arsc_bytes, test_sha1)
    assert test_sha1.encode("ascii") in patched
    assert ArscBuilder.is_valid_arsc(patched) is True
    assert len(patched) == len(arsc_bytes)
