"""Android binary resource table (resources.arsc) generator, patcher, and validator.

Pure Python implementation of Android's ResTable binary format.
Strict memory overhead control using __slots__.
"""

from __future__ import annotations

import hashlib
import re
import struct
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
TYPE_INT_COLOR_ARGB8 = 0x1C
TYPE_INT_COLOR_RGB8 = 0x1D


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
            u16_len = len(s.encode("utf-16le")) // 2
            u8_len = len(s_bytes)
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
            u16_len = len(s_bytes) // 2
            encoded_len = bytearray()
            if u16_len > 0x7FFF:
                encoded_len.extend(struct.pack("<HH", ((u16_len >> 16) & 0x7FFF) | 0x8000, u16_len & 0xFFFF))
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


def _parse_string_pool_chunk(data: bytes, offset: int) -> Tuple[List[str], bool, int]:
    """Parses a ResStringPool chunk at ``offset`` and returns (strings, is_utf8, chunk_size)."""
    from pureapk.manifest import StringPool

    view = memoryview(data)
    sp_hdr = struct.unpack_from("<HHIIIIII", view, offset)
    hdr_size, chunk_size, str_count, _, flags, str_start, _ = (
        sp_hdr[1],
        sp_hdr[2],
        sp_hdr[3],
        sp_hdr[4],
        sp_hdr[5],
        sp_hdr[6],
        sp_hdr[7],
    )
    is_utf8 = bool(flags & 0x100)
    offsets = struct.unpack_from(f"<{str_count}I", view, offset + hdr_size) if str_count else ()
    sp = StringPool(view, is_utf8, offsets, offset + str_start)
    strings = [sp.get(i) for i in range(str_count)]
    return strings, is_utf8, chunk_size


