"""Shared test fixtures and binary artifact generators."""

from __future__ import annotations

import io
from pathlib import Path
import struct
import sys
from typing import Dict, List, Optional, Tuple
import zipfile
import pytest

# Ensure src/ is on sys.path for direct pytest invocation without pip install
_SRC_PATH = str(Path(__file__).resolve().parent.parent / "src")
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

from pureapk.apk import APK
from pureapk.builder import APKBuilder


def make_test_axml(
    package: str = "com.example.testapp",
    version_code: int = 101,
    version_name: str = "1.2.3",
    min_sdk: int = 21,
    target_sdk: int = 34,
    permissions: Tuple[str, ...] = ("android.permission.INTERNET", "android.permission.CAMERA"),
    activities: Tuple[str, ...] = ("MainActivity", "SettingsActivity"),
    label: str = "TestApp",
) -> bytes:
    """Builds a strictly valid binary AndroidManifest.xml (AXML)."""
    strings = [
        "manifest",
        "package",
        package,
        "versionCode",
        "versionName",
        version_name,
        "uses-sdk",
        "minSdkVersion",
        "targetSdkVersion",
        "uses-permission",
        "name",
        "application",
        "label",
        label,
        "activity",
    ]
    # Add dynamic permissions and activities to strings
    for p in permissions:
        if p not in strings:
            strings.append(p)
    for a in activities:
        if a not in strings:
            strings.append(a)

    str_idx_map = {s: i for i, s in enumerate(strings)}

    str_offsets = []
    str_data = bytearray()
    for s in strings:
        str_offsets.append(len(str_data))
        encoded = s.encode("utf-16le")
        str_data.extend(struct.pack("<H", len(s)))
        str_data.extend(encoded)
        str_data.extend(b"\x00\x00")

    # Pad string data to 4-byte boundary
    pad = (4 - (len(str_data) % 4)) % 4
    str_data.extend(b"\x00" * pad)

    offsets_bytes = b"".join(struct.pack("<I", off) for off in str_offsets)
    sp_hdr_size = 28
    sp_chunk_size = sp_hdr_size + len(offsets_bytes) + len(str_data)
    sp_chunk = (
        struct.pack(
            "<HHIIIIII",
            0x0001,
            sp_hdr_size,
            sp_chunk_size,
            len(strings),
            0,
            0,
            sp_hdr_size + len(offsets_bytes),
            0,
        )
        + offsets_bytes
        + bytes(str_data)
    )

    def make_elem(tag: str, attrs: List[Tuple[str, int, int, int]]) -> bytes:
        tag_idx = str_idx_map[tag]
        attr_bytes = bytearray()
        for a_name, a_raw, a_type, a_data in attrs:
            name_idx = str_idx_map[a_name]
            attr_bytes.extend(
                struct.pack("<IIIHBB I", 0, name_idx, a_raw, 8, 0, a_type, a_data)
            )
        extra = struct.pack("<IIHHHHHH", 0, tag_idx, 20, 20, len(attrs), 0, 0, 0)
        chunk_size = 16 + 20 + len(attr_bytes)
        base = struct.pack("<HHIII", 0x0102, 16, chunk_size, 1, 0xFFFFFFFF)
        return base + extra + bytes(attr_bytes)

    def make_end_elem(tag: str) -> bytes:
        tag_idx = str_idx_map[tag]
        base = struct.pack("<HHIII", 0x0103, 16, 24, 1, 0xFFFFFFFF)
        extra = struct.pack("<II", 0, tag_idx)
        return base + extra

    # 1. Manifest tag
    e_manifest = make_elem(
        "manifest",
        [
            ("package", str_idx_map[package], 3, str_idx_map[package]),
            ("versionCode", 0xFFFFFFFF, 16, version_code),
            ("versionName", str_idx_map[version_name], 3, str_idx_map[version_name]),
        ],
    )

    # 2. uses-sdk
    e_sdk = make_elem(
        "uses-sdk",
        [
            ("minSdkVersion", 0xFFFFFFFF, 16, min_sdk),
            ("targetSdkVersion", 0xFFFFFFFF, 16, target_sdk),
        ],
    )
    end_sdk = make_end_elem("uses-sdk")

    # 3. permissions
    perm_chunks = bytearray()
    for p in permissions:
        p_idx = str_idx_map[p]
        perm_chunks.extend(make_elem("uses-permission", [("name", p_idx, 3, p_idx)]))
        perm_chunks.extend(make_end_elem("uses-permission"))

    # 4. application & activities
    e_app = make_elem("application", [("label", str_idx_map[label], 3, str_idx_map[label])])
    act_chunks = bytearray()
    for a in activities:
        a_idx = str_idx_map[a]
        act_chunks.extend(make_elem("activity", [("name", a_idx, 3, a_idx)]))
        act_chunks.extend(make_end_elem("activity"))
    end_app = make_end_elem("application")
    end_manifest = make_end_elem("manifest")

    nodes = (
        e_manifest
        + e_sdk
        + end_sdk
        + bytes(perm_chunks)
        + e_app
        + bytes(act_chunks)
        + end_app
        + end_manifest
    )
    total_len = 8 + len(sp_chunk) + len(nodes)
    header = struct.pack("<HHI", 0x0003, 8, total_len)
    return header + sp_chunk + nodes


