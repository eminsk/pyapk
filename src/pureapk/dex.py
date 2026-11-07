"""High-performance Dalvik Executable (DEX) header parser and multi-dex analyzer.

Unpacks DEX headers in a single C-level struct operation for maximum speed.
Memory overhead is strictly minimized using __slots__.
"""

from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Pre-compiled struct for 112-byte DEX Header (magic, checksum, signature, 20 uint32s = 23 fields)
_STRUCT_DEX_HEADER = struct.Struct("<8sI20s" + "I" * 20)
DEX_MAGIC_PREFIX = b"dex\n"
ENDIAN_CONSTANT = 0x12345678
REVERSE_ENDIAN_CONSTANT = 0x78563412


class DexHeader:
    """Parsed Dalvik Executable (DEX) header."""

    __slots__ = (
        "magic",
        "version",
        "checksum",
        "signature",
        "file_size",
        "header_size",
        "endian_tag",
        "link_size",
        "link_off",
        "map_off",
        "string_ids_size",
        "string_ids_off",
        "type_ids_size",
        "type_ids_off",
        "proto_ids_size",
        "proto_ids_off",
        "field_ids_size",
        "field_ids_off",
        "method_ids_size",
        "method_ids_off",
        "class_defs_size",
        "class_defs_off",
        "data_size",
        "data_off",
        "is_valid",
    )

    def __init__(
        self,
        magic: bytes,
        version: str,
        checksum: int,
        signature: bytes,
        file_size: int,
        header_size: int,
        endian_tag: int,
        link_size: int,
        link_off: int,
        map_off: int,
        string_ids_size: int,
        string_ids_off: int,
        type_ids_size: int,
        type_ids_off: int,
        proto_ids_size: int,
        proto_ids_off: int,
        field_ids_size: int,
        field_ids_off: int,
        method_ids_size: int,
        method_ids_off: int,
        class_defs_size: int,
        class_defs_off: int,
        data_size: int,
        data_off: int,
        is_valid: bool = True,
    ) -> None:
        self.magic = magic
        self.version = version
        self.checksum = checksum
        self.signature = signature
        self.file_size = file_size
        self.header_size = header_size
        self.endian_tag = endian_tag
        self.link_size = link_size
        self.link_off = link_off
        self.map_off = map_off
        self.string_ids_size = string_ids_size
        self.string_ids_off = string_ids_off
        self.type_ids_size = type_ids_size
        self.type_ids_off = type_ids_off
        self.proto_ids_size = proto_ids_size
        self.proto_ids_off = proto_ids_off
        self.field_ids_size = field_ids_size
        self.field_ids_off = field_ids_off
        self.method_ids_size = method_ids_size
        self.method_ids_off = method_ids_off
        self.class_defs_size = class_defs_size
        self.class_defs_off = class_defs_off
        self.data_size = data_size
        self.data_off = data_off
        self.is_valid = is_valid

    @property
    def signature_hex(self) -> str:
        return self.signature.hex()

    def as_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "checksum": self.checksum,
            "signature": self.signature_hex,
            "file_size": self.file_size,
            "classes_count": self.class_defs_size,
            "methods_count": self.method_ids_size,
            "fields_count": self.field_ids_size,
            "strings_count": self.string_ids_size,
            "types_count": self.type_ids_size,
            "prototypes_count": self.proto_ids_size,
            "is_valid": self.is_valid,
        }

    @classmethod
    def from_bytes(cls, data: bytes) -> DexHeader:
        is_sufficient = len(data) >= _STRUCT_DEX_HEADER.size
        handler = {
            True: lambda: cls._parse_raw(data),
            False: cls._create_invalid,
        }[is_sufficient]
        return handler()

    @classmethod
    def _create_invalid(cls) -> DexHeader:
        return cls(
            magic=b"",
            version="",
            checksum=0,
            signature=b"",
            file_size=0,
            header_size=0,
            endian_tag=0,
            link_size=0,
            link_off=0,
            map_off=0,
            string_ids_size=0,
            string_ids_off=0,
            type_ids_size=0,
            type_ids_off=0,
            proto_ids_size=0,
            proto_ids_off=0,
            field_ids_size=0,
            field_ids_off=0,
            method_ids_size=0,
            method_ids_off=0,
            class_defs_size=0,
            class_defs_off=0,
            data_size=0,
            data_off=0,
            is_valid=False,
        )

    @classmethod
    def _parse_raw(cls, data: bytes) -> DexHeader:
        fields = _STRUCT_DEX_HEADER.unpack_from(data, 0)
        magic_bytes = fields[0]
        has_magic = magic_bytes.startswith(DEX_MAGIC_PREFIX)
        version_str = magic_bytes[4:7].decode("ascii", errors="replace") if has_magic else ""
        return cls(
            magic=magic_bytes,
            version=version_str,
            checksum=fields[1],
            signature=fields[2],
            file_size=fields[3],
            header_size=fields[4],
            endian_tag=fields[5],
            link_size=fields[6],
            link_off=fields[7],
            map_off=fields[8],
            string_ids_size=fields[9],
            string_ids_off=fields[10],
            type_ids_size=fields[11],
            type_ids_off=fields[12],
            proto_ids_size=fields[13],
            proto_ids_off=fields[14],
            field_ids_size=fields[15],
            field_ids_off=fields[16],
            method_ids_size=fields[17],
            method_ids_off=fields[18],
            class_defs_size=fields[19],
            class_defs_off=fields[20],
            data_size=fields[21],
            data_off=fields[22],
            is_valid=has_magic,
        )


class MultiDexSummary:
    """Aggregated statistics across all DEX files in an APK."""

    __slots__ = (
        "dex_count",
        "total_classes",
        "total_methods",
        "total_fields",
        "total_strings",
        "total_dex_bytes",
        "headers",
    )

    def __init__(self, headers: Sequence[DexHeader]) -> None:
        self.headers = tuple(headers)
        self.dex_count = len(headers)
        self.total_classes = sum(map(lambda h: h.class_defs_size, headers))
        self.total_methods = sum(map(lambda h: h.method_ids_size, headers))
        self.total_fields = sum(map(lambda h: h.field_ids_size, headers))
        self.total_strings = sum(map(lambda h: h.string_ids_size, headers))
        self.total_dex_bytes = sum(map(lambda h: h.file_size, headers))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "dex_count": self.dex_count,
            "total_classes": self.total_classes,
            "total_methods": self.total_methods,
            "total_fields": self.total_fields,
            "total_strings": self.total_strings,
            "total_dex_bytes": self.total_dex_bytes,
            "files": list(map(lambda h: h.as_dict(), self.headers)),
        }
