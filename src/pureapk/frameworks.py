"""First-class support and templates for Kivy, Pygame, and Python-for-Android frameworks.



Provides framework detection, manifest generators, and project scaffolding.

"""



from __future__ import annotations



import os

from pathlib import Path

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union



FRAMEWORK_SIGNATURES: Dict[str, Tuple[str, ...]] = {

    "kivy": (

        "libkivy.so",

        "org.kivy.android.PythonActivity",

        "org/kivy/android",

        ".kv",

    ),

    "pygame": (

        "libpygame.so",

        "org.renpy.android.PythonSDLActivity",

        "org.renpy.android",

        "pygame",

    ),

    "flet": (

        "libflet.so",

        "io.flet",

        "flet",

    ),

    "beeware": (

        "org.beeware",

        "toga",

        "rubicon",

    ),

    "renpy": (

        "librenpy.so",

        ".rpy",

        ".rpyc",

        "renpy",

    ),

    "webview": (

        "android.webkit.WebView",

        "assets/index.html",

    ),

    "pyside": (

        "org.qtproject.qt.android.bindings.QtActivity",

        "libplugins_platforms_qtforandroid.so",

        "libQt6Core.so",

        "libQt5Core.so",

        "pyside6",

        "pyqt6",

    ),

    "flutter": ("libflutter.so", "io.flutter.app.FlutterActivity"),

    "react-native": ("libreactnativejni.so", "com.facebook.react"),

    "unity": ("libunity.so", "com.unity3d.player"),

    "godot": ("libgodot_android.so", "org.godotengine.godot"),

}





class FrameworkDetector:

    """Detects mobile game/app frameworks inside APK archives."""



    __slots__ = ()



    @staticmethod

    def detect(filenames: Sequence[str], activities: Sequence[str]) -> str:

        files_lower = tuple(map(str.lower, filenames))

        acts_lower = tuple(map(str.lower, activities))



        def has_marker(marker: str) -> bool:

            m = marker.lower()

            return any(m in f for f in files_lower) or any(m in a for a in acts_lower)



        for fw, markers in FRAMEWORK_SIGNATURES.items():

            if any(map(has_marker, markers)):

                return fw



        # Check generic python

        if any("libpython" in f for f in files_lower):

            return "python"



        return "native"





def patch_arsc_private_version(arsc: bytes, new_version: str) -> bytes:

    """Replace the 40-char SHA1 ``private_version`` value inside a p4a resources.arsc.

    p4a stores ``private_version`` as a 40-hex-digit string in the UTF-8 global
    string pool (encoded as ``0x28 0x28 <40 bytes> 0x00``). The replacement has the
    same length, so the pool layout and all offsets stay intact. Returns the input
    unchanged when no unique candidate is found.

    """

    import re

    if len(new_version) != 40 or not re.fullmatch(r"[0-9a-f]{40}", new_version):

        raise ValueError("new_version must be a 40-char lowercase hex string")

    matches = list(re.finditer(rb"\x28\x28([0-9a-f]{40})\x00", arsc))

    if len(matches) != 1:

        return arsc

    start, end = matches[0].span(1)

    return arsc[:start] + new_version.encode("ascii") + arsc[end:]



def _detect_runtime_python_version(
    src: Path,
    runtime_apk: Optional[Union[str, Path]] = None,
) -> Optional[str]:
    """Detect targeted Python runtime version (e.g. '3.8', '3.9', '3.10', '3.11', '3.12') from native libraries."""
    import re
    import zipfile

    for abi in ("arm64-v8a", "armeabi-v7a", "x86_64", "x86"):
        abi_dir = src / "lib" / abi
        if abi_dir.is_dir():
            for f in abi_dir.iterdir():
                m = re.match(r"libpython(3\.\d+)\.so", f.name)
                if m:
                    return m.group(1)

    if runtime_apk:
        rt_path = Path(runtime_apk)
        if rt_path.is_dir():
            return _detect_runtime_python_version(rt_path, None)
        if rt_path.is_file():
            try:
                with zipfile.ZipFile(rt_path, "r") as zf:
                    for name in zf.namelist():
                        m = re.search(r"lib/[^/]+/libpython(3\.\d+)\.so$", name)
                        if m:
                            return m.group(1)
            except Exception:
                pass
    return None


def _find_python(target_version: str = "3.10") -> Optional[str]:
    """Locate Python executable on host for a specific target version to compile compatible bytecode."""
    import shutil
    uv_bin = shutil.which("uv")
    if uv_bin:
        try:
            import subprocess
            res = subprocess.run([uv_bin, "python", "find", target_version], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip() and not line.strip().startswith("warning:")]
                if lines and os.path.exists(lines[-1]):
                    return lines[-1]
            # Try auto-installing target python version via uv if missing
            res_inst = subprocess.run([uv_bin, "python", "install", target_version], capture_output=True, text=True, timeout=60)
            if res_inst.returncode == 0:
                res = subprocess.run([uv_bin, "python", "find", target_version], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip() and not line.strip().startswith("warning:")]
                    if lines and os.path.exists(lines[-1]):
                        return lines[-1]
        except Exception:
            pass
    p = shutil.which(f"python{target_version}")
    if p:
        return p
    # Check Windows uv directory
    win_uv = Path.home() / "AppData" / "Roaming" / "uv" / "python"
    if win_uv.is_dir():
        for cand in win_uv.glob(f"*cpython-{target_version}*"):
            exe = cand / "python.exe"
            if exe.exists():
                return str(exe)
    # Check Posix uv directory
    posix_uv = Path.home() / ".local" / "share" / "uv" / "python"
    if posix_uv.is_dir():
        for cand in posix_uv.glob(f"*cpython-{target_version}*"):
            exe = cand / "bin" / "python3"
            if exe.exists():
                return str(exe)
    return None


def _compile_py_bytecode(full_path: Path, filename: str, target_version: Optional[str] = None) -> Optional[bytes]:
    """Compile Python source to timestamp-based .pyc bytecode compatible with target runtime version."""
    import sys
    source_bytes = full_path.read_bytes()
    host_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    if target_version is not None and target_version != host_ver:
        py_bin = _find_python(target_version)
        if py_bin:
            try:
                import subprocess
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".pyc", delete=False) as tmp:
                    tmp_path = tmp.name
                res = subprocess.run(
                    [
                        py_bin,
                        "-c",
                        "import py_compile, sys; py_compile.compile(sys.argv[1], cfile=sys.argv[2], doraise=True)",
                        str(full_path),
                        tmp_path,
                    ],
                    capture_output=True,
                    timeout=10,
                )
                if res.returncode == 0 and os.path.exists(tmp_path):
                    with open(tmp_path, "rb") as f:
                        data = f.read()
                    os.unlink(tmp_path)
                    return data
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass
        # CRITICAL: If target version differs from host but matching compiler was not found or failed,
        # DO NOT fallback to host compilation. Host compilation produces bytecode with the wrong magic number,
        # crashing Android runtime with "Bad magic number in .pyc file".
        # Returning None ensures the raw .py file is used instead, which Python compiles on device cleanly.
        return None

    try:
        import importlib._bootstrap_external
        code_obj = compile(source_bytes, filename, "exec")
        return importlib._bootstrap_external._code_to_timestamp_pyc(code_obj)
    except Exception:
        return None


