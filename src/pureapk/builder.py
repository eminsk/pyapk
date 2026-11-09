"""High-performance APK builder and packager with 4-byte and 16KB alignment support.

Pure Python, zero-dependency APK creator compatible with all operating systems.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
import struct
from typing import BinaryIO, Dict, Iterable, List, Optional, Tuple, Union
import zipfile

# File extensions that should remain uncompressed for Android runtime efficiency
UNCOMPRESSED_EXTS: Tuple[str, ...] = (
    ".arsc",
    ".so",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".ogg",
    ".mp3",
    ".mp4",
)


def align_zip_entry(
    curr_offset: int,
    filename: str,
    extra: bytes,
    align: int,
) -> bytes:
    """Calculates padding and returns updated extra field ensuring data is aligned to `align` bytes."""
    if align <= 1:
        return extra
    fn_bytes = filename.encode("utf-8")
    unaligned_offset = curr_offset + 30 + len(fn_bytes) + len(extra)
    rem = unaligned_offset % align
    if rem == 0:
        return extra
    pad = align - rem
    if pad < 4:
        pad += align
    # ZIP Extra Field block: Tag 0xd935 (Android alignment), 2-byte length, then null padding
    return extra + struct.pack("<HH", 0xd935, pad - 4) + (b"\x00" * (pad - 4))


class APKBuilder:
    """Builder class for creating Android APK packages."""

    __slots__ = (
        "_output_path",
        "_entries",
        "_uncompressed_exts",
        "_auto_axml",
        "_auto_dex",
        "_auto_resources",
        "_sign",
        "_compile_py",
        "_alignment",
        "_so_alignment",
    )

    def __init__(
        self,
        output_path: Union[str, Path, BinaryIO],
        uncompressed_exts: Tuple[str, ...] = UNCOMPRESSED_EXTS,
        auto_axml: bool = False,
        auto_dex: bool = False,
        auto_resources: bool = False,
        sign: bool = False,
        compile_py: bool = False,
        alignment: int = 4,
        so_alignment: int = 16384,
    ) -> None:
        self._output_path = output_path
        self._entries: List[Tuple[str, bytes, int]] = []
        self._uncompressed_exts = tuple(map(str.lower, uncompressed_exts))
        self._auto_axml = auto_axml
        self._auto_dex = auto_dex
        self._auto_resources = auto_resources
        self._sign = sign
        self._compile_py = compile_py
        self._alignment = alignment
        self._so_alignment = so_alignment

    def add_bytes(self, archive_name: str, data: bytes, compress: Optional[bool] = None) -> APKBuilder:
        norm_name = archive_name.replace("\\", "/").lstrip("/")

        # Auto-compile text AndroidManifest.xml into binary AXML
        final_data = data
        if self._auto_axml and norm_name == "AndroidManifest.xml" and data.strip().startswith(b"<"):
            try:
                from pureapk.manifest import AxmlEncoder
                final_data = AxmlEncoder.encode(data)
            except Exception:
                final_data = data

        ext = os.path.splitext(norm_name)[1].lower()

        # Compression selection without if-else
        should_compress = {
            True: lambda: compress,
            False: lambda: ext not in self._uncompressed_exts,
        }[compress is not None]()

        compression_type = {
            True: zipfile.ZIP_DEFLATED,
            False: zipfile.ZIP_STORED,
        }[bool(should_compress)]

        self._entries.append((norm_name, final_data, compression_type))
        return self

    def add_file(self, local_path: Union[str, Path], archive_name: Optional[str] = None, compress: Optional[bool] = None) -> APKBuilder:
        path_obj = Path(local_path)
        arc_name = archive_name or path_obj.name
        with open(path_obj, "rb") as f:
            data = f.read()

        # Optional python compilation to bytecode .pyc
        if self._compile_py and arc_name.endswith(".py"):
            try:
                code_obj = compile(data, arc_name, "exec")
                import importlib._bootstrap_external
                pyc_data = importlib._bootstrap_external._code_to_timestamp_pyc(code_obj)
                self.add_bytes(f"{arc_name}c", pyc_data)
            except Exception:
                pass

        return self.add_bytes(arc_name, data, compress=compress)

    def add_directory(self, local_dir: Union[str, Path], prefix: str = "", compress: Optional[bool] = None) -> APKBuilder:
        base = Path(local_dir)
        for root, _, files in os.walk(base):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(base)
                arc_path = f"{prefix}/{rel_path}".lstrip("/") if prefix else str(rel_path)
                self.add_file(full_path, arc_path, compress=compress)
        return self

    def build(self) -> None:
        """Writes the aligned APK archive, injecting bootstrap runtime & signatures if requested."""
        existing_names = {name for name, _, _ in self._entries}

        # Auto-inject bootstrap DEX if missing
        if self._auto_dex and not any(name.endswith(".dex") for name in existing_names):
            from pureapk.dex import DexBuilder
            dex_bytes = DexBuilder.generate_bootstrap_dex()
            self._entries.append(("classes.dex", dex_bytes, zipfile.ZIP_DEFLATED))

        # Auto-inject resources.arsc table if missing
        if self._auto_resources and "resources.arsc" not in existing_names:
            arsc_bytes = struct.pack("<HHII", 0x0002, 12, 12, 0)
            self._entries.append(("resources.arsc", arsc_bytes, zipfile.ZIP_STORED))

        buf = io.BytesIO() if self._sign else self._output_path
        with zipfile.ZipFile(buf, "w") as zf:
            for arc_name, data, comp_type in self._entries:
                info = zipfile.ZipInfo(arc_name)
                info.compress_type = comp_type
                info.external_attr = 0o644 << 16  # standard file permissions
                if comp_type == zipfile.ZIP_STORED:
                    align = self._so_alignment if arc_name.endswith(".so") else self._alignment
                    info.extra = align_zip_entry(zf.fp.tell(), arc_name, info.extra, align)
                zf.writestr(info, data)

        if self._sign and isinstance(buf, io.BytesIO):
            from pureapk.signature import APKSigner
            unsigned_apk = buf.getvalue()
            signed_apk = APKSigner.sign_apk_bytes(
                unsigned_apk,
                alignment=self._alignment,
                so_alignment=self._so_alignment,
            )
            if isinstance(self._output_path, (str, Path)):
                Path(self._output_path).write_bytes(signed_apk)
            elif hasattr(self._output_path, "write"):
                self._output_path.write(signed_apk)


def pack(
    source_dir: Union[str, Path],
    output_apk: Union[str, Path],
    sign: bool = False,
    auto_axml: bool = False,
    auto_dex: bool = False,
    auto_resources: bool = False,
    compile_py: bool = False,
    alignment: int = 4,
    so_alignment: int = 16384,
) -> None:
    """Convenience helper to pack a directory into an APK."""
    builder = APKBuilder(
        output_apk,
        auto_axml=auto_axml,
        auto_dex=auto_dex,
        auto_resources=auto_resources,
        sign=sign,
        compile_py=compile_py,
        alignment=alignment,
        so_alignment=so_alignment,
    )
    builder.add_directory(source_dir)
    builder.build()


def zipalign(
    input_apk: Union[str, Path, bytes, BinaryIO],
    output_apk: Union[str, Path, BinaryIO],
    alignment: int = 4,
    so_alignment: int = 16384,
    file_alignment: Optional[int] = None,
    sign: bool = False,
) -> None:
    """Aligns an APK to 4-byte boundaries (and 16384-byte boundaries for uncompressed .so libraries)."""
    raw_bytes: bytes
    if isinstance(input_apk, (str, Path)):
        raw_bytes = Path(input_apk).read_bytes()
    elif isinstance(input_apk, bytes):
        raw_bytes = input_apk
    else:
        raw_bytes = input_apk.read()

    base_align = file_alignment if file_alignment is not None else alignment
    in_zf = zipfile.ZipFile(io.BytesIO(raw_bytes), "r")
    out_buf = io.BytesIO()
    with zipfile.ZipFile(out_buf, "w") as out_zf:
        for info in in_zf.infolist():
            data = in_zf.read(info.filename)
            new_info = zipfile.ZipInfo(info.filename)
            new_info.compress_type = info.compress_type
            new_info.external_attr = info.external_attr or (0o644 << 16)
            new_info.extra = b""
            if new_info.compress_type == zipfile.ZIP_STORED:
                align = so_alignment if info.filename.endswith(".so") else base_align
                new_info.extra = align_zip_entry(out_zf.fp.tell(), info.filename, new_info.extra, align)
            out_zf.writestr(new_info, data)

    aligned_bytes = out_buf.getvalue()
    if sign:
        from pureapk.signature import APKSigner
        aligned_bytes = APKSigner.sign_apk_bytes(aligned_bytes, alignment=base_align, so_alignment=so_alignment)

    if isinstance(output_apk, (str, Path)):
        Path(output_apk).write_bytes(aligned_bytes)
    elif hasattr(output_apk, "write"):
        output_apk.write(aligned_bytes)
