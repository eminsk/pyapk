"""Core APK class with zero-copy stream processing and lazy attribute evaluation.

Designed for minimal memory overhead and maximum throughput across all Python runtimes.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
import threading
from typing import (
    Any,
    BinaryIO,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)
import zipfile

from pureapk.dex import DexHeader, MultiDexSummary
from pureapk.manifest import AndroidManifest
from pureapk.signature import APKSignature

KNOWN_ARCHITECTURES: Tuple[str, ...] = (
    "arm64-v8a",
    "armeabi-v7a",
    "armeabi",
    "x86_64",
    "x86",
    "mips64",
    "mips",
    "riscv64",
)


class APKFileInfo:
    """Lightweight metadata descriptor for an archive file entry."""

    __slots__ = ("filename", "file_size", "compress_size", "crc32", "is_dir")

    def __init__(
        self,
        filename: str,
        file_size: int,
        compress_size: int,
        crc32: int,
        is_dir: bool,
    ) -> None:
        self.filename = filename
        self.file_size = file_size
        self.compress_size = compress_size
        self.crc32 = crc32
        self.is_dir = is_dir

    def as_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "file_size": self.file_size,
            "compress_size": self.compress_size,
            "crc32": f"0x{self.crc32:08x}",
            "is_dir": self.is_dir,
        }


class APK:
    """Primary APK representation with lazy evaluation and thread-safety."""

    __slots__ = (
        "_source",
        "_raw_bytes",
        "_zip",
        "_manifest",
        "_dex_summary",
        "_signature",
        "_files_cache",
        "_lock",
    )

    def __init__(self, source: Union[str, Path, bytes, BinaryIO]) -> None:
        self._source = source
        self._raw_bytes: Optional[bytes] = None
        self._zip: Optional[zipfile.ZipFile] = None
        self._manifest: Optional[AndroidManifest] = None
        self._dex_summary: Optional[MultiDexSummary] = None
        self._signature: Optional[APKSignature] = None
        self._files_cache: Optional[Tuple[APKFileInfo, ...]] = None
        self._lock = threading.Lock()
        self._init_zip()

    def _init_zip(self) -> None:
        source = self._source
        is_bytes = isinstance(source, bytes)
        is_path = isinstance(source, (str, Path))

        def load_bytes() -> None:
            self._raw_bytes = source  # type: ignore[assignment]
            self._zip = zipfile.ZipFile(io.BytesIO(source))  # type: ignore[arg-type]

        def load_path() -> None:
            path_str = str(source)
            with open(path_str, "rb") as f:
                self._raw_bytes = f.read()
            self._zip = zipfile.ZipFile(io.BytesIO(self._raw_bytes))

        def load_stream() -> None:
            self._zip = zipfile.ZipFile(source)  # type: ignore[arg-type]

        dispatch = {
            True: load_bytes,
            False: lambda: {True: load_path, False: load_stream}[is_path](),
        }
        dispatch[is_bytes]()

    @property
    def zip_file(self) -> zipfile.ZipFile:
        return self._zip  # type: ignore[return-value]

    @property
    def manifest(self) -> AndroidManifest:
        with self._lock:
            cached = self._manifest
            action = {
                True: lambda: cached,
                False: self._load_manifest,
            }[cached is not None]
            return action()

    def _load_manifest(self) -> AndroidManifest:
        zf = self.zip_file
        has_manifest = "AndroidManifest.xml" in zf.namelist()
        raw = {
            True: lambda: zf.read("AndroidManifest.xml"),
            False: lambda: b"",
        }[has_manifest]()
        manifest = AndroidManifest(raw)
        self._manifest = manifest
        return manifest

    @property
    def package_name(self) -> str:
        return self.manifest.package_name

    @property
    def version_code(self) -> Optional[int]:
        return self.manifest.version_code

    @property
    def version_name(self) -> str:
        return self.manifest.version_name

    @property
    def min_sdk_version(self) -> Optional[int]:
        return self.manifest.min_sdk_version

    @property
    def target_sdk_version(self) -> Optional[int]:
        return self.manifest.target_sdk_version

    @property
    def permissions(self) -> Tuple[str, ...]:
        return self.manifest.permissions

    @property
    def activities(self) -> Tuple[str, ...]:
        return self.manifest.activities

    @property
    def services(self) -> Tuple[str, ...]:
        return self.manifest.services

    @property
    def receivers(self) -> Tuple[str, ...]:
        return self.manifest.receivers

    @property
    def providers(self) -> Tuple[str, ...]:
        return self.manifest.providers

    @property
    def application_label(self) -> str:
        return self.manifest.application_label

    @property
    def application_icon(self) -> str:
        return self.manifest.application_icon

    @property
    def dex(self) -> MultiDexSummary:
        with self._lock:
            cached = self._dex_summary
            action = {
                True: lambda: cached,
                False: self._load_dex,
            }[cached is not None]
            return action()

    def _load_dex(self) -> MultiDexSummary:
        zf = self.zip_file
        dex_names = tuple(
            sorted(
                filter(
                    lambda name: name.startswith("classes") and name.endswith(".dex"),
                    zf.namelist(),
                )
            )
        )
        headers = tuple(map(lambda name: DexHeader.from_bytes(zf.read(name)), dex_names))
        summary = MultiDexSummary(headers)
        self._dex_summary = summary
        return summary

    @property
    def signature(self) -> APKSignature:
        with self._lock:
            cached = self._signature
            action = {
                True: lambda: cached,
                False: self._load_signature,
            }[cached is not None]
            return action()

    def _load_signature(self) -> APKSignature:
        sig = APKSignature.inspect(self.zip_file, self._raw_bytes)
        self._signature = sig
        return sig

    @property
    def native_architectures(self) -> Tuple[str, ...]:
        zf = self.zip_file
        names = zf.namelist()
        archs: Set[str] = set()

        def extract_arch(name: str) -> None:
            parts = name.split("/")
            has_lib = len(parts) >= 3 and parts[0] == "lib"
            action = {
                True: lambda: archs.add(parts[1]),
                False: lambda: None,
            }[has_lib]
            action()

        tuple(map(extract_arch, names))
        return tuple(sorted(archs))

    @property
    def files(self) -> Tuple[APKFileInfo, ...]:
        with self._lock:
            cached = self._files_cache
            action = {
                True: lambda: cached,
                False: self._load_files,
            }[cached is not None]
            return action()

    def _load_files(self) -> Tuple[APKFileInfo, ...]:
        zf = self.zip_file
        file_infos = tuple(
            map(
                lambda zinfo: APKFileInfo(
                    filename=zinfo.filename,
                    file_size=zinfo.file_size,
                    compress_size=zinfo.compress_size,
                    crc32=zinfo.CRC,
                    is_dir=zinfo.is_dir(),
                ),
                zf.infolist(),
            )
        )
        self._files_cache = file_infos
        return file_infos

    @property
    def filenames(self) -> Tuple[str, ...]:
        return tuple(map(lambda f: f.filename, self.files))

    def read(self, filename: str) -> bytes:
        return self.zip_file.read(filename)

    def extract(
        self,
        output_dir: Union[str, Path],
        members: Optional[Iterable[str]] = None,
    ) -> None:
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        self.zip_file.extractall(target, members=members)

    def verify(self) -> Dict[str, Any]:
        """Validates internal CRC checksums and returns integrity status."""
        bad_file = self.zip_file.testzip()
        is_corrupt = bad_file is not None
        return {
            "is_valid": not is_corrupt,
            "corrupted_file": bad_file,
            "is_signed": self.signature.is_signed,
            "signature_schemes": list(self.signature.scheme_names),
        }

    def info(self) -> Dict[str, Any]:
        """Serializes full APK metadata to a dictionary."""
        return {
            "package_name": self.package_name,
            "version_code": self.version_code,
            "version_name": self.version_name,
            "min_sdk_version": self.min_sdk_version,
            "target_sdk_version": self.target_sdk_version,
            "application_label": self.application_label,
            "application_icon": self.application_icon,
            "permissions": list(self.permissions),
            "activities": list(self.activities),
            "services": list(self.services),
            "receivers": list(self.receivers),
            "providers": list(self.providers),
            "native_architectures": list(self.native_architectures),
            "dex": self.dex.as_dict(),
            "signature": self.signature.as_dict(),
            "total_files": len(self.files),
        }

    def close(self) -> None:
        closer = {
            True: lambda: self._zip.close(),  # type: ignore[union-attr]
            False: lambda: None,
        }[self._zip is not None]
        closer()

    def __enter__(self) -> APK:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"APK(package={self.package_name!r}, version={self.version_name!r})"