def _generate_sitecustomize_script(user_script: Optional[bytes] = None) -> bytes:
    """Generates an enhanced sitecustomize.py with PyJNIus Cython 3 compatibility and Kivy runtime safety."""
    bootstrap = b'''# -*- coding: utf-8 -*-
"""pureapk runtime bootstrap: sys.path, PyJNIus Cython 3 compatibility, and Kivy crash prevention."""
import os
import sys

# 1. Add _applibs directory to sys.path if present
_applibs = os.path.join(os.path.dirname(__file__), "_applibs")
if os.path.isdir(_applibs) and _applibs not in sys.path:
    sys.path.append(_applibs)


# 2. PyJNIus Cython 3 compatibility patch (_JavaClass__cls_storage)
def _pureapk_patch_pyjnius():
    try:
        import jnius
        import jnius.jnius as _jj

        orig_resolve = _jj.MetaJavaClass.resolve_class
        @classmethod
        def _patched_resolve(meta, classDict):
            orig_resolve(classDict)
            if "__cls_storage" in classDict:
                classDict["_JavaClass__cls_storage"] = classDict["__cls_storage"]
        _jj.MetaJavaClass.resolve_class = _patched_resolve

        orig_new = _jj.MetaJavaClass.__new__
        def _patched_new(meta, classname, bases, classDict, classparams=(True, True)):
            if "__cls_storage" in classDict:
                classDict["_JavaClass__cls_storage"] = classDict["__cls_storage"]
            tp = orig_new(meta, classname, bases, classDict, classparams)
            if hasattr(tp, "__cls_storage"):
                try:
                    setattr(tp, "_JavaClass__cls_storage", getattr(tp, "__cls_storage"))
                except Exception:
                    pass
            return tp
        _jj.MetaJavaClass.__new__ = _patched_new

        try:
            import jnius.reflect as _jr
            for mod in (_jr, jnius, _jj):
                for k, obj in list(vars(mod).items()):
                    if hasattr(obj, "__cls_storage"):
                        try:
                            setattr(obj, "_JavaClass__cls_storage", getattr(obj, "__cls_storage"))
                        except Exception:
                            pass
        except Exception:
            pass
    except Exception:
        pass


_pureapk_patch_pyjnius()


# 3. Kivy EventLoop splash screen & metrics safety hooks
def _pureapk_hook_kivy():
    try:
        import builtins
        _orig_import = builtins.__import__

        def _hooked_import(name, *args, **kwargs):
            mod = _orig_import(name, *args, **kwargs)
            if name == "kivy.base" or name.startswith("kivy.base."):
                try:
                    from kivy.base import EventLoopBase
                    if not getattr(EventLoopBase, "_pureapk_splash_patched", False):
                        orig_splash = getattr(EventLoopBase, "remove_android_splash", None)
                        def _safe_remove_splash(self=None):
                            try:
                                if orig_splash:
                                    orig_splash(self)
                                else:
                                    import android
                                    if hasattr(android, "remove_presplash"):
                                        android.remove_presplash()
                            except Exception:
                                pass
                        EventLoopBase.remove_android_splash = _safe_remove_splash
                        EventLoopBase._pureapk_splash_patched = True
                except Exception:
                    pass
            elif name == "kivy.metrics" or name.startswith("kivy.metrics."):
                try:
                    import kivy.metrics
                    if not getattr(kivy.metrics, "_pureapk_metrics_patched", False):
                        orig_dpi = kivy.metrics.MetricsBase.get_dpi
                        def _safe_get_dpi(self, force_recompute=False):
                            try:
                                if self._dpi is not None:
                                    return self._dpi
                                return orig_dpi(self, force_recompute=force_recompute)
                            except Exception:
                                return 320.0
                        kivy.metrics.MetricsBase.get_dpi = _safe_get_dpi
                        orig_fs = getattr(kivy.metrics.MetricsBase, "get_fontscale", None)
                        def _safe_get_fs(self, force_recompute=False):
                            try:
                                if orig_fs:
                                    return orig_fs(self, force_recompute=force_recompute)
                            except Exception:
                                pass
                            return 1.0
                        kivy.metrics.MetricsBase.get_fontscale = _safe_get_fs
                        kivy.metrics._pureapk_metrics_patched = True
                except Exception:
                    pass
            return mod

        builtins.__import__ = _hooked_import
    except Exception:
        pass


_pureapk_hook_kivy()
'''
    if user_script:
        return bootstrap + b"\n\n# --- User custom sitecustomize.py ---\n" + user_script
    return bootstrap


