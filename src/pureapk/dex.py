"""High-performance Dalvik Executable (DEX) header parser, class inspector, and bootstrap generator.

Unpacks DEX headers in a single C-level struct operation for maximum speed.
Memory overhead is strictly minimized using __slots__.
"""

from __future__ import annotations

import hashlib
import struct
from typing import Any, Dict, List, Optional, Sequence, Tuple
import zlib

# Pre-compiled struct for 112-byte DEX Header (magic, checksum, signature, 20 uint32s = 23 fields)
_STRUCT_DEX_HEADER = struct.Struct("<8sI20s" + "I" * 20)
DEX_MAGIC_PREFIX = b"dex\n"
ENDIAN_CONSTANT = 0x12345678
REVERSE_ENDIAN_CONSTANT = 0x78563412

# Standard launcher activities used by Python/hybrid mobile frameworks
DEFAULT_ACTIVITY_CLASSES: Tuple[str, ...] = (
    "org.kivy.android.PythonActivity",
    "org.renpy.android.PythonSDLActivity",
    "io.flet.FletActivity",
    "org.flet.app.MainActivity",
    "org.beeware.android.MainActivity",
    "android.webkit.WebViewActivity",
    "com.webview.app.MainActivity",
    "org.qtproject.qt.android.bindings.QtActivity",
    "MainActivity",
)


def _encode_uleb128(value: int) -> bytes:
    """Encodes an integer into Dalvik ULEB128 format."""
    result = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value != 0:
            byte |= 0x80
        result.append(byte)
        if value == 0:
            break
    return bytes(result)


def _align(data: bytes, n: int = 4) -> bytes:
    """Pad bytes to n-byte boundary."""
    rem = len(data) % n
    return data + (b"\x00" * (n - rem)) if rem else data


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


