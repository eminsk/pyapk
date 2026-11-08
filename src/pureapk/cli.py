"""Professional CLI interface for inspecting, analyzing, and building Android APKs.

Provides rich subcommands with JSON output options and high-speed execution.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence

from pureapk.apk import APK
from pureapk.builder import pack


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_info(args: argparse.Namespace) -> int:
    with APK(args.apk_path) as apk:
        data = apk.info()
        output_dispatch = {
            True: lambda: _print_json(data),
            False: lambda: _format_info_human(apk, data),
        }
        output_dispatch[args.json]()
    return 0


def _format_info_human(apk: APK, data: Dict[str, Any]) -> None:
    print(f"Package:        {data['package_name']}")
    print(f"Version Name:   {data['version_name']}")
    print(f"Version Code:   {data['version_code']}")
    print(f"Min SDK:        {data['min_sdk_version']}")
    print(f"Target SDK:     {data['target_sdk_version']}")
    print(f"App Label:      {data['application_label']}")
    print(f"Framework:      {data.get('framework', 'native').capitalize()}")
    print(f"Is Python App:  {data.get('is_python_app', False)}")
    print(f"Total Files:    {data['total_files']}")
    print(f"Architectures:  {', '.join(data['native_architectures']) or 'Universal (no native libs)'}")
    print(f"Permissions:    {len(data['permissions'])}")
    print(f"Activities:     {len(data['activities'])}")
    print(f"DEX Classes:    {data['dex']['total_classes']}")
    print(f"DEX Methods:    {data['dex']['total_methods']}")
    print(f"16KB Aligned:   {data.get('is_aligned_16k', False)} (Android 15 ready)")
    print(f"Signed:         {data['signature']['is_signed']} ({', '.join(data['signature']['schemes']) or 'none'})")


def cmd_manifest(args: argparse.Namespace) -> int:
    with APK(args.apk_path) as apk:
        output_dispatch = {
            True: lambda: _print_json(apk.manifest.as_dict()),
            False: lambda: print(apk.manifest.xml_string or "<manifest />"),
        }
        output_dispatch[args.json]()
    return 0


def cmd_permissions(args: argparse.Namespace) -> int:
    with APK(args.apk_path) as apk:
        perms = list(apk.permissions)
        output_dispatch = {
            True: lambda: _print_json({"permissions": perms}),
            False: lambda: print("\n".join(perms) if perms else "No permissions declared."),
        }
        output_dispatch[args.json]()
    return 0


def cmd_dex(args: argparse.Namespace) -> int:
    with APK(args.apk_path) as apk:
        dex_info = apk.dex.as_dict()
        output_dispatch = {
            True: lambda: _print_json(dex_info),
            False: lambda: _format_dex_human(dex_info),
        }
        output_dispatch[args.json]()
    return 0


def _format_dex_human(dex_info: Dict[str, Any]) -> None:
    print(f"Total DEX Files: {dex_info['dex_count']}")
    print(f"Total Classes:   {dex_info['total_classes']}")
    print(f"Total Methods:   {dex_info['total_methods']}")
    print(f"Total Fields:    {dex_info['total_fields']}")
    print(f"Total Strings:   {dex_info['total_strings']}")
    print(f"Total Size:      {dex_info['total_dex_bytes']} bytes")


def cmd_files(args: argparse.Namespace) -> int:
    with APK(args.apk_path) as apk:
        files = list(map(lambda f: f.as_dict(), apk.files))
        output_dispatch = {
            True: lambda: _print_json({"files": files}),
            False: lambda: _format_files_human(files),
        }
        output_dispatch[args.json]()
    return 0


def _format_files_human(files: List[Dict[str, Any]]) -> None:
    header = f"{'Size':>10}  {'Compressed':>10}  {'CRC32':>10}  {'Filename'}"
    print(header)
    print("-" * len(header))
    for f in files:
        print(f"{f['file_size']:>10}  {f['compress_size']:>10}  {f['crc32']:>10}  {f['filename']}")


def cmd_verify(args: argparse.Namespace) -> int:
    with APK(args.apk_path) as apk:
        res = apk.verify()
        output_dispatch = {
            True: lambda: _print_json(res),
            False: lambda: print(
                f"Valid Integrity: {res['is_valid']}\n"
                f"Corrupted File:  {res['corrupted_file'] or 'None'}\n"
                f"Signed:          {res['is_signed']} ({', '.join(res['signature_schemes']) or 'none'})\n"
                f"16KB Aligned:    {res['so_16k_compliant']} ({'Android 15 ready' if res['so_16k_compliant'] else 'needs zipalign'})\n"
                f"Fully Aligned:   {res['is_aligned']}"
            ),
        }
        output_dispatch[args.json]()
        return 0 if res["is_valid"] else 1


def cmd_extract(args: argparse.Namespace) -> int:
    with APK(args.apk_path) as apk:
        apk.extract(args.output)
        print(f"Successfully extracted {len(apk.files)} files to: {args.output}")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    pack(
        args.source_dir,
        args.output,
        sign=getattr(args, "sign", True),
        auto_axml=getattr(args, "auto_axml", True),
        auto_dex=getattr(args, "auto_dex", True),
        auto_resources=getattr(args, "auto_resources", True),
        compile_py=getattr(args, "compile_py", True),
    )
    print(f"Successfully packaged APK: {args.output}")
    return 0


def cmd_sign(args: argparse.Namespace) -> int:
    from pureapk.signature import APKSigner
    APKSigner.sign_apk_file(args.apk_path, output_path=args.output, key_alias=args.alias)
    out_target = args.output or args.apk_path
    print(f"Successfully signed APK (v1+v2 schemes): {out_target}")
    return 0


def cmd_compile_manifest(args: argparse.Namespace) -> int:
    from pureapk.manifest import AxmlEncoder
    raw_xml = Path(args.input_manifest).read_bytes()
    binary_axml = AxmlEncoder.encode(raw_xml)
    Path(args.output).write_bytes(binary_axml)
    print(f"Successfully compiled manifest to binary AXML ({len(binary_axml)} bytes): {args.output}")
    return 0


def cmd_install_deps(args: argparse.Namespace) -> int:
    target_dir = Path(args.project_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    uv_bin = shutil.which("uv")
    cmd = [uv_bin, "pip", "install", "--target", str(target_dir)] if uv_bin else [sys.executable, "-m", "pip", "install", "--target", str(target_dir)]

    if args.requirements:
        cmd.extend(["-r", str(args.requirements)])
    if args.packages:
        cmd.extend(args.packages)

    if not args.requirements and not args.packages:
        print("Error: No packages or requirements.txt specified.")
        return 1

    print(f"Installing dependencies into: {target_dir}...")
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print(f"Successfully installed dependencies into: {target_dir}")
    return res.returncode


def cmd_zipalign(args: argparse.Namespace) -> int:
    from pureapk.builder import zipalign
    if getattr(args, "check", False):
        with APK(args.input_apk) as apk:
            res = apk.check_alignment(so_alignment=args.so_align, file_alignment=args.align)
            output_dispatch = {
                True: lambda: _print_json(res),
                False: lambda: _format_zipalign_check_human(res),
            }
            output_dispatch[args.json]()
            return 0 if res["is_aligned"] else 1

    if not args.output:
        print("Error: -o / --output is required when aligning an APK (use -c / --check to verify only).")
        return 1

    zipalign(args.input_apk, args.output, alignment=args.align, so_alignment=args.so_align, sign=getattr(args, "sign", False))
    print(f"Successfully aligned APK (16KB page alignment): {args.output}")
    return 0


def _format_zipalign_check_human(res: Dict[str, Any]) -> None:
    status = "PASSED (16KB Android 15 ready)" if res["so_16k_compliant"] else "FAILED (unaligned .so files)"
    print(f"Alignment Verification:  {status}")
    print(f"Total .so Libraries:     {res['total_so_files']}")
    print(f"Aligned .so Libraries:   {res['aligned_so_files']}")
    print(f"Fully Aligned (4B/16KB):  {res['is_aligned']}")
    if res["unaligned_files"]:
        print("Unaligned files:")
        for u in res["unaligned_files"]:
            print(f"  - {u['filename']}: offset {u['data_offset']} (rem {u['remainder']} for align {u['target_alignment']})")


def cmd_unpack_wheel(args: argparse.Namespace) -> int:
    from pureapk.wheels import AndroidWheelHelper
    res = AndroidWheelHelper.unpack_wheel(args.wheel_path, args.target_dir, abi=args.abi)
    output_dispatch = {
        True: lambda: _print_json(res),
        False: lambda: (
            print(f"Successfully unpacked {res['wheel_name']} (ABI: {res['target_abi']}) into: {res['target_dir']}"),
            print(f"  + Extracted {len(res['extracted_so_files'])} native .so libraries to lib/{res['target_abi']}/"),
            print(f"  + Extracted {res['extracted_py_files_count']} Python module / resource files"),
        ),
    }
    output_dispatch[args.json]()
    return 0


def cmd_init_ci(args: argparse.Namespace) -> int:
    from pureapk.ci import CIHelper
    target_dir = getattr(args, "project_dir", ".") or "."
    res = CIHelper.generate_cython_workflow(target_dir, generate_scaffold=not getattr(args, "no_scaffold", False))
    output_dispatch = {
        True: lambda: _print_json(res),
        False: lambda: (
            print(f"Successfully generated GitHub Actions CI workflow for Cython & Android NDK:"),
            [print(f"  + {path}") for path in res["created_files"]],
            print("\nCloud CI Features:"),
            print("  - Automated ARM64 / ARMv7 / x86_64 matrix builds in Ubuntu cloud runners"),
            print("  - 16KB ELF page alignment (-Wl,-z,max-page-size=16384) for Android 15 compatibility"),
            print("  - Automated artifact upload for direct packaging with pureapk"),
        ),
    }
    output_dispatch[args.json]()
    return 0


def cmd_init_kivy(args: argparse.Namespace) -> int:
    from pureapk.frameworks import KivyAppHelper
    KivyAppHelper.init_project(args.target_dir, title=args.title)
    print(f"Successfully initialized Kivy project in: {args.target_dir}")
    return 0


def cmd_init_pygame(args: argparse.Namespace) -> int:
    from pureapk.frameworks import PygameAppHelper
    PygameAppHelper.init_project(args.target_dir, title=args.title)
    print(f"Successfully initialized Pygame project in: {args.target_dir}")
    return 0


def cmd_pack_kivy(args: argparse.Namespace) -> int:
    from pureapk.frameworks import KivyAppHelper
    KivyAppHelper.pack_app(args.source_dir, args.output, app_title=args.title, release=getattr(args, "release", False), channel=getattr(args, "channel", None))
    print(f"Successfully packaged Kivy APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_pack_pygame(args: argparse.Namespace) -> int:
    from pureapk.frameworks import PygameAppHelper
    PygameAppHelper.pack_app(args.source_dir, args.output, app_title=args.title, release=getattr(args, "release", False), channel=getattr(args, "channel", None))
    print(f"Successfully packaged Pygame APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_init_flet(args: argparse.Namespace) -> int:
    from pureapk.frameworks import FletAppHelper
    FletAppHelper.init_project(args.target_dir, title=args.title)
    print(f"Successfully initialized Flet project in: {args.target_dir}")
    return 0


def cmd_pack_flet(args: argparse.Namespace) -> int:
    from pureapk.frameworks import FletAppHelper
    FletAppHelper.pack_app(args.source_dir, args.output, app_title=args.title, release=getattr(args, "release", False), channel=getattr(args, "channel", None))
    print(f"Successfully packaged Flet APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_init_toga(args: argparse.Namespace) -> int:
    from pureapk.frameworks import TogaAppHelper
    TogaAppHelper.init_project(args.target_dir, title=args.title)
    print(f"Successfully initialized BeeWare Toga project in: {args.target_dir}")
    return 0


def cmd_pack_toga(args: argparse.Namespace) -> int:
    from pureapk.frameworks import TogaAppHelper
    TogaAppHelper.pack_app(args.source_dir, args.output, app_title=args.title, release=getattr(args, "release", False), channel=getattr(args, "channel", None))
    print(f"Successfully packaged BeeWare Toga APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_init_renpy(args: argparse.Namespace) -> int:
    from pureapk.frameworks import RenPyAppHelper
    RenPyAppHelper.init_project(args.target_dir, title=args.title)
    print(f"Successfully initialized Ren'Py project in: {args.target_dir}")
    return 0


def cmd_pack_renpy(args: argparse.Namespace) -> int:
    from pureapk.frameworks import RenPyAppHelper
    RenPyAppHelper.pack_app(args.source_dir, args.output, app_title=args.title, release=getattr(args, "release", False), channel=getattr(args, "channel", None))
    print(f"Successfully packaged Ren'Py APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_init_webview(args: argparse.Namespace) -> int:
    from pureapk.frameworks import WebViewAppHelper
    WebViewAppHelper.init_project(args.target_dir, title=args.title)
    print(f"Successfully initialized WebView project in: {args.target_dir}")
    return 0


def cmd_pack_webview(args: argparse.Namespace) -> int:
    from pureapk.frameworks import WebViewAppHelper
    WebViewAppHelper.pack_app(args.source_dir, args.output, app_title=args.title, release=getattr(args, "release", False), channel=getattr(args, "channel", None))
    print(f"Successfully packaged WebView APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_init_pyside(args: argparse.Namespace) -> int:
    from pureapk.frameworks import PySideAppHelper
    PySideAppHelper.init_project(args.target_dir, title=args.title)
    print(f"Successfully initialized PySide/Qt project in: {args.target_dir}")
    return 0


def cmd_pack_pyside(args: argparse.Namespace) -> int:
    from pureapk.frameworks import PySideAppHelper
    rel_mode = "release" if getattr(args, "release", False) else "debug"
    PySideAppHelper.pack_app(args.source_dir, args.output, app_title=args.title, release=getattr(args, "release", False), channel=getattr(args, "channel", None))
    print(f"Successfully packaged PySide/Qt APK ({rel_mode}): {args.output}")
    return 0


def cmd_pack_aab(args: argparse.Namespace) -> int:
    from pureapk.stores import AABBuilder
    builder = AABBuilder(args.output)
    builder.add_base_directory(args.source_dir)
    builder.build()
    print(f"Successfully packaged Google Play Android App Bundle (AAB): {args.output}")
    return 0


def cmd_init_ios(args: argparse.Namespace) -> int:
    from pureapk.stores import AppleAppHelper
    AppleAppHelper.init_project(args.target_dir, app_name=args.title, bundle_id=args.bundle_id)
    print(f"Successfully initialized Apple iOS project in: {args.target_dir}")
    return 0


def cmd_pack_ipa(args: argparse.Namespace) -> int:
    from pureapk.stores import IPABuilder
    builder = IPABuilder(args.output, app_name=args.title)
    builder.add_directory(args.source_dir)
    builder.build()
    print(f"Successfully packaged Apple App Store IPA: {args.output}")
    return 0


def cmd_init_windows(args: argparse.Namespace) -> int:
    from pureapk.stores import WindowsStoreHelper
    WindowsStoreHelper.init_project(args.target_dir, display_name=args.title, package_name=args.package)
    print(f"Successfully initialized Microsoft Store Windows project in: {args.target_dir}")
    return 0


def cmd_pack_msix(args: argparse.Namespace) -> int:
    from pureapk.stores import MSIXBuilder
    builder = MSIXBuilder(args.output)
    builder.add_directory(args.source_dir)
    builder.build()
    print(f"Successfully packaged Microsoft Store MSIX: {args.output}")
    return 0


def cmd_generate_keystore(args: argparse.Namespace) -> int:
    from pureapk.stores import ReleaseHelper
    meta = ReleaseHelper.generate_release_keystore(
        args.output,
        key_alias=args.alias,
        store_pass=args.password,
    )
    output_dispatch = {
        True: lambda: _print_json(meta),
        False: lambda: print(
            f"Release Keystore Created: {args.output}\n"
            f"Key Alias:                {meta['key_alias']}\n"
            f"SHA256 Fingerprint:       {meta['sha256_fingerprint']}\n"
            f"SHA1 Fingerprint:         {meta['sha1_fingerprint']}\n"
            f"Validity:                 {meta['validity_days']} days"
        ),
    }
    output_dispatch[args.json]()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pureapk",
        description="High-performance pure Python APK inspection, alignment, and packaging toolkit.",
    )
    parser.add_argument("-V", "--version", action="version", version="pureapk 0.1.2")

    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # info
    p_info = subparsers.add_parser("info", help="Display APK metadata summary")
    p_info.add_argument("apk_path", help="Path to APK file")
    p_info.add_argument("--json", action="store_true", help="Format output as JSON")

    # manifest
    p_manifest = subparsers.add_parser("manifest", help="Dump decoded AndroidManifest")
    p_manifest.add_argument("apk_path", help="Path to APK file")
    p_manifest.add_argument("--json", action="store_true", help="Dump manifest as JSON")

    # permissions
    p_perms = subparsers.add_parser("permissions", help="List app permissions")
    p_perms.add_argument("apk_path", help="Path to APK file")
    p_perms.add_argument("--json", action="store_true", help="Format output as JSON")

    # dex
    p_dex = subparsers.add_parser("dex", help="Display DEX headers and Dalvik stats")
    p_dex.add_argument("apk_path", help="Path to APK file")
    p_dex.add_argument("--json", action="store_true", help="Format output as JSON")

    # files
    p_files = subparsers.add_parser("files", help="List archive files")
    p_files.add_argument("apk_path", help="Path to APK file")
    p_files.add_argument("--json", action="store_true", help="Format output as JSON")

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify APK integrity, signatures, and page alignment")
    p_verify.add_argument("apk_path", help="Path to APK file")
    p_verify.add_argument("--json", action="store_true", help="Format output as JSON")

    # extract
    p_extract = subparsers.add_parser("extract", help="Extract APK contents")
    p_extract.add_argument("apk_path", help="Path to APK file")
    p_extract.add_argument("-o", "--output", required=True, help="Destination directory")

    # pack
    p_pack = subparsers.add_parser("pack", help="Build APK from directory")
    p_pack.add_argument("source_dir", help="Source folder to package")
    p_pack.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack.add_argument("--sign", action="store_true", default=True, help="Sign APK with debug keys")
    p_pack.add_argument("--no-sign", action="store_false", dest="sign", help="Skip signing")
    p_pack.add_argument("--no-axml", action="store_false", dest="auto_axml", help="Keep text manifest")
    p_pack.add_argument("--no-dex", action="store_false", dest="auto_dex", help="Skip DEX injection")

    # sign
    p_sign = subparsers.add_parser("sign", help="Digitally sign an APK with v1 and v2 schemes")
    p_sign.add_argument("apk_path", help="Path to APK to sign")
    p_sign.add_argument("-o", "--output", help="Output signed APK path (defaults to in-place)")
    p_sign.add_argument("--alias", default="androiddebugkey", help="Key alias")

    # zipalign
    p_zipalign = subparsers.add_parser("zipalign", help="Align APK entries to 4-byte and 16KB boundaries for Android 15")
    p_zipalign.add_argument("input_apk", help="Input APK file")
    p_zipalign.add_argument("-o", "--output", help="Output aligned APK file")
    p_zipalign.add_argument("-c", "--check", action="store_true", help="Verify alignment without modifying the archive")
    p_zipalign.add_argument("--so-align", type=int, default=16384, help="Byte boundary for uncompressed .so libraries (default: 16384)")
    p_zipalign.add_argument("--align", type=int, default=4, help="Byte boundary for other uncompressed files (default: 4)")
    p_zipalign.add_argument("--sign", action="store_true", help="Digitally sign APK after alignment")
    p_zipalign.add_argument("--json", action="store_true", help="Output results as JSON")

    # compile-manifest
    p_cman = subparsers.add_parser("compile-manifest", help="Compile text AndroidManifest.xml into binary AXML")
    p_cman.add_argument("input_manifest", help="Input XML file")
    p_cman.add_argument("-o", "--output", required=True, help="Output binary AXML file")

    # install-deps
    p_inst = subparsers.add_parser("install-deps", aliases=["add-deps"], help="Install pure Python dependencies directly into a project folder")
    p_inst.add_argument("project_dir", help="Project folder to install dependencies into")
    p_inst.add_argument("packages", nargs="*", help="Package names to install (e.g. requests urllib3)")
    p_inst.add_argument("-r", "--requirements", help="Path to requirements.txt file")

    # unpack-wheel / install-wheel
    p_wheel = subparsers.add_parser("unpack-wheel", aliases=["install-wheel"], help="Unpack an Android wheel (.whl) into lib/<abi>/ and project folders")
    p_wheel.add_argument("wheel_path", help="Path to .whl package")
    p_wheel.add_argument("target_dir", help="Project folder to unpack into")
    p_wheel.add_argument("--abi", help="Target ABI override (e.g. arm64-v8a, armeabi-v7a, x86_64)")
    p_wheel.add_argument("--json", action="store_true", help="Output results as JSON")

    # init-ci
    p_ci = subparsers.add_parser("init-ci", help="Generate GitHub Actions CI workflow for cloud Cython/NDK compilation")
    p_ci.add_argument("project_dir", nargs="?", default=".", help="Target project root directory (default: current directory)")
    p_ci.add_argument("--cython", action="store_true", default=True, help="Enable Cython build configuration")
    p_ci.add_argument("--no-scaffold", action="store_true", help="Skip generating sample setup.py and fast_core.pyx")
    p_ci.add_argument("--json", action="store_true", help="Output results as JSON")

    # init-kivy
    p_kivy = subparsers.add_parser("init-kivy", help="Scaffold a Kivy Android project")
    p_kivy.add_argument("target_dir", help="Target project folder")
    p_kivy.add_argument("--title", default="Kivy App", help="App title")

    # init-pygame
    p_pygame = subparsers.add_parser("init-pygame", help="Scaffold a Pygame Android project")
    p_pygame.add_argument("target_dir", help="Target project folder")
    p_pygame.add_argument("--title", default="Pygame App", help="App title")

    # pack-kivy
    p_pack_kivy = subparsers.add_parser("pack-kivy", help="Pack a Kivy project directory into an APK")
    p_pack_kivy.add_argument("source_dir", help="Kivy project folder")
    p_pack_kivy.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_kivy.add_argument("--title", default="Kivy App", help="App title")
    p_pack_kivy.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_kivy.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")

    # pack-pygame
    p_pack_pygame = subparsers.add_parser("pack-pygame", help="Pack a Pygame project directory into an APK")
    p_pack_pygame.add_argument("source_dir", help="Pygame project folder")
    p_pack_pygame.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_pygame.add_argument("--title", default="Pygame App", help="App title")
    p_pack_pygame.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_pygame.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")

    # init-flet
    p_init_flet = subparsers.add_parser("init-flet", help="Scaffold a Flet (Flutter/Python) mobile project")
    p_init_flet.add_argument("target_dir", help="Target project folder")
    p_init_flet.add_argument("--title", default="Flet App", help="App title")

    # pack-flet
    p_pack_flet = subparsers.add_parser("pack-flet", help="Pack a Flet project directory into an APK")
    p_pack_flet.add_argument("source_dir", help="Flet project folder")
    p_pack_flet.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_flet.add_argument("--title", default="Flet App", help="App title")
    p_pack_flet.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_flet.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")

    # init-toga
    p_init_toga = subparsers.add_parser("init-toga", help="Scaffold a BeeWare Toga (native UI) mobile project")
    p_init_toga.add_argument("target_dir", help="Target project folder")
    p_init_toga.add_argument("--title", default="Toga App", help="App title")

    # pack-toga
    p_pack_toga = subparsers.add_parser("pack-toga", help="Pack a BeeWare Toga project directory into an APK")
    p_pack_toga.add_argument("source_dir", help="BeeWare Toga project folder")
    p_pack_toga.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_toga.add_argument("--title", default="Toga App", help="App title")
    p_pack_toga.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_toga.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")

    # init-renpy
    p_init_renpy = subparsers.add_parser("init-renpy", help="Scaffold a Ren'Py visual novel project")
    p_init_renpy.add_argument("target_dir", help="Target project folder")
    p_init_renpy.add_argument("--title", default="Visual Novel", help="App title")

    # pack-renpy
    p_pack_renpy = subparsers.add_parser("pack-renpy", help="Pack a Ren'Py visual novel project into an APK")
    p_pack_renpy.add_argument("source_dir", help="Ren'Py project folder")
    p_pack_renpy.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_renpy.add_argument("--title", default="Visual Novel", help="App title")
    p_pack_renpy.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_renpy.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")

    # init-webview
    p_init_web = subparsers.add_parser("init-webview", help="Scaffold a lightweight HTML5/CSS WebView project")
    p_init_web.add_argument("target_dir", help="Target project folder")
    p_init_web.add_argument("--title", default="WebView App", help="App title")

    # pack-webview
    p_pack_web = subparsers.add_parser("pack-webview", help="Pack a WebView project directory into an APK")
    p_pack_web.add_argument("source_dir", help="WebView project folder")
    p_pack_web.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_web.add_argument("--title", default="WebView App", help="App title")
    p_pack_web.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_web.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")

    # init-pyside / init-pyqt
    p_init_pyside = subparsers.add_parser("init-pyside", aliases=["init-pyqt"], help="Scaffold a PySide6 / PyQt6 Qt for Android project")
    p_init_pyside.add_argument("target_dir", help="Target project folder")
    p_init_pyside.add_argument("--title", default="PySide App", help="App display title")

    # pack-pyside / pack-pyqt
    p_pack_pyside = subparsers.add_parser("pack-pyside", aliases=["pack-pyqt"], help="Pack a PySide6 / PyQt6 Qt project into an APK")
    p_pack_pyside.add_argument("source_dir", help="PySide / PyQt project folder")
    p_pack_pyside.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_pyside.add_argument("--title", default="PySide App", help="App title")
    p_pack_pyside.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_pyside.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")

    # pack-aab (Google Play Console)
    p_pack_aab = subparsers.add_parser("pack-aab", help="Build Google Play Android App Bundle (.aab)")
    p_pack_aab.add_argument("source_dir", help="Source folder containing project / base assets")
    p_pack_aab.add_argument("-o", "--output", required=True, help="Output .aab bundle filename")

    # init-ios (Apple App Store)
    p_init_ios = subparsers.add_parser("init-ios", help="Scaffold an Apple iOS project with Info.plist")
    p_init_ios.add_argument("target_dir", help="Target iOS project folder")
    p_init_ios.add_argument("--title", default="MyIOSApp", help="App display name")
    p_init_ios.add_argument("--bundle-id", default="com.example.app", help="Apple CFBundleIdentifier")

    # pack-ipa (Apple App Store)
    p_pack_ipa = subparsers.add_parser("pack-ipa", help="Pack an Apple App Store IPA package")
    p_pack_ipa.add_argument("source_dir", help="Source directory containing Info.plist and app files")
    p_pack_ipa.add_argument("-o", "--output", required=True, help="Output .ipa filename")
    p_pack_ipa.add_argument("--title", default="PayloadApp", help="App executable / bundle title")

    # init-windows (Microsoft Store)
    p_init_win = subparsers.add_parser("init-windows", help="Scaffold a Microsoft Store Windows project")
    p_init_win.add_argument("target_dir", help="Target Windows project folder")
    p_init_win.add_argument("--title", default="MyWinApp", help="App display name")
    p_init_win.add_argument("--package", default="MyCompany.MyWinApp", help="Package identity name")

    # pack-msix (Microsoft Store)
    p_pack_msix = subparsers.add_parser("pack-msix", help="Pack a Microsoft Store MSIX package with BlockMap")
    p_pack_msix.add_argument("source_dir", help="Source directory containing AppxManifest.xml and assets")
    p_pack_msix.add_argument("-o", "--output", required=True, help="Output .msix filename")

    # generate-keystore
    p_key = subparsers.add_parser("generate-keystore", help="Generate production release signing profile")
    p_key.add_argument("-o", "--output", required=True, help="Output keystore filename")
    p_key.add_argument("--alias", default="release", help="Key alias")
    p_key.add_argument("--password", default="android", help="Store password")
    p_key.add_argument("--json", action="store_true", help="Output metadata as JSON")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args_list = argv if argv is not None else sys.argv[1:]

    # Fallback to info command if first argument is a file ending in .apk
    known_commands = {
        "info", "manifest", "permissions", "dex", "files", "verify", "extract", "pack",
        "zipalign", "unpack-wheel", "install-wheel", "init-ci",
        "init-kivy", "init-pygame", "pack-kivy", "pack-pygame",
        "init-flet", "pack-flet", "init-toga", "pack-toga",
        "init-renpy", "pack-renpy", "init-webview", "pack-webview", "init-pyside", "init-pyqt", "pack-pyside", "pack-pyqt",
        "pack-aab", "init-ios", "pack-ipa", "init-windows", "pack-msix", "generate-keystore", "sign", "compile-manifest", "install-deps", "add-deps",
    }
    has_subcommand = bool(args_list and not args_list[0].startswith("-") and args_list[0] in known_commands)
    is_direct_apk = bool(args_list and not args_list[0].startswith("-") and args_list[0].lower().endswith(".apk"))

    effective_args = {
        True: lambda: ["info"] + list(args_list),
        False: lambda: list(args_list),
    }[is_direct_apk and not has_subcommand]()

    if not effective_args:
        parser.print_help()
        return 0

    parsed = parser.parse_args(effective_args)

    dispatch_table: Dict[str, Callable[[argparse.Namespace], int]] = {
        "info": cmd_info,
        "manifest": cmd_manifest,
        "permissions": cmd_permissions,
        "dex": cmd_dex,
        "files": cmd_files,
        "verify": cmd_verify,
        "extract": cmd_extract,
        "pack": cmd_pack,
        "sign": cmd_sign,
        "zipalign": cmd_zipalign,
        "compile-manifest": cmd_compile_manifest,
        "install-deps": cmd_install_deps,
        "add-deps": cmd_install_deps,
        "unpack-wheel": cmd_unpack_wheel,
        "install-wheel": cmd_unpack_wheel,
        "init-ci": cmd_init_ci,
        "init-kivy": cmd_init_kivy,
        "init-pygame": cmd_init_pygame,
        "pack-kivy": cmd_pack_kivy,
        "pack-pygame": cmd_pack_pygame,
        "init-flet": cmd_init_flet,
        "pack-flet": cmd_pack_flet,
        "init-toga": cmd_init_toga,
        "pack-toga": cmd_pack_toga,
        "init-renpy": cmd_init_renpy,
        "pack-renpy": cmd_pack_renpy,
        "init-webview": cmd_init_webview,
        "pack-webview": cmd_pack_webview,
        "init-pyside": cmd_init_pyside,
        "init-pyqt": cmd_init_pyside,
        "pack-pyside": cmd_pack_pyside,
        "pack-pyqt": cmd_pack_pyside,
        "pack-aab": cmd_pack_aab,
        "init-ios": cmd_init_ios,
        "pack-ipa": cmd_pack_ipa,
        "init-windows": cmd_init_windows,
        "pack-msix": cmd_pack_msix,
        "generate-keystore": cmd_generate_keystore,
    }

    handler = dispatch_table.get(parsed.command, lambda a: parser.print_help() or 0)  # type: ignore[func-returns-value]
    return handler(parsed)


if __name__ == "__main__":
    sys.exit(main())