def _pack_framework_project(
    builder: APKBuilder,
    src: Path,
    is_webview: bool = False,
    channel: Optional[str] = None,
    package_name: Optional[str] = None,
    app_title: Optional[str] = None,
    runtime_apk: Optional[Union[str, Path]] = None,
) -> None:
    """Packages framework project folders: lib/, res/, assets/, root DEX/resources, and private python tarballs."""
    import io
    import tarfile
    import zipfile

    # Optional runtime template APK / directory
    rt_zf: Optional[zipfile.ZipFile] = None
    rt_dir: Optional[Path] = None
    rt_sitecustomize: Optional[bytes] = None
    if runtime_apk:
        rt_p = Path(runtime_apk)
        if not rt_p.exists():
            raise FileNotFoundError(f"Runtime APK or directory not found: {runtime_apk}")
        if rt_p.is_dir():
            rt_dir = rt_p
            if (rt_p / "sitecustomize.pyc").exists():
                rt_sitecustomize = (rt_p / "sitecustomize.pyc").read_bytes()
        else:
            rt_zf = zipfile.ZipFile(rt_p, "r")
            if "assets/private.tar" in rt_zf.namelist():
                try:
                    with tarfile.open(fileobj=io.BytesIO(rt_zf.read("assets/private.tar"))) as btf:
                        for member in btf.getmembers():
                            if member.name.lstrip("./") == "sitecustomize.pyc":
                                extr = btf.extractfile(member)
                                if extr:
                                    rt_sitecustomize = extr.read()
                                break
                except Exception:
                    pass

    try:
        # 1. Native shared libraries (lib/ -> lib/)
        lib_dir = src / "lib"
        has_native_so = False
        added_lib_entries = set()
        if lib_dir.is_dir():
            builder.add_directory(lib_dir, prefix="lib", compress=True)
            for root_l, _, files_l in os.walk(lib_dir):
                for f in files_l:
                    rel_l = (Path(root_l) / f).relative_to(lib_dir).as_posix()
                    added_lib_entries.add(f"lib/{rel_l}")
                    if f.endswith(".so"):
                        has_native_so = True

        if rt_dir and (rt_dir / "lib").is_dir():
            for root_l, _, files_l in os.walk(rt_dir / "lib"):
                for f in files_l:
                    full_l = Path(root_l) / f
                    arc_l = f"lib/{full_l.relative_to(rt_dir / 'lib').as_posix()}"
                    if arc_l not in added_lib_entries:
                        builder.add_file(full_l, arc_l, compress=True)
                        added_lib_entries.add(arc_l)
                        if f.endswith(".so"):
                            has_native_so = True
        elif rt_zf:
            for name in rt_zf.namelist():
                if name.startswith("lib/") and not name.endswith("/") and name not in added_lib_entries:
                    builder.add_bytes(name, rt_zf.read(name), compress=True)
                    added_lib_entries.add(name)
                    if name.endswith(".so"):
                        has_native_so = True

        if not has_native_so and not is_webview:
            import sys
            print(
                "WARNING: Packaging skeleton APK without native Python runtime (0 .so files in lib/).\n"
                "  This APK contains your Python code in assets/private.tar, but requires a native Python runtime to execute on device.\n"
                "  To bundle a working runtime, pass '--runtime-apk <base.apk>', run 'pureapk prepare-runtime', or use 'pureapk unpack-wheel'.",
                file=sys.stderr,
            )

        # 2. Android resources (res/ -> res/)
        res_dir = src / "res"
        added_res_entries = set()
        custom_icon_bytes = (src / "icon.png").read_bytes() if (src / "icon.png").is_file() else None
        if res_dir.is_dir():
            for root_r, _, files_r in os.walk(res_dir):
                for f in files_r:
                    full_r = Path(root_r) / f
                    arc_r = f"res/{full_r.relative_to(res_dir).as_posix()}"
                    builder.add_file(full_r, arc_r)
                    added_res_entries.add(arc_r)

        if rt_dir and (rt_dir / "res").is_dir():
            for root_r, _, files_r in os.walk(rt_dir / "res"):
                for f in files_r:
                    full_r = Path(root_r) / f
                    arc_r = f"res/{full_r.relative_to(rt_dir / 'res').as_posix()}"
                    if arc_r not in added_res_entries:
                        if custom_icon_bytes and f in ("icon.png", "ic_launcher.png"):
                            builder.add_bytes(arc_r, custom_icon_bytes)
                        else:
                            builder.add_file(full_r, arc_r)
                        added_res_entries.add(arc_r)
        elif rt_zf:
            for name in rt_zf.namelist():
                if name.startswith("res/") and not name.endswith("/") and name not in added_res_entries:
                    base_fn = name.rsplit("/", 1)[-1]
                    if custom_icon_bytes and base_fn in ("icon.png", "ic_launcher.png"):
                        builder.add_bytes(name, custom_icon_bytes)
                    else:
                        builder.add_bytes(name, rt_zf.read(name))
                    added_res_entries.add(name)

        # 3. Root DEX files and compiled resources table (classes*.dex, resources.arsc)
        arsc_bytes: Optional[bytes] = None
        private_tar_bytes: Optional[bytes] = None
        added_dex_entries = set()
        for entry in src.iterdir():
            if entry.is_file():
                if entry.name == "resources.arsc":
                    arsc_bytes = entry.read_bytes()
                elif entry.name.endswith(".dex"):
                    builder.add_file(entry, entry.name)
                    added_dex_entries.add(entry.name)

        if rt_dir:
            if arsc_bytes is None and (rt_dir / "resources.arsc").is_file():
                arsc_bytes = (rt_dir / "resources.arsc").read_bytes()
            for entry in sorted(rt_dir.glob("classes*.dex")):
                if entry.name not in added_dex_entries:
                    builder.add_file(entry, entry.name)
                    added_dex_entries.add(entry.name)
        elif rt_zf:
            if arsc_bytes is None and "resources.arsc" in rt_zf.namelist():
                arsc_bytes = rt_zf.read("resources.arsc")
            for name in sorted(rt_zf.namelist()):
                if "/" not in name and name.startswith("classes") and name.endswith(".dex") and name not in added_dex_entries:
                    builder.add_bytes(name, rt_zf.read(name))
                    added_dex_entries.add(name)

        # 4. Custom assets (assets/ -> assets/)
        assets_dir = src / "assets"
        has_custom_private_tar = False
        if assets_dir.is_dir():
            for asset_root, _, asset_files in os.walk(assets_dir):
                for af in asset_files:
                    af_full = Path(asset_root) / af
                    af_rel = af_full.relative_to(assets_dir)
                    arc_name = f"assets/{af_rel}".replace("\\", "/")
                    if arc_name == "assets/private.tar":
                        has_custom_private_tar = True
                        data = af_full.read_bytes()
                        if not data.startswith(b"\x1f\x8b"):
                            import gzip
                            data = gzip.compress(data)
                        builder.add_bytes(arc_name, data, compress=False)
                        private_tar_bytes = data
                    else:
                        builder.add_file(af_full, arc_name)

        if is_webview:
            index_html = src / "index.html"
            if index_html.exists() and not (assets_dir / "index.html").exists():
                builder.add_file(index_html, "assets/index.html")

        # 5. Bundle Python codebase into assets/private.tar (p4a standard requires gzip-compressed tar)
        if not has_custom_private_tar:
            tar_buf = io.BytesIO()
            has_files = False
            target_py_ver = _detect_runtime_python_version(src, runtime_apk=runtime_apk)
            excluded_top = (
                "lib",
                "res",
                "assets",
                "META-INF",
                ".git",
                ".venv",
                "__pycache__",
                ".pytest_cache",
                ".idea",
                ".vscode",
                "dist",
                "build",
                "tests",
                "asm",
            )
            excluded_exts = (".apk", ".aab", ".ipa", ".msix", ".dex", ".exe", ".dll", ".pyd", ".ico", ".keystore", ".jks", ".p12", ".whl")
            with tarfile.open(fileobj=tar_buf, mode="w:gz", format=tarfile.USTAR_FORMAT) as tf:
                if has_native_so and not is_webview:
                    import tempfile
                    user_sc_py = src / "sitecustomize.py"
                    user_sc_bytes = user_sc_py.read_bytes() if user_sc_py.is_file() else None
                    sc_code = _generate_sitecustomize_script(user_sc_bytes)

                    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as sc_tmp:
                        sc_tmp.write(sc_code)
                        sc_tmp_path = Path(sc_tmp.name)
                    sc_pyc = None
                    try:
                        sc_pyc = _compile_py_bytecode(sc_tmp_path, "sitecustomize.py", target_version=target_py_ver)
                    finally:
                        if sc_tmp_path.exists():
                            sc_tmp_path.unlink()

                    # Add sitecustomize.py source to tar
                    sc_src_ti = tarfile.TarInfo(name="sitecustomize.py")
                    sc_src_ti.type = tarfile.REGTYPE
                    sc_src_ti.size = len(sc_code)
                    sc_src_ti.mode = 0o644
                    tf.addfile(sc_src_ti, io.BytesIO(sc_code))
                    has_files = True

                    # Add sitecustomize.pyc bytecode if compiled
                    if sc_pyc:
                        sc_ti = tarfile.TarInfo(name="sitecustomize.pyc")
                        sc_ti.type = tarfile.REGTYPE
                        sc_ti.size = len(sc_pyc)
                        sc_ti.mode = 0o644
                        tf.addfile(sc_ti, io.BytesIO(sc_pyc))
                        has_files = True

                for root, dirs, files in os.walk(src):
                    dirs[:] = [d for d in dirs if d not in excluded_top and not d.endswith((".dist-info", ".egg-info"))]

                    if Path(root) != src:
                        rel_dir = Path(root).relative_to(src)
                        if rel_dir.parts[0] not in excluded_top:
                            dir_name = rel_dir.as_posix()
                            if not dir_name.endswith("/"):
                                dir_name += "/"
                            dti = tarfile.TarInfo(name=dir_name)
                            dti.type = tarfile.DIRTYPE
                            dti.mode = 0o755
                            dti.mtime = int(Path(root).stat().st_mtime)
                            tf.addfile(dti)

                    for f in files:
                        full_f = Path(root) / f
                        rel_f = full_f.relative_to(src)
                        rel_parts = rel_f.parts
                        if rel_parts[0] in excluded_top or rel_parts[0].endswith((".dist-info", ".egg-info")):
                            continue
                        if rel_parts[0] in (
                            "AndroidManifest.xml",
                            "buildozer.spec",
                            ".lock",
                            ".gitignore",
                            "pyproject.toml",
                            "README.md",
                            "uv.lock",
                            ".python-version",
                        ):
                            continue
                        if f.lower().endswith(excluded_exts) or f == "resources.arsc":
                            continue
                        if f in ("sitecustomize.py", "sitecustomize.pyc") and has_native_so and not is_webview:
                            continue
                        rel_str = rel_f.as_posix()
                        file_bytes = full_f.read_bytes()
                        fti = tarfile.TarInfo(name=rel_str)
                        fti.type = tarfile.REGTYPE
                        fti.size = len(file_bytes)
                        fti.mode = 0o644
                        fti.mtime = int(full_f.stat().st_mtime)
                        tf.addfile(fti, io.BytesIO(file_bytes))
                        has_files = True

                        # Include .pyc if compiling and not already present on disk
                        if builder._compile_py and f.endswith(".py"):
                            existing_pyc = full_f.parent / f"{f}c"
                            if not existing_pyc.exists():
                                pyc_bytes = _compile_py_bytecode(full_f, f, target_version=target_py_ver)
                                if pyc_bytes:
                                    pyc_ti = tarfile.TarInfo(name=f"{rel_str}c")
                                    pyc_ti.type = tarfile.REGTYPE
                                    pyc_ti.size = len(pyc_bytes)
                                    pyc_ti.mode = 0o644
                                    pyc_ti.mtime = int(full_f.stat().st_mtime)
                                    tf.addfile(pyc_ti, io.BytesIO(pyc_bytes))

            tar_bytes = tar_buf.getvalue()
            if has_files and tar_bytes:
                builder.add_bytes("assets/private.tar", tar_bytes, compress=False)
                builder.add_bytes("assets/private.mp3", tar_bytes, compress=False)
                private_tar_bytes = tar_bytes

        # 6. resources.arsc with package_name, app_name, and "private_version" bound to private.tar SHA-1
        from pureapk.resources import ArscBuilder

        if arsc_bytes is None:
            arsc_bytes = ArscBuilder.generate_minimal_arsc(
                package_name=package_name or "org.pureapk.app",
                app_name=app_title or "PureAPK App",
            )

        if arsc_bytes is not None:
            priv_ver = None
            if private_tar_bytes:
                import hashlib
                priv_ver = hashlib.sha1(private_tar_bytes).hexdigest()
            arsc_bytes = ArscBuilder.patch_arsc(
                arsc_bytes,
                package_name=package_name,
                app_name=app_title,
                private_version=priv_ver,
            )
            if priv_ver:
                arsc_bytes = patch_arsc_private_version(arsc_bytes, priv_ver)
            builder.add_bytes("resources.arsc", arsc_bytes, compress=False)

        if channel:
            builder.add_bytes("assets/channel.txt", channel.strip().encode("utf-8"), compress=False)
    finally:
        if rt_zf is not None:
            rt_zf.close()





