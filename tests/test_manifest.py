"""Tests for AndroidManifest and binary AXML parsing."""

from __future__ import annotations

import pytest
from pureapk.manifest import AndroidManifest, AxmlElement, AxmlAttribute, StringPool


def test_plain_xml_manifest() -> None:
    xml_data = b"""<?xml version="1.0" encoding="utf-8"?>
    <manifest xmlns:android="http://schemas.android.com/apk/res/android"
        package="org.example.plain"
        android:versionCode="42"
        android:versionName="2.0">
        <uses-sdk android:minSdkVersion="19" android:targetSdkVersion="33" />
        <uses-permission android:name="android.permission.VIBRATE" />
        <application android:label="PlainApp" android:icon="@drawable/icon">
            <activity android:name=".MainPlainActivity" />
        </application>
    </manifest>
    """
    manifest = AndroidManifest(xml_data)
    assert manifest.package_name == "org.example.plain"
    assert manifest.version_code == 42
    assert manifest.version_name == "2.0"
    assert manifest.min_sdk_version == 19
    assert manifest.target_sdk_version == 33
    assert "android.permission.VIBRATE" in manifest.permissions
    assert ".MainPlainActivity" in manifest.activities
    assert manifest.application_label == "PlainApp"
    assert manifest.application_icon == "@drawable/icon"


def test_binary_axml_manifest(sample_axml_bytes: bytes) -> None:
    manifest = AndroidManifest(sample_axml_bytes)
    assert manifest.package_name == "com.example.testapp"
    assert manifest.version_code == 101
    assert manifest.version_name == "1.2.3"
    assert manifest.min_sdk_version == 21
    assert manifest.target_sdk_version == 34
    assert "android.permission.INTERNET" in manifest.permissions
    assert "android.permission.CAMERA" in manifest.permissions
    assert "MainActivity" in manifest.activities
    assert "SettingsActivity" in manifest.activities
    assert manifest.application_label == "TestApp"


def test_manifest_as_dict(sample_axml_bytes: bytes) -> None:
    manifest = AndroidManifest(sample_axml_bytes)
    d = manifest.as_dict()
    assert d["package_name"] == "com.example.testapp"
    assert d["version_code"] == 101
    assert d["version_name"] == "1.2.3"
    assert d["min_sdk_version"] == 21
    assert d["target_sdk_version"] == 34
    assert isinstance(d["permissions"], list)
    assert isinstance(d["activities"], list)


def test_malformed_axml_resilience() -> None:
    # Too short bytes
    manifest_short = AndroidManifest(b"\x03\x00")
    assert manifest_short.package_name == ""
    assert manifest_short.version_code is None

    # Corrupt chunk size
    manifest_corrupt = AndroidManifest(b"\x03\x00\x08\x00\xFF\xFF\xFF\x7F\x01\x00\x1C\x00\x20\x00\x00\x00")
    assert manifest_corrupt.package_name == ""


def test_axml_element_and_attributes() -> None:
    elem = AxmlElement("activity")
    attr = AxmlAttribute("android", "name", ".SubActivity", 3, 0, ".SubActivity")
    elem.attributes["name"] = attr
    assert elem.get_attr("name") == ".SubActivity"
    assert elem.get_attr("missing", "default") == "default"

    child = AxmlElement("intent-filter")
    elem.children.append(child)
    assert len(list(elem.find_all("intent-filter"))) == 1
    assert len(list(elem.find_all("unknown"))) == 0

    xml_text = elem.to_xml_string()
    assert "<activity" in xml_text
    assert "<intent-filter" in xml_text
