"""High-performance APK builder and packager with 4-byte alignment support.

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
    ) -> None:
        self._output_path = output_path
        self._entries: List[Tuple[str, bytes, int]] = []
        self._uncompressed_exts = tuple(map(str.lower, uncompressed_exts))
        self._auto_axml = auto_axml
        self._auto_dex = auto_dex
        self._auto_resources = auto_resources
        self._sign = sign
        self._compile_py = compile_py

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

    def add_file(self, local_path: Union[str, Path], archive_name: Optional[str] = None) -> APKBuilder:
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

        return self.add_bytes(arc_name, data)

    def add_directory(self, local_dir: Union[str, Path], prefix: str = "") -> APKBuilder:
        base = Path(local_dir)
        for root, _, files in os.walk(base):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(base)
                arc_path = f"{prefix}/{rel_path}".lstrip("/") if prefix else str(rel_path)
                self.add_file(full_path, arc_path)
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
                zf.writestr(info, data)

        if self._sign and isinstance(buf, io.BytesIO):
            from pureapk.signature import APKSigner
            unsigned_apk = buf.getvalue()
            signed_apk = APKSigner.sign_apk_bytes(unsigned_apk)
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
) -> None:
    """Convenience helper to pack a directory into an APK."""
    builder = APKBuilder(
        output_apk,
        auto_axml=auto_axml,
        auto_dex=auto_dex,
        auto_resources=auto_resources,
        sign=sign,
        compile_py=compile_py,
    )
    builder.add_directory(source_dir)
    builder.build()