class KivyAppHelper:

    """Helper utilities and template generators for Kivy Android applications."""



    __slots__ = ()



    @staticmethod
    def generate_manifest_xml(
        package_name: str,
        app_title: str,
        version_code: int = 1,
        version_name: str = "0.1",
        orientation: str = "portrait",
        has_icon: bool = False,
    ) -> str:
        icon_attr = '\n        android:icon="@mipmap/ic_launcher"' if has_icon else ""
        return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}"
    android:versionCode="{version_code}"
    android:versionName="{version_name}">

    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    <uses-feature android:glEsVersion="0x00020000" android:required="true" />

    <application
        android:label="{app_title}"{icon_attr}
        android:extractNativeLibs="true"
        android:hardwareAccelerated="true">
        <activity
            android:name="org.kivy.android.PythonActivity"
            android:label="{app_title}"
            android:screenOrientation="{orientation}"
            android:configChanges="keyboard|keyboardHidden|orientation|screenSize"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""



    @staticmethod

    def generate_buildozer_spec(

        title: str = "Kivy App",

        package_name: str = "kivyapp",

        package_domain: str = "org.kivy",

        orientation: str = "portrait",

    ) -> str:

        return f"""[app]

title = {title}

package.name = {package_name}

package.domain = {package_domain}

source.dir = .

source.include_exts = py,png,jpg,kv,atlas,json,txt

version = 0.1

requirements = python3,kivy

orientation = {orientation}

android.minapi = 21

android.sdk = 34

android.ndk = 25b

android.archs = arm64-v8a, armeabi-v7a

android.permissions = INTERNET

"""



    @staticmethod

    def init_project(target_dir: Union[str, Path], title: str = "Kivy App") -> None:

        path = Path(target_dir)

        path.mkdir(parents=True, exist_ok=True)

        main_py = path / "main.py"

        if not main_py.exists():

            main_py.write_text(

                "from kivy.app import App\n"

                "from kivy.uix.label import Label\n\n"

                "class MainApp(App):\n"

                "    def build(self):\n"

                f"        return Label(text='Hello from {title}!')\n\n"

                "if __name__ == '__main__':\n"

                "    MainApp().run()\n",

                encoding="utf-8",

            )

        spec = path / "buildozer.spec"

        if not spec.exists():

            spec.write_text(KivyAppHelper.generate_buildozer_spec(title=title), encoding="utf-8")



    DEFAULT_RUNTIME_URL: str = "https://github.com/eminsk/pyapk/releases/download/runtime-py310/kivy-runtime-py310.apk"
    DEFAULT_RUNTIME_SHA256: str = "00b9959d542524dc8b33e2840702b6f02c5eb500e97478de380a5a1b55287aee"

    @staticmethod
    def ensure_runtime(
        cache_dir: Optional[Union[str, Path]] = None,
        download: bool = True,
    ) -> Optional[Path]:
        """Locates or downloads the prebuilt p4a Python 3.10 + Kivy 2.1 + SDL2 Android runtime APK."""
        import hashlib
        import tempfile
        import urllib.request

        env_rt = os.environ.get("PUREAPK_RUNTIME_APK")
        if env_rt:
            p = Path(env_rt)
            if p.exists():
                return p

        base_cache = Path(cache_dir) if cache_dir else (Path.home() / ".pureapk" / "runtime")
        cached_apk = base_cache / "kivy-runtime-py310.apk"
        if cached_apk.is_file() and cached_apk.stat().st_size > 1_000_000:
            return cached_apk

        if not download or os.environ.get("PUREAPK_OFFLINE") == "1":
            return None

        url = os.environ.get("PUREAPK_RUNTIME_URL", KivyAppHelper.DEFAULT_RUNTIME_URL)
        try:
            base_cache.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": "pureapk-runtime-fetcher/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = resp.read()
            if len(data) < 1_000_000:
                return None
            if url == KivyAppHelper.DEFAULT_RUNTIME_URL:
                digest = hashlib.sha256(data).hexdigest()
                if digest != KivyAppHelper.DEFAULT_RUNTIME_SHA256:
                    return None
            with tempfile.NamedTemporaryFile(dir=str(base_cache), suffix=".apk.tmp", delete=False) as tf:
                tf.write(data)
                tmp_name = tf.name
            os.replace(tmp_name, str(cached_apk))
            return cached_apk
        except Exception:
            return None

    @staticmethod
    def prepare_runtime(
        source_apk_or_dir: Union[str, Path],
        target_dir: Union[str, Path],
    ) -> Dict[str, Any]:
        """Extracts native Python/Kivy runtime (lib/*.so, classes*.dex, resources.arsc, res/, AndroidManifest.xml) into a project folder."""
        import io
        import shutil
        import tarfile
        import zipfile

        src_p = Path(source_apk_or_dir)
        if not src_p.exists():
            raise FileNotFoundError(f"Runtime source not found: {source_apk_or_dir}")

        dst_p = Path(target_dir)
        dst_p.mkdir(parents=True, exist_ok=True)

        extracted_so = 0
        dex_files: List[str] = []
        abis: set[str] = set()
        has_arsc = False
        has_manifest = False

        if src_p.is_dir():
            for dname in ("lib", "res"):
                sub = src_p / dname
                if sub.is_dir():
                    for root, _, files in os.walk(sub):
                        for f in files:
                            full = Path(root) / f
                            rel = full.relative_to(src_p)
                            out_f = dst_p / rel
                            out_f.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(full, out_f)
                            if dname == "lib" and f.endswith(".so"):
                                extracted_so += 1
                                if len(rel.parts) >= 2:
                                    abis.add(rel.parts[1])
            for dex_f in sorted(src_p.glob("classes*.dex")):
                shutil.copy2(dex_f, dst_p / dex_f.name)
                dex_files.append(dex_f.name)
            if (src_p / "resources.arsc").is_file():
                shutil.copy2(src_p / "resources.arsc", dst_p / "resources.arsc")
                has_arsc = True
            if (src_p / "AndroidManifest.xml").is_file():
                shutil.copy2(src_p / "AndroidManifest.xml", dst_p / "AndroidManifest.xml")
                has_manifest = True
            if (src_p / "sitecustomize.pyc").is_file():
                shutil.copy2(src_p / "sitecustomize.pyc", dst_p / "sitecustomize.pyc")
        else:
            with zipfile.ZipFile(src_p, "r") as zf:
                for name in zf.namelist():
                    if name.endswith("/"):
                        continue
                    if name.startswith("lib/"):
                        out_f = dst_p / name
                        out_f.parent.mkdir(parents=True, exist_ok=True)
                        out_f.write_bytes(zf.read(name))
                        if name.endswith(".so"):
                            extracted_so += 1
                            parts = name.split("/")
                            if len(parts) >= 3:
                                abis.add(parts[1])
                    elif name.startswith("res/"):
                        out_f = dst_p / name
                        out_f.parent.mkdir(parents=True, exist_ok=True)
                        out_f.write_bytes(zf.read(name))
                    elif "/" not in name and name.startswith("classes") and name.endswith(".dex"):
                        (dst_p / name).write_bytes(zf.read(name))
                        dex_files.append(name)
                    elif name == "resources.arsc":
                        (dst_p / "resources.arsc").write_bytes(zf.read(name))
                        has_arsc = True
                    elif name == "AndroidManifest.xml":
                        (dst_p / "AndroidManifest.xml").write_bytes(zf.read(name))
                        has_manifest = True
                    elif name == "assets/private.tar":
                        try:
                            with tarfile.open(fileobj=io.BytesIO(zf.read(name))) as btf:
                                for member in btf.getmembers():
                                    if member.name.lstrip("./") == "sitecustomize.pyc":
                                        extr = btf.extractfile(member)
                                        if extr:
                                            (dst_p / "sitecustomize.pyc").write_bytes(extr.read())
                                        break
                        except Exception:
                            pass

        return {
            "target_dir": str(dst_p),
            "abis": sorted(abis),
            "extracted_so_count": extracted_so,
            "dex_files": sorted(dex_files),
            "has_arsc": has_arsc,
            "has_manifest": has_manifest,
            "python_version": _detect_runtime_python_version(dst_p),
        }

    @staticmethod
    def pack_app(
        source_dir: Union[str, Path],
        output_apk: Union[str, Path],
        package_name: Optional[str] = None,
        app_title: Optional[str] = None,
        release: bool = False,
        channel: Optional[str] = None,
        orientation: Optional[str] = None,
        keystore: Optional[Union[str, Path]] = None,
        password: str = "",
        alias: Optional[str] = None,
        runtime_apk: Optional[Union[str, Path]] = None,
        skeleton: bool = False,
    ) -> None:
        """Packs a Kivy project directory into a standard Android APK."""
        import re
        import zipfile
        from pureapk.builder import APKBuilder
        from pureapk.manifest import AxmlEncoder
        from pureapk.stores import ReleaseHelper

        src = Path(source_dir)

        # Auto-resolve prebuilt Kivy/Python runtime if project does not already contain lib/*.so
        if runtime_apk is None and not skeleton and os.environ.get("PUREAPK_SKELETON") != "1":
            has_local_so = False
            if (src / "lib").is_dir():
                for _, _, files_l in os.walk(src / "lib"):
                    if any(f.endswith(".so") for f in files_l):
                        has_local_so = True
                        break
            if not has_local_so:
                in_pytest = os.environ.get("PYTEST_CURRENT_TEST") is not None
                if not in_pytest or os.environ.get("PUREAPK_AUTO_RUNTIME") == "1":
                    resolved_rt = KivyAppHelper.ensure_runtime(download=True)
                    if resolved_rt is not None:
                        runtime_apk = resolved_rt

        spec_file = src / "buildozer.spec"
        spec_title = None
        spec_pkg = None
        spec_orientation = "portrait"
        if spec_file.exists():
            try:
                import configparser
                cfg = configparser.ConfigParser()
                cfg.read(str(spec_file), encoding="utf-8")
                if "app" in cfg:
                    spec_title = cfg["app"].get("title")
                    p_name = cfg["app"].get("package.name")
                    p_dom = cfg["app"].get("package.domain")
                    if p_name and p_dom:
                        spec_pkg = f"{p_dom}.{p_name}"
                    elif p_name:
                        spec_pkg = p_name
                    spec_orientation = cfg["app"].get("orientation", "portrait")
            except Exception:
                pass

        final_title = app_title or spec_title or "Kivy App"
        final_pkg = package_name or spec_pkg or "org.kivy.app"
        final_orient = orientation or spec_orientation or "portrait"

        # Detect if project contains launcher icon resources
        has_icon = False
        res_dir = src / "res"
        if res_dir.is_dir():
            for _, _, files in os.walk(res_dir):
                if any(f.startswith("ic_launcher") or f.endswith((".png", ".webp")) for f in files):
                    has_icon = True
                    break

        builder = APKBuilder(
            output_apk,
            auto_axml=True,
            auto_dex=True,
            auto_resources=True,
            sign=True,
            compile_py=True,
            keystore_path=keystore,
            keystore_password=password,
            key_alias=alias or ("release" if (release or keystore) else "androiddebugkey"),
        )

        manifest_path = src / "AndroidManifest.xml"
        rt_manifest_bytes: Optional[bytes] = None
        if runtime_apk:
            rt_p = Path(runtime_apk)
            if rt_p.is_dir() and (rt_p / "AndroidManifest.xml").is_file():
                rt_manifest_bytes = (rt_p / "AndroidManifest.xml").read_bytes()
            elif rt_p.is_file():
                with zipfile.ZipFile(rt_p, "r") as zf:
                    if "AndroidManifest.xml" in zf.namelist():
                        rt_manifest_bytes = zf.read("AndroidManifest.xml")

        if manifest_path.exists() or rt_manifest_bytes is not None:
            ver_code: Optional[int] = None
            ver_name: Optional[str] = None
            xml_pkg: Optional[str] = None
            xml_label: Optional[str] = None
            local_m = manifest_path.read_bytes() if manifest_path.exists() else b""
            if local_m and not (len(local_m) >= 4 and local_m[:2] == b"\x03\x00"):
                txt_m = local_m.decode("utf-8", errors="ignore")
                m_vc = re.search(r'android:versionCode="(\d+)"', txt_m)
                if m_vc:
                    ver_code = int(m_vc.group(1))
                m_vn = re.search(r'android:versionName="([^"]+)"', txt_m)
                if m_vn:
                    ver_name = m_vn.group(1)
                m_pk = re.search(r'\bpackage="([^"]+)"', txt_m)
                if m_pk:
                    xml_pkg = m_pk.group(1)
                m_lb = re.search(r'android:label="([^"@][^"]*)"', txt_m)
                if m_lb:
                    xml_label = m_lb.group(1)

            raw_m = local_m if local_m else (rt_manifest_bytes or b"")
            if len(raw_m) >= 4 and raw_m[:2] == b"\x03\x00":
                raw_m = AxmlEncoder.patch_binary_axml(
                    raw_m,
                    package_name=package_name or spec_pkg or xml_pkg,
                    app_label=app_title or spec_title or xml_label,
                    version_code=ver_code,
                    version_name=ver_name,
                )
            builder.add_bytes("AndroidManifest.xml", raw_m)
        else:
            manifest_str = KivyAppHelper.generate_manifest_xml(
                final_pkg,
                final_title,
                orientation=final_orient,
                has_icon=has_icon,
            )
            if release:
                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)
            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))

        _pack_framework_project(
            builder,
            src,
            channel=channel,
            package_name=final_pkg,
            app_title=final_title,
            runtime_apk=runtime_apk,
        )
        builder.build()





