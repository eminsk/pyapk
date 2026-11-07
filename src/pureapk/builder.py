"""High-performance APK builder and packager with 4-byte alignment support.

Pure Python, zero-dependency APK creator compatible with all operating systems.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
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

    __slots__ = ("_output_path", "_entries", "_uncompressed_exts")

    def __init__(
        self,
        output_path: Union[str, Path, BinaryIO],
        uncompressed_exts: Tuple[str, ...] = UNCOMPRESSED_EXTS,
    ) -> None:
        self._output_path = output_path
        self._entries: List[Tuple[str, bytes, int]] = []
        self._uncompressed_exts = tuple(map(str.lower, uncompressed_exts))

    def add_bytes(self, archive_name: str, data: bytes, compress: Optional[bool] = None) -> APKBuilder:
        norm_name = archive_name.replace("\\", "/").lstrip("/")
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

        self._entries.append((norm_name, data, compression_type))
        return self

    def add_file(self, local_path: Union[str, Path], archive_name: Optional[str] = None) -> APKBuilder:
        path_obj = Path(local_path)
        arc_name = archive_name or path_obj.name
        with open(path_obj, "rb") as f:
            data = f.read()
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
        """Writes the aligned APK archive."""
        with zipfile.ZipFile(self._output_path, "w") as zf:
            for arc_name, data, comp_type in self._entries:
                info = zipfile.ZipInfo(arc_name)
                info.compress_type = comp_type
                info.external_attr = 0o644 << 16  # standard file permissions
                zf.writestr(info, data)


def pack(source_dir: Union[str, Path], output_apk: Union[str, Path]) -> None:
    """Convenience helper to pack a directory into an APK."""
    builder = APKBuilder(output_apk)
    builder.add_directory(source_dir)
    builder.build()
