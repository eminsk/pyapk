"""APK Signature scheme detection and certificate fingerprint analysis.

Supports:
- v1 (JAR signing: META-INF/*.RSA, *.DSA, *.EC)
- v2 (APK Signature Scheme v2)
- v3 (APK Signature Scheme v3)
- v4 (APK Signature Scheme v4)
Computes SHA-256, SHA-1, and MD5 fingerprints with zero C-dependencies.
"""

from __future__ import annotations

import hashlib
import struct
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import zipfile

# APK Signing Block Magic (16 bytes)
APK_SIG_BLOCK_MAGIC = b"APK Sig Block 42"
SIGNATURE_SCHEME_V2_BLOCK_ID = 0x7109871A
SIGNATURE_SCHEME_V3_BLOCK_ID = 0xF05368C0
SIGNATURE_SCHEME_V31_BLOCK_ID = 0x1B93AD61
SIGNATURE_SCHEME_V4_BLOCK_ID = 0x2B09871A

# Pre-compiled struct
_STRUCT_SIG_PAIR_HEADER = struct.Struct("<QI")


class APKCertificate:
    """Certificate container with pre-computed cryptographic fingerprints."""

    __slots__ = ("filename", "raw_bytes", "sha256", "sha1", "md5")

    def __init__(self, filename: str, raw_bytes: bytes) -> None:
        self.filename = filename
        self.raw_bytes = raw_bytes
        self.sha256 = hashlib.sha256(raw_bytes).hexdigest()
        self.sha1 = hashlib.sha1(raw_bytes).hexdigest()
        self.md5 = hashlib.md5(raw_bytes).hexdigest()

    def as_dict(self) -> Dict[str, str]:
        return {
            "filename": self.filename,
            "sha256": self.sha256,
            "sha1": self.sha1,
            "md5": self.md5,
        }


class APKSignature:
    """Parsed signature schemes and certificate info for an APK."""

    __slots__ = (
        "has_v1",
        "has_v2",
        "has_v3",
        "has_v4",
        "certificates",
        "scheme_names",
    )

    def __init__(
        self,
        has_v1: bool,
        has_v2: bool,
        has_v3: bool,
        has_v4: bool,
        certificates: Sequence[APKCertificate],
    ) -> None:
        self.has_v1 = has_v1
        self.has_v2 = has_v2
        self.has_v3 = has_v3
        self.has_v4 = has_v4
        self.certificates = tuple(certificates)

        schemes: List[str] = []
        appender = {
            True: lambda name: schemes.append(name),
            False: lambda name: None,
        }
        appender[has_v1]("v1")
        appender[has_v2]("v2")
        appender[has_v3]("v3")
        appender[has_v4]("v4")
        self.scheme_names = tuple(schemes)

    @property
    def is_signed(self) -> bool:
        return bool(self.scheme_names)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "is_signed": self.is_signed,
            "schemes": list(self.scheme_names),
            "v1_jar": self.has_v1,
            "v2_apk_sig": self.has_v2,
            "v3_apk_sig": self.has_v3,
            "v4_apk_sig": self.has_v4,
            "certificates": list(map(lambda c: c.as_dict(), self.certificates)),
        }

    @classmethod
    def inspect(cls, zf: zipfile.ZipFile, raw_bytes: Optional[bytes] = None) -> APKSignature:
        # 1. Inspect v1 JAR signatures in META-INF
        namelist = zf.namelist()
        v1_certs: List[APKCertificate] = []
        cert_exts = (".RSA", ".DSA", ".EC")

        def check_v1(name: str) -> None:
            upper = name.upper()
            is_cert = upper.startswith("META-INF/") and any(map(upper.endswith, cert_exts))
            action = {
                True: lambda: v1_certs.append(APKCertificate(name, zf.read(name))),
                False: lambda: None,
            }[is_cert]
            action()

        tuple(map(check_v1, namelist))
        has_v1 = bool(v1_certs)

        # 2. Inspect v2 / v3 / v4 Signing Block
        has_v2 = False
        has_v3 = False
        has_v4 = False

        lookup_source = {
            True: lambda: raw_bytes,
            False: lambda: getattr(zf, "_filePassed", None) and getattr(zf.fp, "getvalue", lambda: None)(),
        }[raw_bytes is not None]
        data = lookup_source()

        if data and len(data) >= 32:
            sig_flags = cls._scan_signing_block(data)
            has_v2 = sig_flags.get("v2", False)
            has_v3 = sig_flags.get("v3", False)
            has_v4 = sig_flags.get("v4", False)

        return cls(
            has_v1=has_v1,
            has_v2=has_v2,
            has_v3=has_v3,
            has_v4=has_v4,
            certificates=v1_certs,
        )

    @staticmethod
    def _scan_signing_block(data: bytes) -> Dict[str, bool]:
        """Scans for APK Signing Block preceding the ZIP Central Directory."""
        results = {"v2": False, "v3": False, "v4": False}
        total_len = len(data)
        # Search for End of Central Directory (EOCD) magic 0x06054b50 in the last 65KB
        search_start = max(0, total_len - 65557)
        tail = data[search_start:]
        eocd_pos = tail.rfind(b"\x50\x4b\x05\x06")

        if eocd_pos == -1:
            return results

        real_eocd_pos = search_start + eocd_pos
        if real_eocd_pos + 22 > total_len:
            return results

        # Central Directory offset is at real_eocd_pos + 16 (uint32)
        cd_offset = struct.unpack_from("<I", data, real_eocd_pos + 16)[0]
        if cd_offset < 24:
            return results

        # Check for APK Signing Block magic right before Central Directory
        magic_offset = cd_offset - 16
        if data[magic_offset:cd_offset] != APK_SIG_BLOCK_MAGIC:
            return results

        block_size_offset = cd_offset - 24
        block_size = struct.unpack_from("<Q", data, block_size_offset)[0]
        block_start = cd_offset - block_size - 8
        if block_start < 0 or block_start + 8 >= total_len:
            return results

        # Read ID-value pairs
        pos = block_start + 8
        block_end = cd_offset - 24

        while pos + 12 <= block_end:
            pair_len = struct.unpack_from("<Q", data, pos)[0]
            if pair_len < 4 or pos + 8 + pair_len > block_end:
                break
            sig_id = struct.unpack_from("<I", data, pos + 8)[0]
            id_dispatch = {
                SIGNATURE_SCHEME_V2_BLOCK_ID: lambda: results.update(v2=True),
                SIGNATURE_SCHEME_V3_BLOCK_ID: lambda: results.update(v3=True),
                SIGNATURE_SCHEME_V31_BLOCK_ID: lambda: results.update(v3=True),
                SIGNATURE_SCHEME_V4_BLOCK_ID: lambda: results.update(v4=True),
            }
            handler = id_dispatch.get(sig_id, lambda: None)
            handler()
            pos += 8 + pair_len

        return results