class PygameAppHelper:

    """Helper utilities and template generators for Pygame Android applications."""



    __slots__ = ()



    @staticmethod
    def generate_manifest_xml(
        package_name: str,
        app_title: str,
        version_code: int = 1,
        version_name: str = "0.1",
        orientation: str = "landscape",
        has_icon: bool = False,
    ) -> str:
        icon_attr = '\n        android:icon="@mipmap/ic_launcher"' if has_icon else ""
        return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}"
    android:versionCode="{version_code}"
    android:versionName="{version_name}">

    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.VIBRATE" />
    <uses-feature android:glEsVersion="0x00020000" android:required="true" />

    <application
        android:label="{app_title}"{icon_attr}
        android:extractNativeLibs="true"
        android:hardwareAccelerated="true">
        <activity
            android:name="org.renpy.android.PythonSDLActivity"
            android:label="{app_title}"
            android:screenOrientation="{orientation}"
            android:configChanges="keyboard|keyboardHidden|orientation|screenSize"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""



    @staticmethod

    def generate_buildozer_spec(

        title: str = "Pygame App",

        package_name: str = "pygameapp",

        package_domain: str = "org.pygame",

        orientation: str = "landscape",

    ) -> str:

        return f"""[app]

title = {title}

package.name = {package_name}

package.domain = {package_domain}

source.dir = .

source.include_exts = py,png,jpg,ogg,wav,mp3,ttf,json

version = 0.1

requirements = python3,pygame

orientation = {orientation}

android.minapi = 21

android.sdk = 34

android.ndk = 25b

android.archs = arm64-v8a, armeabi-v7a

android.permissions = INTERNET,VIBRATE

"""



    @staticmethod

    def init_project(target_dir: Union[str, Path], title: str = "Pygame App") -> None:

        path = Path(target_dir)

        path.mkdir(parents=True, exist_ok=True)

        main_py = path / "main.py"

        if not main_py.exists():

            main_py.write_text(

                "import pygame\n"

                "import sys\n\n"

                "pygame.init()\n"

                "screen = pygame.display.set_mode((800, 600))\n"

                f"pygame.display.set_caption('{title}')\n"

                "clock = pygame.time.Clock()\n\n"

                "running = True\n"

                "while running:\n"

                "    for event in pygame.event.get():\n"

                "        if event.type == pygame.QUIT:\n"

                "            running = False\n"

                "    screen.fill((30, 30, 30))\n"

                "    pygame.display.flip()\n"

                "    clock.tick(60)\n"

                "pygame.quit()\n"

                "sys.exit()\n",

                encoding="utf-8",

            )

        spec = path / "buildozer.spec"

        if not spec.exists():

            spec.write_text(PygameAppHelper.generate_buildozer_spec(title=title), encoding="utf-8")



    @staticmethod
    def pack_app(
        source_dir: Union[str, Path],
        output_apk: Union[str, Path],
        package_name: Optional[str] = None,
        app_title: Optional[str] = None,
        release: bool = False,
        channel: Optional[str] = None,
        orientation: Optional[str] = None,
        keystore: Optional[Union[str, Path]] = None,
        password: str = "",
        alias: Optional[str] = None,
        runtime_apk: Optional[Union[str, Path]] = None,
        skeleton: bool = False,
    ) -> None:
        """Packs a Pygame project directory into a standard Android APK."""
        import re
        import zipfile
        from pureapk.builder import APKBuilder
        from pureapk.manifest import AxmlEncoder
        from pureapk.stores import ReleaseHelper

        src = Path(source_dir)

        # Auto-resolve prebuilt Pygame/Python runtime if project does not already contain lib/*.so
        if runtime_apk is None and not skeleton and os.environ.get("PUREAPK_SKELETON") != "1":
            has_local_so = False
            if (src / "lib").is_dir():
                for _, _, files_l in os.walk(src / "lib"):
                    if any(f.endswith(".so") for f in files_l):
                        has_local_so = True
                        break
            if not has_local_so:
                in_pytest = os.environ.get("PYTEST_CURRENT_TEST") is not None
                if not in_pytest or os.environ.get("PUREAPK_AUTO_RUNTIME") == "1":
                    resolved_rt = KivyAppHelper.ensure_runtime(download=True)
                    if resolved_rt is not None:
                        runtime_apk = resolved_rt

        spec_file = src / "buildozer.spec"
        spec_title = None
        spec_pkg = None
        spec_orientation = "landscape"
        if spec_file.exists():
            try:
                import configparser
                cfg = configparser.ConfigParser()
                cfg.read(str(spec_file), encoding="utf-8")
                if "app" in cfg:
                    spec_title = cfg["app"].get("title")
                    p_name = cfg["app"].get("package.name")
                    p_dom = cfg["app"].get("package.domain")
                    if p_name and p_dom:
                        spec_pkg = f"{p_dom}.{p_name}"
                    elif p_name:
                        spec_pkg = p_name
                    spec_orientation = cfg["app"].get("orientation", "landscape")
            except Exception:
                pass

        final_title = app_title or spec_title or "Pygame App"
        final_pkg = package_name or spec_pkg or "org.pygame.app"
        final_orient = orientation or spec_orientation or "landscape"

        has_icon = False
        res_dir = src / "res"
        if res_dir.is_dir():
            for _, _, files in os.walk(res_dir):
                if any(f.startswith("ic_launcher") or f.endswith((".png", ".webp")) for f in files):
                    has_icon = True
                    break

        builder = APKBuilder(
            output_apk,
            auto_axml=True,
            auto_dex=True,
            auto_resources=True,
            sign=True,
            compile_py=True,
            keystore_path=keystore,
            keystore_password=password,
            key_alias=alias or ("release" if (release or keystore) else "androiddebugkey"),
        )

        manifest_path = src / "AndroidManifest.xml"
        if manifest_path.exists():
            builder.add_file(manifest_path, "AndroidManifest.xml")
        else:
            manifest_str = PygameAppHelper.generate_manifest_xml(
                final_pkg,
                final_title,
                orientation=final_orient,
                has_icon=has_icon,
            )
            if release:
                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)
            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))

        _pack_framework_project(
            builder,
            src,
            channel=channel,
            package_name=final_pkg,
            app_title=final_title,
            runtime_apk=runtime_apk,
        )
        builder.build()





