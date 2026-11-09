"""Android wheel (.whl) inspection and unpacking toolkit.

Supports unpacking pre-compiled binary Python wheels for Android:
- Separates native ELF shared libraries (.so) into target lib/<abi>/ directories.
- Unpacks pure Python modules and packages into application project roots.
- Compatible with wheels from Termux, Kivy, Chaquopy, and custom Android NDK builds.
- 100% pure Python, zero external dependencies.
"""

from __future__ import annotations

import base64
import hashlib
import io
import os
from pathlib import Path
import re
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

    ABI_TO_PLATFORM_TAG: Dict[str, str] = {
        "arm64-v8a": "android_24_arm64_v8a",
        "armeabi-v7a": "android_24_armeabi_v7a",
        "x86_64": "android_24_x86_64",
        "x86": "android_24_x86",
    }

    PLATFORM_TAG_TO_ABI: Dict[str, str] = {
        "android_24_arm64_v8a": "arm64-v8a",
        "android_arm64_v8a": "arm64-v8a",
        "android_aarch64": "arm64-v8a",
        "linux_aarch64": "arm64-v8a",
        "android_24_armeabi_v7a": "armeabi-v7a",
        "android_armeabi_v7a": "armeabi-v7a",
        "android_armv7l": "armeabi-v7a",
        "linux_armv7l": "armeabi-v7a",
        "android_24_x86_64": "x86_64",
        "android_x86_64": "x86_64",
        "linux_x86_64": "x86_64",
        "android_24_x86": "x86",
        "android_x86": "x86",
        "android_i686": "x86",
        "linux_i686": "x86",
    }

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

    @classmethod
    def build_wheel(
        cls,
        source_dir: Union[str, Path],
        output_whl: Optional[Union[str, Path]] = None,
        distribution_name: str = "app",
        version: str = "0.1.0",
        python_tag: str = "py3",
        abi_tag: Optional[str] = None,
        platform_tag: Optional[str] = None,
        abi: Optional[str] = None,
        summary: str = "Mobile Python package",
    ) -> Dict[str, Any]:
        """Builds a PEP 427 standard wheel (.whl) from a source directory.

        Supports:
        - Pure Python: py3-none-any.whl, py2.py3-none-any.whl
        - Specific CPython versions: cp38, cp39, cp310, cp311, cp312, cp313, cp314
        - Target mobile architectures: arm64-v8a, armeabi-v7a, x86_64, x86
        """
        src = Path(source_dir)
        if not src.is_dir():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        # Normalize distribution name and version for PEP 427 filename
        dist_slug = re.sub(r"[-_.]+", "_", distribution_name).strip("_")
        ver_slug = re.sub(r"[-_]+", "_", version).strip("_")

        # Determine platform and ABI tags
        final_platform = platform_tag
        if final_platform is None:
            if abi:
                final_platform = cls.ABI_TO_PLATFORM_TAG.get(abi, f"android_24_{abi.replace('-', '_')}")
            else:
                final_platform = "any"

        final_abi_tag = abi_tag
        if final_abi_tag is None:
            if final_platform == "any":
                final_abi_tag = "none"
            elif python_tag.startswith("cp"):
                final_abi_tag = python_tag
            else:
                final_abi_tag = "none"

        is_pure = (final_platform == "any" and final_abi_tag == "none")
        wheel_filename = f"{dist_slug}-{ver_slug}-{python_tag}-{final_abi_tag}-{final_platform}.whl"

        if output_whl is None:
            out_file = src.parent / wheel_filename
        else:
            out_p = Path(output_whl)
            if out_p.is_dir() or not str(output_whl).lower().endswith(".whl") or str(output_whl).endswith(("/", "\\")):
                out_p.mkdir(parents=True, exist_ok=True)
                out_file = out_p / wheel_filename
            else:
                out_p.parent.mkdir(parents=True, exist_ok=True)
                out_file = out_p

        dist_info_dir = f"{dist_slug}-{ver_slug}.dist-info"
        record_lines: List[str] = []
        excluded = {".git", ".venv", "__pycache__", ".pytest_cache", ".idea", ".vscode", "build", "dist"}

        with zipfile.ZipFile(out_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            total_files = 0
            # 1. Package source files
            for root, dirs, files in os.walk(src):
                dirs[:] = [d for d in dirs if d not in excluded and not d.endswith((".dist-info", ".egg-info"))]
                for file in files:
                    if file.endswith((".whl", ".apk", ".aab", ".pyc")):
                        continue
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(src).as_posix()
                    if any(part in excluded for part in Path(rel_p).parts):
                        continue
                    data = full_p.read_bytes()
                    zf.writestr(rel_p, data)
                    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode("ascii").rstrip("=")
                    record_lines.append(f"{rel_p},sha256={digest},{len(data)}")
                    total_files += 1

            # 2. METADATA
            metadata_content = (
                f"Metadata-Version: 2.1\n"
                f"Name: {distribution_name}\n"
                f"Version: {version}\n"
                f"Summary: {summary}\n"
            ).encode("utf-8")
            meta_arc = f"{dist_info_dir}/METADATA"
            zf.writestr(meta_arc, metadata_content)
            m_digest = base64.urlsafe_b64encode(hashlib.sha256(metadata_content).digest()).decode("ascii").rstrip("=")
            record_lines.append(f"{meta_arc},sha256={m_digest},{len(metadata_content)}")

            # 3. WHEEL
            wheel_content = (
                f"Wheel-Version: 1.0\n"
                f"Generator: pureapk\n"
                f"Root-Is-Purelib: {'true' if is_pure else 'false'}\n"
                f"Tag: {python_tag}-{final_abi_tag}-{final_platform}\n"
            ).encode("utf-8")
            wheel_arc = f"{dist_info_dir}/WHEEL"
            zf.writestr(wheel_arc, wheel_content)
            w_digest = base64.urlsafe_b64encode(hashlib.sha256(wheel_content).digest()).decode("ascii").rstrip("=")
            record_lines.append(f"{wheel_arc},sha256={w_digest},{len(wheel_content)}")

            # 4. RECORD
            record_arc = f"{dist_info_dir}/RECORD"
            record_lines.append(f"{record_arc},,")
            record_content = "\n".join(record_lines).encode("utf-8") + b"\n"
            zf.writestr(record_arc, record_content)

        return {
            "wheel_path": str(out_file),
            "wheel_name": out_file.name,
            "distribution_name": distribution_name,
            "version": version,
            "python_tag": python_tag,
            "abi_tag": final_abi_tag,
            "platform_tag": final_platform,
            "total_files": total_files + 3,
            "size_bytes": out_file.stat().st_size,
        }

    @classmethod
    def repack_wheel(
        cls,
        wheel_path: Union[str, Path],
        output_whl: Union[str, Path],
        target_python_tag: str = "py3",
        target_abi: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Repacks an existing wheel to retarget a specific Python version or ABI."""
        info = cls.inspect_wheel(wheel_path)
        dist_name = info["distribution_name"] or "package"
        ver = info["version"] or "1.0.0"

        import tempfile
        with tempfile.TemporaryDirectory() as tmp_d:
            tmp_root = Path(tmp_d)
            cls.unpack_wheel(wheel_path, tmp_root, strip_dist_info=True)
            return cls.build_wheel(
                tmp_root,
                output_whl=output_whl,
                distribution_name=dist_name,
                version=ver,
                python_tag=target_python_tag,
                abi=target_abi or info["detected_abi"],
            )

    @classmethod
    def build_framework_wheel(
        cls,
        framework: str,
        output_whl: Optional[Union[str, Path]] = None,
        distribution_name: Optional[str] = None,
        version: str = "0.1.0",
        python_tag: str = "py3",
        abi: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Builds a portable wheel package for any supported framework (kivy, pygame, flet, toga, renpy, webview, pyside).

        Decouples the framework template and runtime structure from any author-specific path,
        making ready-to-use wheels accessible universally across environments and Python versions.
        """
        import tempfile
        from pureapk.frameworks import (
            KivyAppHelper,
            PygameAppHelper,
            FletAppHelper,
            TogaAppHelper,
            RenPyAppHelper,
            WebViewAppHelper,
            PySideAppHelper,
        )
        helpers: Dict[str, Tuple[Any, str]] = {
            "kivy": (KivyAppHelper, "kivy-app"),
            "pygame": (PygameAppHelper, "pygame-app"),
            "flet": (FletAppHelper, "flet-app"),
            "toga": (TogaAppHelper, "toga-app"),
            "renpy": (RenPyAppHelper, "renpy-app"),
            "webview": (WebViewAppHelper, "webview-app"),
            "pyside": (PySideAppHelper, "pyside-app"),
            "pyqt": (PySideAppHelper, "pyqt-app"),
        }
        fw_key = framework.lower().strip()
        if fw_key not in helpers:
            supported = ", ".join(helpers.keys())
            raise ValueError(f"Unknown framework '{framework}'. Supported: {supported}")

        helper_cls, default_name = helpers[fw_key]
        dist_name = distribution_name or default_name
        app_title = title or dist_name.replace("-", " ").title()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            helper_cls.init_project(tmp_root, title=app_title)
            return cls.build_wheel(
                tmp_root,
                output_whl=output_whl,
                distribution_name=dist_name,
                version=version,
                python_tag=python_tag,
                abi=abi,
                summary=f"Pre-packaged {framework.title()} mobile application package",
            )
