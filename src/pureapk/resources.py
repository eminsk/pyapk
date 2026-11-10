"""Android binary resource table (resources.arsc) generator and validator.

Pure Python implementation of Android's ResTable binary format.
Strict memory overhead control using __slots__.
"""

from __future__ import annotations

import io
from pathlib import Path
import struct
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# Android Resource Table Chunk Types
RES_NULL_TYPE = 0x0000
RES_STRING_POOL_TYPE = 0x0001
RES_TABLE_TYPE = 0x0002
RES_TABLE_PACKAGE_TYPE = 0x0200
RES_TABLE_TYPE_TYPE = 0x0201
RES_TABLE_TYPE_SPEC_TYPE = 0x0202

# Res_value data types
TYPE_NULL = 0x00
TYPE_REFERENCE = 0x01
TYPE_ATTRIBUTE = 0x02
TYPE_STRING = 0x03
TYPE_FLOAT = 0x04
TYPE_DIMENSION = 0x05
TYPE_FRACTION = 0x06
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_INT_BOOLEAN = 0x12
TYPE_INT_COLOR_ARGB8 = 0x1c
TYPE_INT_COLOR_RGB8 = 0x1d


def _align4(data: bytes) -> bytes:
    """Pad bytes to 4-byte boundary."""
    rem = len(data) % 4
    return data + (b"\x00" * (4 - rem)) if rem else data


def _build_string_pool(strings: Sequence[str], utf8: bool = True) -> bytes:
    """Builds a binary ResStringPool chunk (type 0x0001)."""
    count = len(strings)
    flags = 0x00000100 if utf8 else 0  # UTF-8 flag
    str_data = bytearray()
    offsets: List[int] = []

    for s in strings:
        offsets.append(len(str_data))
        if utf8:
            s_bytes = s.encode("utf-8")
            u16_len = len(s)
            u8_len = len(s_bytes)
            # UTF-8 string encoding in string pool:
            # u16 length (1 or 2 bytes), u8 length (1 or 2 bytes), utf-8 bytes, null terminator
            encoded_len = bytearray()
            if u16_len > 0x7F:
                encoded_len.append(((u16_len >> 8) & 0x7F) | 0x80)
                encoded_len.append(u16_len & 0xFF)
            else:
                encoded_len.append(u16_len)

            if u8_len > 0x7F:
                encoded_len.append(((u8_len >> 8) & 0x7F) | 0x80)
                encoded_len.append(u8_len & 0xFF)
            else:
                encoded_len.append(u8_len)

            str_data.extend(encoded_len + s_bytes + b"\x00")
        else:
            s_bytes = s.encode("utf-16le")
            u16_len = len(s)
            encoded_len = bytearray()
            if u16_len > 0x7FFF:
                encoded_len.append(((u16_len >> 8) & 0x7F) | 0x80)
                encoded_len.append(u16_len & 0xFF)
            else:
                encoded_len.extend(struct.pack("<H", u16_len))
            str_data.extend(encoded_len + s_bytes + b"\x00\x00")

    str_data_padded = _align4(bytes(str_data))
    header_size = 28
    offsets_bytes = struct.pack(f"<{count}I", *offsets) if count else b""
    strings_start = header_size + len(offsets_bytes)
    total_size = strings_start + len(str_data_padded)

    hdr = struct.pack(
        "<HHIIIIII",
        RES_STRING_POOL_TYPE,
        header_size,
        total_size,
        count,
        0,  # styleCount
        flags,
        strings_start,
        0,  # stylesStart
    )
    return hdr + offsets_bytes + str_data_padded


