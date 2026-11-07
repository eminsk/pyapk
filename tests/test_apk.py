"""Tests for core APK class."""

from __future__ import annotations

import io
from pathlib import Path
import pytest
from pureapk.apk import APK
from pureapk import load, inspect


def test_apk_from_bytes(sample_apk_bytes: bytes) -> None:
    with APK(sample_apk_bytes) as apk:
        assert apk.package_name == "com.example.testapp"
        assert apk.version_code == 101
        assert apk.version_name == "1.2.3"
        assert apk.min_sdk_version == 21
        assert apk.target_sdk_version == 34
        assert "android.permission.INTERNET" in apk.permissions
        assert "MainActivity" in apk.activities
        assert "arm64-v8a" in apk.native_architectures
        assert "x86_64" in apk.native_architectures
        assert apk.dex.total_classes == 15
        assert apk.signature.is_signed is True
        assert "AndroidManifest.xml" in apk.filenames

        # Test read
        content = apk.read("resources.arsc")
        assert content == b"TEST_RESOURCES_ARSC"


def test_apk_from_file(sample_apk_file: str) -> None:
    apk = load(sample_apk_file)
    try:
        assert apk.package_name == "com.example.testapp"
        assert repr(apk) == "APK(package='com.example.testapp', version='1.2.3')"

        info_dict = apk.info()
        assert info_dict["package_name"] == "com.example.testapp"
        assert info_dict["version_code"] == 101
        assert info_dict["total_files"] >= 5
    finally:
        apk.close()


def test_apk_inspect_helper(sample_apk_bytes: bytes) -> None:
    info = inspect(sample_apk_bytes)
    assert info["package_name"] == "com.example.testapp"
    assert info["version_code"] == 101


def test_apk_extract(sample_apk_bytes: bytes, tmp_path: Path) -> None:
    dest = tmp_path / "extracted"
    with APK(sample_apk_bytes) as apk:
        apk.extract(dest)
    assert (dest / "AndroidManifest.xml").exists()
    assert (dest / "classes.dex").exists()
    assert (dest / "resources.arsc").exists()


def test_apk_verify(sample_apk_bytes: bytes) -> None:
    with APK(sample_apk_bytes) as apk:
        status = apk.verify()
        assert status["is_valid"] is True
        assert status["corrupted_file"] is None
        assert status["is_signed"] is True
