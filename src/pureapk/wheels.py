"""Android wheel (.whl) inspection and unpacking toolkit.

Supports unpacking pre-compiled binary Python wheels for Android:
- Separates native ELF shared libraries (.so) into target lib/<abi>/ directories.
- Unpacks pure Python modules and packages into application project roots.
- Compatible with wheels from Termux, Kivy, Chaquopy, and custom Android NDK builds.
- 100% pure Python, zero external dependencies.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union
import zipfile


class AndroidWheelHelper:
    """Helper for inspecting and extracting Android wheels (.whl) into mobile project layouts."""

    __slots__ = ()

    SUPPORTED_ABIS: Tuple[str, ...] = (
        "arm64-v8a",
        "armeabi-v7a",
        "x86_64",
        "x86",
    )

    @classmethod
    def detect_abi_from_filename(cls, filename: str) -> Optional[str]:
        """Detects Android target ABI from wheel filename tags."""
        name_lower = filename.lower()
        if "arm64_v8a" in name_lower or "aarch64" in name_lower:
            return "arm64-v8a"
        if "armeabi_v7a" in name_lower or "armv7l" in name_lower or "armeabi" in name_lower:
            return "armeabi-v7a"
        if "x86_64" in name_lower or "amd64" in name_lower:
            return "x86_64"
        if "x86" in name_lower or "i686" in name_lower:
            return "x86"
        return None

    @classmethod
    def inspect_wheel(cls, wheel_path: Union[str, Path, bytes, BinaryIO]) -> Dict[str, Any]:
        """Inspects a wheel file and returns distribution metadata, detected ABI, and file statistics."""
        zf: zipfile.ZipFile
        wheel_name = "in_memory.whl"
        if isinstance(wheel_path, (str, Path)):
            path_obj = Path(wheel_path)
            wheel_name = path_obj.name
            zf = zipfile.ZipFile(path_obj, "r")
        elif isinstance(wheel_path, bytes):
            zf = zipfile.ZipFile(io.BytesIO(wheel_path), "r")
        else:
            zf = zipfile.ZipFile(wheel_path, "r")

        try:
            names = zf.namelist()
            so_files = [n for n in names if n.endswith(".so")]
            py_files = [n for n in names if n.endswith(".py") or n.endswith(".pyc")]
            dist_info_entries = [n for n in names if ".dist-info/" in n or ".dist-info\\" in n]

            dist_name = ""
            dist_version = ""
            for name in dist_info_entries:
                if name.endswith("METADATA"):
                    meta_lines = zf.read(name).decode("utf-8", errors="replace").splitlines()
                    for line in meta_lines:
                        if line.startswith("Name:"):
                            dist_name = line.split(":", 1)[1].strip()
                        elif line.startswith("Version:"):
                            dist_version = line.split(":", 1)[1].strip()

            abi = cls.detect_abi_from_filename(wheel_name)

            return {
                "wheel_name": wheel_name,
                "distribution_name": dist_name,
                "version": dist_version,
                "detected_abi": abi,
                "is_pure_python": abi is None and len(so_files) == 0,
                "native_libraries": so_files,
                "native_libraries_count": len(so_files),
                "python_files_count": len(py_files),
                "total_files": len(names),
            }
        finally:
            zf.close()

    @classmethod
    def unpack_wheel(
        cls,
        wheel_path: Union[str, Path, bytes, BinaryIO],
        target_dir: Union[str, Path],
        abi: Optional[str] = None,
        target_subpath: Optional[str] = None,
        strip_dist_info: bool = True,
    ) -> Dict[str, Any]:
        """Unpacks an Android wheel:
        - Native shared libraries (.so) -> target_dir/lib/<abi>/
        - Pure Python modules & assets -> target_dir / (target_subpath or "")
        """
        dest_root = Path(target_dir)
        dest_root.mkdir(parents=True, exist_ok=True)

        zf: zipfile.ZipFile
        wheel_name = "archive.whl"
        if isinstance(wheel_path, (str, Path)):
            p = Path(wheel_path)
            wheel_name = p.name
            zf = zipfile.ZipFile(p, "r")
        elif isinstance(wheel_path, bytes):
            zf = zipfile.ZipFile(io.BytesIO(wheel_path), "r")
        else:
            zf = zipfile.ZipFile(wheel_path, "r")

        try:
            target_abi = abi or cls.detect_abi_from_filename(wheel_name) or "arm64-v8a"
            lib_dest_dir = dest_root / "lib" / target_abi
            pure_dest_dir = dest_root / target_subpath if target_subpath else dest_root

            extracted_py: List[str] = []
            extracted_so: List[str] = []

            for member in zf.infolist():
                if member.is_dir():
                    continue

                norm_name = member.filename.replace("\\", "/").lstrip("/")

                # Filter out unwanted distribution records
                if strip_dist_info and ".dist-info/" in norm_name:
                    if norm_name.endswith("RECORD") or norm_name.endswith("INSTALLER"):
                        continue

                data = zf.read(member.filename)

                if norm_name.endswith(".so"):
                    # 1. Place .so into lib/<abi>/
                    lib_dest_dir.mkdir(parents=True, exist_ok=True)
                    so_filename = Path(norm_name).name
                    (lib_dest_dir / so_filename).write_bytes(data)
                    extracted_so.append(f"lib/{target_abi}/{so_filename}")

                    # 2. Also keep package-relative .so if it belongs to a Python package
                    if "/" in norm_name:
                        rel_dest = pure_dest_dir / norm_name
                        rel_dest.parent.mkdir(parents=True, exist_ok=True)
                        rel_dest.write_bytes(data)
                else:
                    # Pure Python code or resources
                    out_path = pure_dest_dir / norm_name
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(data)
                    extracted_py.append(norm_name)

            return {
                "wheel_name": wheel_name,
                "target_dir": str(dest_root),
                "target_abi": target_abi,
                "extracted_so_files": extracted_so,
                "extracted_py_files_count": len(extracted_py),
                "total_extracted": len(extracted_so) + len(extracted_py),
            }
        finally:
            zf.close()