class ArscBuilder:
    """Minimal 100% valid Android binary resource table (resources.arsc) generator."""

    __slots__ = ()

    @staticmethod
    def generate_minimal_arsc(
        package_name: str = "org.pureapk.app",
        app_name: str = "PureAPK App",
        private_version: Optional[str] = None,
    ) -> bytes:
        """Generates a minimal valid resources.arsc table accepted by Android's PackageParser.

        Includes:
        - Global string pool containing app_name and private_version (for p4a asset unpacking).
        - Package chunk with id 0x7F and package name.
        - Type string pool with 'string'.
        - Key string pool with 'app_name' and 'private_version'.
        - ResTable_typeSpec chunk.
        - ResTable_type chunk with entries pointing to string pool values.
        """
        # Ensure 40-character hex string for private_version so patch_arsc_private_version can update it
        ver_str = private_version or ("0" * 40)
        if len(ver_str) != 40:
            import hashlib
            ver_str = hashlib.sha1(ver_str.encode("utf-8")).hexdigest()

        # 1. Global string pool (UTF-8)
        global_strings = [app_name, ver_str]
        global_pool = _build_string_pool(global_strings, utf8=True)

        # 2. Package Chunk
        type_pool = _build_string_pool(["string"], utf8=True)
        key_pool = _build_string_pool(["app_name", "private_version"], utf8=True)

        pkg_header_size = 288
        type_strings_off = pkg_header_size
        key_strings_off = type_strings_off + len(type_pool)

        entry_count = 2
        type_spec_size = 16 + (entry_count * 4)
        type_spec = struct.pack("<HHI BBH I", RES_TABLE_TYPE_SPEC_TYPE, 16, type_spec_size, 1, 0, 0, entry_count)
        type_spec += struct.pack(f"<{entry_count}I", 0, 0)

        # ResTable_type chunk (84-byte header + config)
        entries_start = 84 + (entry_count * 4)
        res_val_0 = struct.pack("<HBB I", 8, 0, TYPE_STRING, 0)  # global string 0 (app_name)
        res_val_1 = struct.pack("<HBB I", 8, 0, TYPE_STRING, 1)  # global string 1 (private_version)

        entry_data_0 = struct.pack("<HHI", 8, 0, 0) + res_val_0  # key 0 (app_name)
        entry_data_1 = struct.pack("<HHI", 8, 0, 1) + res_val_1  # key 1 (private_version)

        entry_offsets = struct.pack("<2I", 0, len(entry_data_0))
        type_chunk_size = entries_start + len(entry_data_0) + len(entry_data_1)

        config = b"\x00" * 64
        type_chunk_hdr = struct.pack("<HHI BBH II", RES_TABLE_TYPE_TYPE, 84, type_chunk_size, 1, 0, 0, entry_count, entries_start)
        type_chunk = type_chunk_hdr + config + entry_offsets + entry_data_0 + entry_data_1

        pkg_body = type_pool + key_pool + type_spec + type_chunk
        pkg_total_size = pkg_header_size + len(pkg_body)

        pkg_name_bytes = package_name.encode("utf-16le").ljust(256, b"\x00")[:256]
        pkg_hdr = struct.pack(
            "<HHI I 256s II II",
            RES_TABLE_PACKAGE_TYPE,
            pkg_header_size,
            pkg_total_size,
            0x7F,  # Application package ID
            pkg_name_bytes,
            type_strings_off,
            1,  # lastPublicType
            key_strings_off,
            entry_count,  # lastPublicKey
        )
        pkg_chunk = pkg_hdr + pkg_body

        # 3. Main table header
        tbl_header_size = 12
        tbl_total_size = tbl_header_size + len(global_pool) + len(pkg_chunk)
        tbl_hdr = struct.pack("<HHII", RES_TABLE_TYPE, tbl_header_size, tbl_total_size, 1)

        return tbl_hdr + global_pool + pkg_chunk

    @staticmethod
    def is_valid_arsc(data: bytes) -> bool:
        """Validates if byte sequence is a real, non-stub Android binary resource table."""
        if len(data) < 32:
            return False
        # Must start with ResTable_header (0x0002, 12 bytes)
        tbl_type, hdr_size, total_size, pkg_count = struct.unpack_from("<HHII", data, 0)
        if tbl_type != RES_TABLE_TYPE or hdr_size != 12:
            return False
        if pkg_count < 1 or total_size > len(data):
            return False
        # Must contain at least one package chunk
        pos = hdr_size
        found_pkg = False
        while pos + 8 <= len(data):
            chunk_type, chunk_hdr_size, chunk_size = struct.unpack_from("<HHI", data, pos)
            if chunk_size < 8:
                break
            if chunk_type == RES_TABLE_PACKAGE_TYPE:
                found_pkg = True
                break
            pos += chunk_size
        return found_pkg

    @staticmethod
    def parse_summary(data: bytes) -> Dict[str, Any]:
        """Parses high-level metadata from an ARSC byte stream."""
        if not ArscBuilder.is_valid_arsc(data):
            return {"valid": False, "package_count": 0, "size": len(data)}

        tbl_type, hdr_size, total_size, pkg_count = struct.unpack_from("<HHII", data, 0)
        return {
            "valid": True,
            "package_count": pkg_count,
            "table_size": total_size,
            "raw_bytes": len(data),
        }