class ArscBuilder:
    """100% valid Android binary resource table (resources.arsc) generator, patcher, and validator."""

    __slots__ = ()

    @staticmethod
    def generate_minimal_arsc(
        package_name: str = "org.pureapk.app",
        app_name: str = "PureAPK App",
        private_version: Optional[str] = None,
    ) -> bytes:
        """Generates a minimal valid resources.arsc table accepted by Android's PackageParser and aapt2/ARSCParser.

        Includes:
        - Global string pool containing app_name, presplash_color, private_version, and urlScheme.
        - 288-byte ResTable_package header (with typeIdOffset) with id 0x7F and package name.
        - Type string pool with 'string'.
        - Key string pool with 'app_name', 'presplash_color', 'private_version', 'urlScheme'.
        - ResTable_typeSpec chunk.
        - ResTable_type chunk with valid 64-byte ResTable_config (size=64).
        """
        ver_str = private_version or ("0" * 40)
        if len(ver_str) != 40 or not re.fullmatch(r"[0-9a-f]{40}", ver_str):
            ver_str = hashlib.sha1(ver_str.encode("utf-8")).hexdigest()

        # 1. Global string pool (UTF-8)
        global_strings = [app_name, "#000000", ver_str, "kivy"]
        global_pool = _build_string_pool(global_strings, utf8=True)

        # 2. Package Chunk
        type_pool = _build_string_pool(["string"], utf8=True)
        key_names = ["app_name", "presplash_color", "private_version", "urlScheme"]
        key_pool = _build_string_pool(key_names, utf8=True)

        pkg_header_size = 288
        type_strings_off = pkg_header_size
        key_strings_off = type_strings_off + len(type_pool)

        entry_count = len(key_names)
        type_spec_size = 16 + (entry_count * 4)
        type_spec = struct.pack(
            "<HHI BBH I",
            RES_TABLE_TYPE_SPEC_TYPE,
            16,
            type_spec_size,
            1,  # id = 1 ('string')
            0,
            0,
            entry_count,
        )
        type_spec += struct.pack(f"<{entry_count}I", *([0] * entry_count))

        # ResTable_type chunk (20-byte header + 64-byte ResTable_config = 84 bytes)
        entries_start = 84 + (entry_count * 4)
        entries_blob = bytearray()
        entry_offsets_list: List[int] = []
        for idx in range(entry_count):
            entry_offsets_list.append(len(entries_blob))
            res_entry = struct.pack("<HHI", 8, 0, idx)
            res_val = struct.pack("<HBB I", 8, 0, TYPE_STRING, idx)
            entries_blob.extend(res_entry + res_val)

        entry_offsets = struct.pack(f"<{entry_count}I", *entry_offsets_list)
        type_chunk_size = entries_start + len(entries_blob)

        # First 4 bytes of ResTable_config is uint32 size = 64
        config = struct.pack("<I", 64) + (b"\x00" * 60)
        type_chunk_hdr = struct.pack(
            "<HHI BBH II",
            RES_TABLE_TYPE_TYPE,
            84,
            type_chunk_size,
            1,  # id = 1 ('string')
            0,
            0,
            entry_count,
            entries_start,
        )
        type_chunk = type_chunk_hdr + config + entry_offsets + bytes(entries_blob)

        pkg_body = type_pool + key_pool + type_spec + type_chunk
        pkg_total_size = pkg_header_size + len(pkg_body)

        pkg_name_bytes = package_name.encode("utf-16le").ljust(256, b"\x00")[:256]
        # 288-byte ResTable_package header includes trailing uint32 typeIdOffset = 0
        pkg_hdr = struct.pack(
            "<HHI I 256s II II I",
            RES_TABLE_PACKAGE_TYPE,
            pkg_header_size,
            pkg_total_size,
            0x7F,  # Application package ID
            pkg_name_bytes,
            type_strings_off,
            1,  # lastPublicType
            key_strings_off,
            entry_count,  # lastPublicKey
            0,  # typeIdOffset
        )
        pkg_chunk = pkg_hdr + pkg_body

        # 3. Main table header (12 bytes)
        tbl_header_size = 12
        tbl_total_size = tbl_header_size + len(global_pool) + len(pkg_chunk)
        tbl_hdr = struct.pack("<HHII", RES_TABLE_TYPE, tbl_header_size, tbl_total_size, 1)

        return tbl_hdr + global_pool + pkg_chunk

    @staticmethod
    def patch_arsc(
        arsc_bytes: bytes,
        package_name: Optional[str] = None,
        app_name: Optional[str] = None,
        private_version: Optional[str] = None,
    ) -> bytes:
        """Patches package_name, app_name, and/or private_version inside a binary resources.arsc table."""
        if not ArscBuilder.is_valid_arsc(arsc_bytes):
            return arsc_bytes

        data = bytearray(arsc_bytes)
        global_strings, is_utf8, sp_size = _parse_string_pool_chunk(bytes(data), 12)
        pkg_pos = 12 + sp_size
        if pkg_pos + 284 > len(data):
            return bytes(data)

        pkg_type, pkg_hdr_size, pkg_size = struct.unpack_from("<HHI", data, pkg_pos)
        if pkg_type != RES_TABLE_PACKAGE_TYPE:
            return bytes(data)

        # 1. Patch 256-byte UTF-16LE package name in ResTable_package header
        if package_name:
            pkg_name_bytes = package_name.encode("utf-16le").ljust(256, b"\x00")[:256]
            data[pkg_pos + 12 : pkg_pos + 268] = pkg_name_bytes

        # 2. Locate key indices for app_name and private_version inside ResTable_package
        type_strings_off, _, key_strings_off, _ = struct.unpack_from("<IIII", data, pkg_pos + 268)
        key_strings, _, key_sp_size = _parse_string_pool_chunk(bytes(data), pkg_pos + key_strings_off)

        key_to_global_idx: Dict[str, int] = {}
        sub_pos = pkg_pos + key_strings_off + key_sp_size
        pkg_end = min(len(data), pkg_pos + pkg_size)
        while sub_pos + 8 <= pkg_end:
            ct, chs, cs = struct.unpack_from("<HHI", data, sub_pos)
            if cs < 8 or sub_pos + cs > pkg_end:
                break
            if ct == RES_TABLE_TYPE_TYPE and sub_pos + chs <= pkg_end:
                entry_count, entries_start = struct.unpack_from("<II", data, sub_pos + 12)
                for i in range(entry_count):
                    off_pos = sub_pos + chs + i * 4
                    if off_pos + 4 > sub_pos + entries_start:
                        break
                    e_off = struct.unpack_from("<i", data, off_pos)[0]
                    if e_off < 0:
                        continue
                    e_pos = sub_pos + entries_start + e_off
                    if e_pos + 16 <= sub_pos + cs:
                        _, e_flags, key_idx = struct.unpack_from("<HHI", data, e_pos)
                        if (e_flags & 0x0001) == 0:  # non-complex entry
                            _, _, val_type, val_data = struct.unpack_from("<HBBI", data, e_pos + 8)
                            if val_type == TYPE_STRING and 0 <= key_idx < len(key_strings) and 0 <= val_data < len(global_strings):
                                key_to_global_idx[key_strings[key_idx]] = val_data
            sub_pos += cs

        modified_pool = False
        if app_name is not None and "app_name" in key_to_global_idx:
            global_strings[key_to_global_idx["app_name"]] = app_name
            modified_pool = True

        if private_version is not None:
            if "private_version" in key_to_global_idx:
                global_strings[key_to_global_idx["private_version"]] = private_version
                modified_pool = True

        if modified_pool:
            new_sp = _build_string_pool(global_strings, utf8=is_utf8)
            rest = bytes(data[pkg_pos:])
            total_size = 12 + len(new_sp) + len(rest)
            tbl_hdr = struct.pack("<HHII", RES_TABLE_TYPE, 12, total_size, 1)
            return tbl_hdr + new_sp + rest

        return bytes(data)

    @staticmethod
    def is_valid_arsc(data: bytes) -> bool:
        """Validates if byte sequence is a well-formed, non-stub Android binary resource table."""
        if len(data) < 32:
            return False
        tbl_type, hdr_size, total_size, pkg_count = struct.unpack_from("<HHII", data, 0)
        if tbl_type != RES_TABLE_TYPE or hdr_size != 12:
            return False
        if pkg_count < 1 or total_size != len(data):
            return False

        pos = hdr_size
        found_pkg = False
        while pos + 8 <= total_size:
            chunk_type, chunk_hdr_size, chunk_size = struct.unpack_from("<HHI", data, pos)
            if chunk_size < 8 or pos + chunk_size > total_size:
                return False
            if chunk_type == RES_TABLE_PACKAGE_TYPE:
                if chunk_hdr_size not in (284, 288) or pos + chunk_hdr_size > total_size:
                    return False
                type_off, _, key_off, _ = struct.unpack_from("<IIII", data, pos + 268)
                if type_off < chunk_hdr_size or key_off <= type_off or pos + key_off + 8 > pos + chunk_size:
                    return False
                found_pkg = True
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