class FletAppHelper:

    """Helper utilities and template generators for Flet (Flutter/Python) mobile applications."""



    __slots__ = ()



    @staticmethod

    def generate_manifest_xml(

        package_name: str,

        app_title: str,

        version_code: int = 1,

        version_name: str = "0.1",

        orientation: str = "sensor",
        has_icon: bool = False,
    ) -> str:

        icon_attr = '\n        android:icon="@mipmap/ic_launcher"' if has_icon else ""
        return f"""<?xml version="1.0" encoding="utf-8"?>

<manifest xmlns:android="http://schemas.android.com/apk/res/android"

    package="{package_name}"

    android:versionCode="{version_code}"

    android:versionName="{version_name}">



    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />

    <uses-permission android:name="android.permission.INTERNET" />



    <application

        android:label="{app_title}"

        {icon_attr}

        android:hardwareAccelerated="true">

        <activity

            android:name="io.flet.FletActivity"

            android:label="{app_title}"

            android:screenOrientation="{orientation}"

            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"

            android:hardwareAccelerated="true"

            android:windowSoftInputMode="adjustResize"

            android:exported="true">

            <intent-filter>

                <action android:name="android.intent.action.MAIN" />

                <category android:name="android.intent.category.LAUNCHER" />

            </intent-filter>

        </activity>

    </application>

</manifest>

"""



    @staticmethod

    def init_project(target_dir: Union[str, Path], title: str = "Flet App") -> None:

        path = Path(target_dir)

        path.mkdir(parents=True, exist_ok=True)

        main_py = path / "main.py"

        if not main_py.exists():

            main_py.write_text(

                "import flet as ft\n\n"

                "def main(page: ft.Page):\n"

                f"    page.title = '{title}'\n"

                "    page.vertical_alignment = ft.MainAxisAlignment.CENTER\n"

                "    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER\n\n"

                "    txt_number = ft.TextField(value='0', text_align=ft.TextAlign.RIGHT, width=100)\n\n"

                "    def minus_click(e):\n"

                "        txt_number.value = str(int(txt_number.value) - 1)\n"

                "        page.update()\n\n"

                "    def plus_click(e):\n"

                "        txt_number.value = str(int(txt_number.value) + 1)\n"

                "        page.update()\n\n"

                "    page.add(\n"

                "        ft.Row(\n"

                "            [\n"

                "                ft.IconButton(ft.icons.REMOVE, on_click=minus_click),\n"

                "                txt_number,\n"

                "                ft.IconButton(ft.icons.ADD, on_click=plus_click),\n"

                "            ],\n"

                "            alignment=ft.MainAxisAlignment.CENTER,\n"

                "        )\n"

                "    )\n\n"

                "if __name__ == '__main__':\n"

                "    ft.app(target=main)\n",

                encoding="utf-8",

            )



    @staticmethod

    def pack_app(

        source_dir: Union[str, Path],

        output_apk: Union[str, Path],

        package_name: Optional[str] = None,

        app_title: str = "Flet App",

        release: bool = False,

        channel: Optional[str] = None,
        keystore: Optional[Union[str, Path]] = None, password: str = "", alias: Optional[str] = None) -> None:

        from pureapk.builder import APKBuilder

        from pureapk.stores import ReleaseHelper

        src = Path(source_dir)

        has_icon = False
        res_dir = src / "res"
        if res_dir.is_dir():
            for _, _, files in os.walk(res_dir):
                if any(f.startswith("ic_launcher") or f.endswith((".png", ".webp")) for f in files):
                    has_icon = True
                    break

        builder = APKBuilder(
            output_apk,
            auto_axml=True,
            auto_dex=True,
            auto_resources=True,
            sign=True,
            compile_py=True,
            keystore_path=keystore,
            keystore_password=password,
            key_alias=alias or ("release" if (release or keystore) else "androiddebugkey"),
        )

        manifest_path = src / "AndroidManifest.xml"

        if manifest_path.exists():

            builder.add_file(manifest_path, "AndroidManifest.xml")

        else:

            manifest_str = FletAppHelper.generate_manifest_xml(package_name or "com.flet.app", app_title, has_icon=has_icon)

            if release:

                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)

            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))



        _pack_framework_project(builder, src, channel=channel)

        builder.build()