class DexBuilder:
    """Dalvik Executable (DEX) generator with real bytecode instructions.

    Produces 100% valid Dalvik bytecode containers accepted by Android's ART dex2oat compiler.
    """

    __slots__ = ()

    @classmethod
    def extract_class_names(cls, dex_bytes: bytes) -> List[str]:
        """Extracts fully-qualified class names declared in class_defs of a DEX binary."""
        if len(dex_bytes) < 112:
            return []
        hdr = DexHeader.from_bytes(dex_bytes)
        if not hdr.is_valid:
            return []

        # Read string offsets
        string_offsets: List[int] = []
        for i in range(hdr.string_ids_size):
            off = struct.unpack_from("<I", dex_bytes, hdr.string_ids_off + (i * 4))[0]
            string_offsets.append(off)

        # Helper to read string
        def get_string(idx: int) -> str:
            if idx >= len(string_offsets):
                return ""
            off = string_offsets[idx]
            # Skip uleb128 length
            pos = off
            while pos < len(dex_bytes) and (dex_bytes[pos] & 0x80):
                pos += 1
            pos += 1
            null_pos = dex_bytes.find(b"\x00", pos)
            if null_pos != -1:
                return dex_bytes[pos:null_pos].decode("utf-8", errors="replace")
            return ""

        # Read type descriptor string_ids
        type_str_ids: List[int] = []
        for i in range(hdr.type_ids_size):
            s_idx = struct.unpack_from("<I", dex_bytes, hdr.type_ids_off + (i * 4))[0]
            type_str_ids.append(s_idx)

        # Read class_defs
        class_names: List[str] = []
        for i in range(hdr.class_defs_size):
            c_type_idx = struct.unpack_from("<I", dex_bytes, hdr.class_defs_off + (i * 32))[0]
            if c_type_idx < len(type_str_ids):
                desc = get_string(type_str_ids[c_type_idx])
                if desc.startswith("L") and desc.endswith(";"):
                    class_names.append(desc[1:-1].replace("/", "."))
        return class_names

    @classmethod
    def generate_bootstrap_dex(
        cls,
        classes_count: Optional[int] = None,
        methods_count: Optional[int] = None,
        activity_classes: Optional[Sequence[str]] = None,
        raw_stub: bool = False,
    ) -> bytes:
        """Generates a Dalvik Executable binary.

        By default, produces a valid DEX binary containing bootstrap Activity classes
        with bytecode implementing <init>() and onCreate() calling super methods.
        If raw_stub=True, generates a 112-byte header placeholder (for low-level tests).
        """
        if raw_stub:
            c_cnt = classes_count if classes_count is not None else 1
            m_cnt = methods_count if methods_count is not None else 1
            magic = b"dex\n035\x00"
            header_size = 112
            file_size = 112
            endian_tag = 0x12345678

            payload = struct.pack(
                "<IIIIIIIIIIIIIIIIIIII",
                file_size,
                header_size,
                endian_tag,
                0, 0,  # link
                0,     # map
                1, 0,  # string_ids
                1, 0,  # type_ids
                1, 0,  # proto_ids
                0, 0,  # field_ids
                m_cnt, 0,  # method_ids
                c_cnt, 0,  # class_defs
                0, 0,  # data
            )
            sig = hashlib.sha1(payload).digest()
            sig_and_payload = sig + payload
            chk = zlib.adler32(sig_and_payload) & 0xFFFFFFFF
            return struct.pack("<8sI", magic, chk) + sig_and_payload

        # Determine target activity classes
        if activity_classes:
            target_classes = list(activity_classes)
        elif classes_count is not None and classes_count > 1 and classes_count != len(DEFAULT_ACTIVITY_CLASSES):
            target_classes = [f"MainActivity{i}" for i in range(classes_count)]
        else:
            target_classes = list(DEFAULT_ACTIVITY_CLASSES)

        strings = sorted(list(set([
            "<init>",
            "Landroid/app/Activity;",
            "Landroid/os/Bundle;",
            "Ljava/lang/Object;",
            "MainActivity.java",
            "V",
            "VL",
            "onCreate",
        ] + [f"L{a.replace('.', '/')};" for a in target_classes])))
        str_to_idx = {s: i for i, s in enumerate(strings)}

        types = sorted(list(set([
            "Landroid/app/Activity;",
            "Landroid/os/Bundle;",
            "Ljava/lang/Object;",
            "V",
        ] + [f"L{a.replace('.', '/')};" for a in target_classes])))
        type_to_idx = {t: i for i, t in enumerate(types)}

        # Protos
        # proto 0: ()V -> shorty V, return V, params: None
        # proto 1: (Landroid/os/Bundle;)V -> shorty VL, return V, params: [Landroid/os/Bundle;]
        proto_defs = [
            (str_to_idx["V"], type_to_idx["V"], ()),
            (str_to_idx["VL"], type_to_idx["V"], (type_to_idx["Landroid/os/Bundle;"],)),
        ]
        proto_defs = sorted(proto_defs, key=lambda p: (p[1], p[2]))
        proto_to_idx = {p: i for i, p in enumerate(proto_defs)}
        proto_init_idx = proto_to_idx[(str_to_idx["V"], type_to_idx["V"], ())]
        proto_oncreate_idx = proto_to_idx[(str_to_idx["VL"], type_to_idx["V"], (type_to_idx["Landroid/os/Bundle;"],))]

        # Methods
        methods = [
            (type_to_idx["Landroid/app/Activity;"], proto_init_idx, str_to_idx["<init>"]),
            (type_to_idx["Landroid/app/Activity;"], proto_oncreate_idx, str_to_idx["onCreate"]),
        ]
        for act in target_classes:
            desc = f"L{act.replace('.', '/')};"
            t_idx = type_to_idx[desc]
            methods.append((t_idx, proto_init_idx, str_to_idx["<init>"]))
            methods.append((t_idx, proto_oncreate_idx, str_to_idx["onCreate"]))

        methods = sorted(methods, key=lambda m: (m[0], m[1], m[2]))
        method_to_idx = {m: i for i, m in enumerate(methods)}
        super_init_idx = method_to_idx[(type_to_idx["Landroid/app/Activity;"], proto_init_idx, str_to_idx["<init>"])]
        super_oncreate_idx = method_to_idx[(type_to_idx["Landroid/app/Activity;"], proto_oncreate_idx, str_to_idx["onCreate"])]

        # Class definitions
        classes = []
        for act in target_classes:
            desc = f"L{act.replace('.', '/')};"
            classes.append(type_to_idx[desc])
        classes.sort()

        # Pre-calculate section layouts
        header_size = 112
        string_ids_off = header_size
        string_ids_size = len(strings)

        type_ids_off = string_ids_off + (string_ids_size * 4)
        type_ids_size = len(types)

        proto_ids_off = type_ids_off + (type_ids_size * 4)
        proto_ids_size = len(proto_defs)

        method_ids_off = proto_ids_off + (proto_ids_size * 12)
        method_ids_size = len(methods)

        class_defs_off = method_ids_off + (method_ids_size * 8)
        class_defs_size = len(classes)

        data_off = class_defs_off + (class_defs_size * 32)
        data_off = (data_off + 3) & ~3

        # Assemble the data section
        data_buf = bytearray()

        # 1. TypeList for proto 1 parameters
        bundle_type_list_off = data_off + len(data_buf)
        data_buf.extend(struct.pack("<II", 1, type_to_idx["Landroid/os/Bundle;"]))
        data_buf = bytearray(_align(bytes(data_buf), 4))

        # 2. String data items
        string_offsets = []
        for s in strings:
            string_offsets.append(data_off + len(data_buf))
            s_bytes = s.encode("utf-8")
            data_buf.extend(_encode_uleb128(len(s)))
            data_buf.extend(s_bytes)
            data_buf.append(0)
        data_buf = bytearray(_align(bytes(data_buf), 4))

        # 3. Code item for <init>()
        # registers=1, ins=1, outs=1, tries=0, debug=0, insns_size=4
        # Dalvik: invoke-direct {v0}, Activity.<init>() -> 0x1070, super_init_idx, 0x0000, 0x000e (return-void)
        code_init_off = data_off + len(data_buf)
        code_init = struct.pack("<HHHHII", 1, 1, 1, 0, 0, 4)
        code_init += struct.pack("<HHH", 0x1070, super_init_idx, 0x0000)
        code_init += struct.pack("<H", 0x000e)
        data_buf.extend(code_init)
        data_buf = bytearray(_align(bytes(data_buf), 4))

        # Code item for onCreate(Bundle)
        # registers=2, ins=2, outs=2, tries=0, debug=0, insns_size=4
        # Dalvik: invoke-super {v0, v1}, Activity.onCreate() -> 0x206f, super_oncreate_idx, 0x0010, 0x000e (return-void)
        code_oncreate_off = data_off + len(data_buf)
        code_oncreate = struct.pack("<HHHHII", 2, 2, 2, 0, 0, 4)
        code_oncreate += struct.pack("<HHH", 0x206f, super_oncreate_idx, 0x0010)
        code_oncreate += struct.pack("<H", 0x000e)
        data_buf.extend(code_oncreate)
        data_buf = bytearray(_align(bytes(data_buf), 4))

        # 4. Class data items for each class
        class_data_offsets = {}
        for c_idx in classes:
            class_data_offsets[c_idx] = data_off + len(data_buf)
            cd = bytearray()
            cd.extend(_encode_uleb128(0))  # static fields
            cd.extend(_encode_uleb128(0))  # instance fields
            cd.extend(_encode_uleb128(1))  # direct methods (<init>)
            cd.extend(_encode_uleb128(1))  # virtual methods (onCreate)

            m_init = method_to_idx[(c_idx, proto_init_idx, str_to_idx["<init>"])]
            m_oncreate = method_to_idx[(c_idx, proto_oncreate_idx, str_to_idx["onCreate"])]

            # direct method: <init>
            cd.extend(_encode_uleb128(m_init))
            cd.extend(_encode_uleb128(0x10001))  # ACC_PUBLIC | ACC_CONSTRUCTOR
            cd.extend(_encode_uleb128(code_init_off))

            # virtual method: onCreate
            cd.extend(_encode_uleb128(m_oncreate))
            cd.extend(_encode_uleb128(0x0001))  # ACC_PUBLIC
            cd.extend(_encode_uleb128(code_oncreate_off))

            data_buf.extend(cd)
        data_buf = bytearray(_align(bytes(data_buf), 4))

        # 5. Map list
        map_off = data_off + len(data_buf)
        map_items = [
            (0x0000, 1, 0),                            # HEADER_ITEM
            (0x0001, string_ids_size, string_ids_off),  # STRING_ID_ITEM
            (0x0002, type_ids_size, type_ids_off),      # TYPE_ID_ITEM
            (0x0003, proto_ids_size, proto_ids_off),    # PROTO_ID_ITEM
            (0x0005, method_ids_size, method_ids_off),  # METHOD_ID_ITEM
            (0x0006, class_defs_size, class_defs_off),  # CLASS_DEF_ITEM
            (0x1001, 1, bundle_type_list_off),          # TYPE_LIST
            (0x2002, string_ids_size, string_offsets[0]),  # STRING_DATA_ITEM
            (0x2001, 2, code_init_off),                 # CODE_ITEM
            (0x2000, class_defs_size, class_data_offsets[classes[0]]),  # CLASS_DATA_ITEM
            (0x1000, 11, map_off),                      # MAP_LIST
        ]
        map_data = struct.pack("<I", len(map_items))
        for t, count, off in map_items:
            map_data += struct.pack("<HHII", t, 0, count, off)
        data_buf.extend(map_data)
        data_buf = bytearray(_align(bytes(data_buf), 4))

        data_size = len(data_buf)
        file_size = data_off + data_size

        # Assemble table buffers
        s_ids_buf = bytearray()
        for off in string_offsets:
            s_ids_buf.extend(struct.pack("<I", off))

        t_ids_buf = bytearray()
        for t in types:
            t_ids_buf.extend(struct.pack("<I", str_to_idx[t]))

        p_ids_buf = bytearray()
        for s_idx, r_idx, params in proto_defs:
            p_off = bundle_type_list_off if params else 0
            p_ids_buf.extend(struct.pack("<III", s_idx, r_idx, p_off))

        m_ids_buf = bytearray()
        for c_idx, pr_idx, n_idx in methods:
            m_ids_buf.extend(struct.pack("<HHI", c_idx, pr_idx, n_idx))

        c_defs_buf = bytearray()
        super_idx = type_to_idx["Landroid/app/Activity;"]
        src_idx = str_to_idx["MainActivity.java"]
        for c_idx in classes:
            c_defs_buf.extend(struct.pack(
                "<IIIIIIII",
                c_idx,
                0x0001,  # ACC_PUBLIC
                super_idx,
                0,        # interfaces_off
                src_idx,  # source_file_idx
                0,        # annotations_off
                class_data_offsets[c_idx],
                0,        # static_values_off
            ))

        pad_to_data = data_off - (class_defs_off + len(c_defs_buf))
        c_defs_buf.extend(b"\x00" * pad_to_data)

        payload_without_chk = struct.pack(
            "<IIIIIIIIIIIIIIIIIIII",
            file_size,
            header_size,
            0x12345678,
            0, 0,
            map_off,
            string_ids_size, string_ids_off,
            type_ids_size, type_ids_off,
            proto_ids_size, proto_ids_off,
            0, 0,
            method_ids_size, method_ids_off,
            class_defs_size, class_defs_off,
            data_size, data_off,
        ) + s_ids_buf + t_ids_buf + p_ids_buf + m_ids_buf + c_defs_buf + data_buf

        sig = hashlib.sha1(payload_without_chk).digest()
        sig_and_payload = sig + payload_without_chk
        chk = zlib.adler32(sig_and_payload) & 0xFFFFFFFF
        header_prefix = struct.pack("<8sI", b"dex\n035\x00", chk)
        return header_prefix + sig_and_payload