def make_test_dex(classes: int = 12, methods: int = 55, fields: int = 30) -> bytes:
    """Builds a minimal valid 112-byte Dalvik Executable (DEX) header."""
    magic = b"dex\n035\0"
    checksum = 0xA1B2C3D4
    signature = b"\x01" * 20
    file_size = 112
    header_size = 112
    endian_tag = 0x12345678
    return struct.pack(
        "<8sI20s" + "I" * 20,
        magic,
        checksum,
        signature,
        file_size,
        header_size,
        endian_tag,
        0,
        0,  # link
        0,  # map
        100,
        0,  # string_ids
        20,
        0,  # type_ids
        15,
        0,  # proto_ids
        fields,
        0,  # field_ids
        methods,
        0,  # method_ids
        classes,
        0,  # class_defs
        0,
        0,  # data
    )


def make_test_apk_bytes(
    package: str = "com.example.testapp",
    version_code: int = 101,
    version_name: str = "1.2.3",
    has_native_libs: bool = True,
    has_signature: bool = True,
) -> bytes:
    """Builds an entire in-memory APK archive for fast testing."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # 1. AndroidManifest.xml
        zf.writestr("AndroidManifest.xml", make_test_axml(package, version_code, version_name))
        # 2. DEX files
        zf.writestr("classes.dex", make_test_dex(classes=10, methods=45, fields=20))
        zf.writestr("classes2.dex", make_test_dex(classes=5, methods=25, fields=10))
        # 3. Resources
        zf.writestr("resources.arsc", b"TEST_RESOURCES_ARSC")
        # 4. Native libs
        if has_native_libs:
            zf.writestr("lib/arm64-v8a/libnative.so", b"\x7fELF_ARM64")
            zf.writestr("lib/x86_64/libnative.so", b"\x7fELF_X86_64")
        # 5. META-INF signatures
        if has_signature:
            zf.writestr("META-INF/MANIFEST.MF", b"Manifest-Version: 1.0\nCreated-By: PureAPK\n")
            zf.writestr("META-INF/CERT.SF", b"Signature-Version: 1.0\n")
            zf.writestr("META-INF/CERT.RSA", b"MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0")

    return buf.getvalue()


@pytest.fixture
def sample_axml_bytes() -> bytes:
    return make_test_axml()


@pytest.fixture
def sample_dex_bytes() -> bytes:
    return make_test_dex()


@pytest.fixture
def sample_apk_bytes() -> bytes:
    return make_test_apk_bytes()


@pytest.fixture
def sample_apk_file(tmp_path: pytest.TempPathFactory) -> str:
    path = tmp_path / "sample.apk"
    path.write_bytes(make_test_apk_bytes())
    return str(path)