class TogaAppHelper:

    """Helper utilities and template generators for BeeWare Toga (native UI) applications."""



    __slots__ = ()



    @staticmethod

    def generate_manifest_xml(

        package_name: str,

        app_title: str,

        version_code: int = 1,

        version_name: str = "0.1",

        orientation: str = "portrait",
        has_icon: bool = False,
    ) -> str:

        icon_attr = '\n        android:icon="@mipmap/ic_launcher"' if has_icon else ""
        return f"""<?xml version="1.0" encoding="utf-8"?>

<manifest xmlns:android="http://schemas.android.com/apk/res/android"

    package="{package_name}"

    android:versionCode="{version_code}"

    android:versionName="{version_name}">



    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />

    <uses-permission android:name="android.permission.INTERNET" />



    <application

        android:label="{app_title}"

        {icon_attr}>

        <activity

            android:name="org.beeware.android.MainActivity"

            android:label="{app_title}"

            android:screenOrientation="{orientation}"

            android:exported="true">

            <intent-filter>

                <action android:name="android.intent.action.MAIN" />

                <category android:name="android.intent.category.LAUNCHER" />

            </intent-filter>

        </activity>

    </application>

</manifest>

"""



    @staticmethod

    def init_project(target_dir: Union[str, Path], title: str = "Toga App") -> None:

        path = Path(target_dir)

        path.mkdir(parents=True, exist_ok=True)

        app_py = path / "app.py"

        if not app_py.exists():

            app_py.write_text(

                "import toga\n"

                "from toga.style import Pack\n"

                "from toga.style.pack import COLUMN, ROW\n\n"

                f"def build(app):\n"

                "    box = toga.Box(style=Pack(direction=COLUMN, padding=20))\n"

                f"    label = toga.Label('Welcome to {title}!', style=Pack(padding=(0, 0, 10, 0)))\n"

                "    button = toga.Button('Click Me', on_press=lambda widget: app.main_window.info_dialog('Hello', 'Button pressed!'))\n"

                "    box.add(label)\n"

                "    box.add(button)\n"

                "    return box\n\n"

                "def main():\n"

                f"    return toga.App('{title}', 'org.beeware.app', startup=build)\n\n"

                "if __name__ == '__main__':\n"

                "    main().main_loop()\n",

                encoding="utf-8",

            )



    @staticmethod

    def pack_app(

        source_dir: Union[str, Path],

        output_apk: Union[str, Path],

        package_name: Optional[str] = None,

        app_title: str = "Toga App",

        release: bool = False,

        channel: Optional[str] = None,
        keystore: Optional[Union[str, Path]] = None, password: str = "", alias: Optional[str] = None) -> None:

        from pureapk.builder import APKBuilder

        from pureapk.stores import ReleaseHelper

        src = Path(source_dir)

        has_icon = False
        res_dir = src / "res"
        if res_dir.is_dir():
            for _, _, files in os.walk(res_dir):
                if any(f.startswith("ic_launcher") or f.endswith((".png", ".webp")) for f in files):
                    has_icon = True
                    break

        builder = APKBuilder(
            output_apk,
            auto_axml=True,
            auto_dex=True,
            auto_resources=True,
            sign=True,
            compile_py=True,
            keystore_path=keystore,
            keystore_password=password,
            key_alias=alias or ("release" if (release or keystore) else "androiddebugkey"),
        )

        manifest_path = src / "AndroidManifest.xml"

        if manifest_path.exists():

            builder.add_file(manifest_path, "AndroidManifest.xml")

        else:

            manifest_str = TogaAppHelper.generate_manifest_xml(package_name or "org.beeware.app", app_title, has_icon=has_icon)

            if release:

                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)

            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))



        _pack_framework_project(builder, src, channel=channel)

        builder.build()





class RenPyAppHelper:

    """Helper utilities and template generators for Ren'Py visual novels."""



    __slots__ = ()



    @staticmethod

    def generate_manifest_xml(

        package_name: str,

        app_title: str,

        version_code: int = 1,

        version_name: str = "0.1",

        orientation: str = "landscape",
        has_icon: bool = False,
    ) -> str:

        icon_attr = '\n        android:icon="@mipmap/ic_launcher"' if has_icon else ""
        return f"""<?xml version="1.0" encoding="utf-8"?>

<manifest xmlns:android="http://schemas.android.com/apk/res/android"

    package="{package_name}"

    android:versionCode="{version_code}"

    android:versionName="{version_name}">



    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />

    <uses-permission android:name="android.permission.INTERNET" />

    <uses-permission android:name="android.permission.VIBRATE" />



    <application

        android:label="{app_title}"

        {icon_attr}

        android:hardwareAccelerated="true">

        <activity

            android:name="org.renpy.android.PythonSDLActivity"

            android:label="{app_title}"

            android:screenOrientation="{orientation}"

            android:configChanges="keyboard|keyboardHidden|orientation|screenSize"

            android:exported="true">

            <intent-filter>

                <action android:name="android.intent.action.MAIN" />

                <category android:name="android.intent.category.LAUNCHER" />

            </intent-filter>

        </activity>

    </application>

</manifest>

"""



    @staticmethod

    def init_project(target_dir: Union[str, Path], title: str = "Visual Novel") -> None:

        path = Path(target_dir)

        game_dir = path / "game"

        game_dir.mkdir(parents=True, exist_ok=True)

        script_rpy = game_dir / "script.rpy"

        if not script_rpy.exists():

            script_rpy.write_text(

                "define e = Character('Eileen')\n\n"

                "label start:\n"

                f"    e 'Welcome to {title} on Android!'\n"

                "    e 'You created this game in pure Python without Android Studio.'\n"

                "    return\n",

                encoding="utf-8",

            )



    @staticmethod

    def pack_app(

        source_dir: Union[str, Path],

        output_apk: Union[str, Path],

        package_name: Optional[str] = None,

        app_title: str = "Visual Novel",

        release: bool = False,

        channel: Optional[str] = None,
        keystore: Optional[Union[str, Path]] = None, password: str = "", alias: Optional[str] = None) -> None:

        from pureapk.builder import APKBuilder

        from pureapk.stores import ReleaseHelper

        src = Path(source_dir)

        has_icon = False
        res_dir = src / "res"
        if res_dir.is_dir():
            for _, _, files in os.walk(res_dir):
                if any(f.startswith("ic_launcher") or f.endswith((".png", ".webp")) for f in files):
                    has_icon = True
                    break

        builder = APKBuilder(
            output_apk,
            auto_axml=True,
            auto_dex=True,
            auto_resources=True,
            sign=True,
            compile_py=True,
            keystore_path=keystore,
            keystore_password=password,
            key_alias=alias or ("release" if (release or keystore) else "androiddebugkey"),
        )

        manifest_path = src / "AndroidManifest.xml"

        if manifest_path.exists():

            builder.add_file(manifest_path, "AndroidManifest.xml")

        else:

            manifest_str = RenPyAppHelper.generate_manifest_xml(package_name or "org.renpy.game", app_title, has_icon=has_icon)

            if release:

                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)

            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))



        _pack_framework_project(builder, src, channel=channel)

        builder.build()





