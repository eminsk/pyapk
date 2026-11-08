"""Tests for pure Python Android Binary XML (AXML) encoder."""

from __future__ import annotations

from pathlib import Path
import pytest
from pureapk.cli import main
from pureapk.manifest import AndroidManifest, AxmlEncoder

SAMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="org.example.coolapp"
    android:versionCode="205"
    android:versionName="2.5.0">
    <uses-sdk android:minSdkVersion="26" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <application android:label="Cool App" android:icon="@mipmap/ic_launcher">
        <activity android:name="org.example.coolapp.MainActivity" android:exported="true" />
    </application>
</manifest>"""


def test_axml_encoder_basic() -> None:
    encoded = AxmlEncoder.encode(SAMPLE_XML)
    assert len(encoded) > 100
    assert encoded[:2] == b"\x03\x00"  # AXML header magic

    # Parse back with AndroidManifest
    manifest = AndroidManifest(encoded)
    assert manifest.package_name == "org.example.coolapp"
    assert manifest.version_code == 205
    assert manifest.version_name == "2.5.0"
    assert manifest.min_sdk_version == 26
    assert manifest.target_sdk_version == 34
    assert "android.permission.INTERNET" in manifest.permissions
    assert "android.permission.ACCESS_NETWORK_STATE" in manifest.permissions
    assert "org.example.coolapp.MainActivity" in manifest.activities
    assert manifest.application_label == "Cool App"


def test_axml_encoder_from_bytes() -> None:
    encoded = AxmlEncoder.encode(SAMPLE_XML.encode("utf-8"))
    manifest = AndroidManifest(encoded)
    assert manifest.package_name == "org.example.coolapp"
    assert manifest.version_code == 205


def test_cli_compile_manifest(tmp_path: Path) -> None:
    xml_file = tmp_path / "AndroidManifest.xml"
    xml_file.write_text(SAMPLE_XML, encoding="utf-8")
    out_axml = tmp_path / "AndroidManifest.bin"

    exit_code = main(["compile-manifest", str(xml_file), "-o", str(out_axml)])
    assert exit_code == 0
    assert out_axml.exists()

    manifest = AndroidManifest(out_axml.read_bytes())
    assert manifest.package_name == "org.example.coolapp"
    assert manifest.version_code == 205