class WebViewAppHelper:

    """Helper utilities and template generators for Python + HTML5/CSS/JS WebView applications."""



    __slots__ = ()



    @staticmethod

    def generate_manifest_xml(

        package_name: str,

        app_title: str,

        version_code: int = 1,

        version_name: str = "0.1",

        orientation: str = "sensor",
        has_icon: bool = False,
    ) -> str:

        icon_attr = '\n        android:icon="@mipmap/ic_launcher"' if has_icon else ""
        return f"""<?xml version="1.0" encoding="utf-8"?>

<manifest xmlns:android="http://schemas.android.com/apk/res/android"

    package="{package_name}"

    android:versionCode="{version_code}"

    android:versionName="{version_name}">



    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />

    <uses-permission android:name="android.permission.INTERNET" />



    <application

        android:label="{app_title}"

        {icon_attr}

        android:hardwareAccelerated="true">

        <activity

            android:name="android.webkit.WebViewActivity"

            android:label="{app_title}"

            android:screenOrientation="{orientation}"

            android:configChanges="orientation|screenSize"

            android:exported="true">

            <intent-filter>

                <action android:name="android.intent.action.MAIN" />

                <category android:name="android.intent.category.LAUNCHER" />

            </intent-filter>

        </activity>

    </application>

</manifest>

"""



    @staticmethod

    def init_project(target_dir: Union[str, Path], title: str = "WebView App") -> None:

        path = Path(target_dir)

        assets_dir = path / "assets"

        assets_dir.mkdir(parents=True, exist_ok=True)

        html_file = assets_dir / "index.html"

        if not html_file.exists():

            html_file.write_text(

                "<!DOCTYPE html>\n"

                "<html>\n"

                "<head>\n"

                "    <meta charset='utf-8'>\n"

                "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"

                f"    <title>{title}</title>\n"

                "    <style>\n"

                "        body { font-family: system-ui, sans-serif; background: #121212; color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }\n"

                "        .card { background: #1e1e1e; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); text-align: center; }\n"

                "        button { background: #6200ee; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 6px; cursor: pointer; margin-top: 1rem; }\n"

                "    </style>\n"

                "</head>\n"

                "<body>\n"

                "    <div class='card'>\n"

                f"        <h1>{title}</h1>\n"

                "        <p>Ultra-lightweight Python WebView Mobile Application</p>\n"

                "        <button onclick='alert(\"Clicked from Mobile!\")'>Click Me</button>\n"

                "    </div>\n"

                "</body>\n"

                "</html>\n",

                encoding="utf-8",

            )

        main_py = path / "main.py"

        if not main_py.exists():

            main_py.write_text('#!/usr/bin/env python3\nprint("Running WebView backend...")\n', encoding="utf-8")



    @staticmethod

    def pack_app(

        source_dir: Union[str, Path],

        output_apk: Union[str, Path],

        package_name: Optional[str] = None,

        app_title: str = "WebView App",

        release: bool = False,

        channel: Optional[str] = None,
        keystore: Optional[Union[str, Path]] = None, password: str = "", alias: Optional[str] = None) -> None:

        from pureapk.builder import APKBuilder

        from pureapk.stores import ReleaseHelper

        src = Path(source_dir)

        has_icon = False
        res_dir = src / "res"
        if res_dir.is_dir():
            for _, _, files in os.walk(res_dir):
                if any(f.startswith("ic_launcher") or f.endswith((".png", ".webp")) for f in files):
                    has_icon = True
                    break

        builder = APKBuilder(
            output_apk,
            auto_axml=True,
            auto_dex=True,
            auto_resources=True,
            sign=True,
            compile_py=True,
            keystore_path=keystore,
            keystore_password=password,
            key_alias=alias or ("release" if (release or keystore) else "androiddebugkey"),
        )

        manifest_path = src / "AndroidManifest.xml"

        if manifest_path.exists():

            builder.add_file(manifest_path, "AndroidManifest.xml")

        else:

            manifest_str = WebViewAppHelper.generate_manifest_xml(package_name or "com.webview.app", app_title, has_icon=has_icon)

            if release:

                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)

            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))



        _pack_framework_project(builder, src, is_webview=True, channel=channel)

        builder.build()





class PySideAppHelper:

    """Helper utilities and template generators for Qt for Android (PySide6 / PyQt6) applications."""



    __slots__ = ()



    @staticmethod

    def generate_manifest_xml(

        package_name: str,

        app_title: str,

        version_code: int = 1,

        version_name: str = "0.1",

        orientation: str = "unspecified",
        has_icon: bool = False,
    ) -> str:

        icon_attr = '\n        android:icon="@mipmap/ic_launcher"' if has_icon else ""
        return f"""<?xml version="1.0" encoding="utf-8"?>

<manifest xmlns:android="http://schemas.android.com/apk/res/android"

    package="{package_name}"

    android:versionCode="{version_code}"

    android:versionName="{version_name}">



    <uses-sdk android:minSdkVersion="23" android:targetSdkVersion="34" />

    <uses-permission android:name="android.permission.INTERNET" />

    <uses-feature android:glEsVersion="0x00020000" android:required="true" />



    <application

        android:label="{app_title}"

        {icon_attr}

        android:hardwareAccelerated="true">

        <activity

            android:name="org.qtproject.qt.android.bindings.QtActivity"

            android:label="{app_title}"

            android:screenOrientation="{orientation}"

            android:configChanges="orientation|screenSize"

            android:exported="true">

            <intent-filter>

                <action android:name="android.intent.action.MAIN" />

                <category android:name="android.intent.category.LAUNCHER" />

            </intent-filter>

            <meta-data android:name="android.app.lib_name" android:value="main" />

        </activity>

    </application>

</manifest>

"""



    @staticmethod

    def init_project(target_dir: Union[str, Path], title: str = "PySide App") -> None:

        path = Path(target_dir)

        path.mkdir(parents=True, exist_ok=True)

        main_py = path / "main.py"

        if not main_py.exists():

            main_py.write_text(

                "import sys\n"

                "try:\n"

                "    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow\n"

                "except ImportError:\n"

                "    from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow\n\n"

                "class MainWindow(QMainWindow):\n"

                "    def __init__(self):\n"

                "        super().__init__()\n"

                f"        self.setWindowTitle('{title}')\n"

                f"        label = QLabel('Hello from {title} (Qt for Android)!', self)\n"

                "        self.setCentralWidget(label)\n\n"

                "if __name__ == '__main__':\n"

                "    app = QApplication(sys.argv)\n"

                "    win = MainWindow()\n"

                "    win.show()\n"

                "    sys.exit(app.exec())\n",

                encoding="utf-8",

            )



    @staticmethod

    def pack_app(

        source_dir: Union[str, Path],

        output_apk: Union[str, Path],

        package_name: str = "org.qtproject.pysideapp",

        app_title: str = "PySide App",

        release: bool = False,

        channel: Optional[str] = None,
        keystore: Optional[Union[str, Path]] = None, password: str = "", alias: Optional[str] = None) -> None:

        from pureapk.builder import APKBuilder

        from pureapk.stores import ReleaseHelper

        src = Path(source_dir)

        has_icon = False
        res_dir = src / "res"
        if res_dir.is_dir():
            for _, _, files in os.walk(res_dir):
                if any(f.startswith("ic_launcher") or f.endswith((".png", ".webp")) for f in files):
                    has_icon = True
                    break

        builder = APKBuilder(
            output_apk,
            auto_axml=True,
            auto_dex=True,
            auto_resources=True,
            sign=True,
            compile_py=True,
            keystore_path=keystore,
            keystore_password=password,
            key_alias=alias or ("release" if (release or keystore) else "androiddebugkey"),
        )

        manifest_path = src / "AndroidManifest.xml"

        if manifest_path.exists():

            builder.add_file(manifest_path, "AndroidManifest.xml")

        else:

            manifest_str = PySideAppHelper.generate_manifest_xml(package_name or "org.qtproject.example", app_title, has_icon=has_icon)

            if release:

                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)

            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))



        _pack_framework_project(builder, src, channel=channel)

        builder.build()





# Alias for PyQt applications

PyQtAppHelper = PySideAppHelper



