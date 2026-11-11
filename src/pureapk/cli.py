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
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


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
    target = str(args.apk_path)
    if target.lower().endswith(".ipa"):
        from pureapk.stores import AppleAppHelper
        res = AppleAppHelper.verify_ipa(target)
        if getattr(args, "json", False):
            _print_json(res)
        else:
            print(f"Apple iOS IPA Package: {res['ipa_name']}")
            print(f"  Valid Integrity: {res['valid']}")
            print(f"  App Name:        {res['app_name'] or 'N/A'}")
            print(f"  Bundle ID:       {res['bundle_id'] or 'N/A'}")
            print(f"  Version:         {res['version'] or 'N/A'}")
            print(f"  Minimum iOS:     {res['min_os_version'] or 'N/A'}")
            print(f"  PkgInfo Header:  {res['has_pkginfo']}")
            print(f"  CodeResources:   {res.get('has_code_resources', False)} (Apple Spec v2)")
            print(f"  Signature Valid: {res.get('signature_valid', False)}")
            if res.get("profile_info"):
                pinfo = res["profile_info"]
                print(f"  Profile Name:    {pinfo.get('name') or 'N/A'}")
                print(f"  Team:            {pinfo.get('team_identifier') or 'N/A'} ({pinfo.get('team_name') or 'N/A'})")
                print(f"  Expires:         {pinfo.get('expiration_date') or 'N/A'} (Expired: {pinfo.get('is_expired')})")
            print(f"  Sideload Ready:  {res['sideload_ready']} (AltStore / Sideloadly / Scarlet / TrollStore)")
            if res["issues"]:
                print(f"  Issues Detected: {'; '.join(res['issues'])}")
        return 0 if res["valid"] else 1

    with APK(args.apk_path) as apk:
        res = apk.verify()

        def _print_human() -> None:
            runnable_flag = res.get("runnable_on_device", False)
            runnable_desc = (
                "Full Native Python Runtime"
                if runnable_flag
                else "Skeleton — missing native Python runtime in lib/<abi>/"
                if res.get("is_skeleton")
                else "Not runnable"
            )
            print(
                f"Valid Integrity:  {res['is_valid']}\n"
                f"Corrupted File:   {res['corrupted_file'] or 'None'}\n"
                f"Signed:           {res['is_signed']} ({', '.join(res['signature_schemes']) or 'none'})\n"
                f"16KB Aligned:     {res['so_16k_compliant']} ({'Android 15 ready' if res['so_16k_compliant'] else 'needs zipalign'})\n"
                f"Fully Aligned:    {res['is_aligned']}\n"
                f"Structural Parse: {res.get('structural_parse_ready', False)} (Valid AXML, DEX & Resource Table)\n"
                f"Runnable App:     {runnable_flag} ({runnable_desc})\n"
                f"Runtime Mode:     {'Full Native' if res.get('has_native_runtime') else 'Skeleton (No lib/*.so runtime)' if res.get('is_skeleton') else 'Standard'}"
            )
            if res.get("is_skeleton"):
                print(
                    "  Warning: Skeleton APK has no native Python runtime in lib/<abi>/. "
                    "Pass '--runtime-apk <base.apk>', run 'pureapk prepare-runtime', or use 'pureapk unpack-wheel' to bundle Python."
                )

        output_dispatch = {
            True: lambda: _print_json(res),
            False: _print_human,
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
    keystore = getattr(args, "keystore", None)
    password = getattr(args, "password", "")
    APKSigner.sign_apk_file(
        args.apk_path,
        output_path=args.output,
        key_alias=args.alias,
        keystore_path=keystore,
        keystore_password=password,
    )
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


def cmd_pack_wheel(args: argparse.Namespace) -> int:
    import sys
    from pureapk.wheels import AndroidWheelHelper
    fw = getattr(args, "framework", None)
    if fw:
        res = AndroidWheelHelper.build_framework_wheel(
            framework=fw,
            output_whl=args.output,
            distribution_name=args.name,
            version=args.version,
            python_tag=getattr(args, "python_tag", "py3"),
            abi=getattr(args, "abi", None),
            title=getattr(args, "title", None),
        )
    else:
        if not args.source_dir:
            print("Error: source_dir is required when --framework is not specified", file=sys.stderr)
            return 1
        res = AndroidWheelHelper.build_wheel(
            args.source_dir,
            output_whl=args.output,
            distribution_name=args.name,
            version=args.version,
            python_tag=getattr(args, "python_tag", "py3"),
            abi=getattr(args, "abi", None),
            summary=getattr(args, "summary", "Mobile Python package"),
        )
    if getattr(args, "json", False):
        _print_json(res)
    else:
        print(f"Successfully packaged wheel: {res['wheel_path']}")
        print(f"  + Distribution: {res['distribution_name']} v{res['version']}")
        print(f"  + Wheel Tag: {res['python_tag']}-{res['abi_tag']}-{res['platform_tag']}")
        print(f"  + Total Files: {res['total_files']} ({res['size_bytes']} bytes)")
    return 0


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


def cmd_prepare_runtime(args: argparse.Namespace) -> int:
    from pureapk.frameworks import KivyAppHelper
    res = KivyAppHelper.prepare_runtime(args.from_apk, args.target_dir)
    if getattr(args, "json", False):
        _print_json(res)
    else:
        print(f"Successfully prepared Python/Kivy runtime in: {res['target_dir']}")
        print(f"  + ABIs:          {', '.join(res['abis']) or 'none'}")
        print(f"  + Native .so:    {res['extracted_so_count']} libraries")
        print(f"  + DEX classes:   {', '.join(res['dex_files']) or 'none'}")
        print(f"  + Target Python: {res.get('python_version') or 'unknown'}")
    return 0


def cmd_pack_kivy(args: argparse.Namespace) -> int:
    from pureapk.frameworks import KivyAppHelper
    KivyAppHelper.pack_app(
        args.source_dir,
        args.output,
        package_name=getattr(args, "package", None),
        app_title=args.title,
        release=getattr(args, "release", False),
        channel=getattr(args, "channel", None),
        keystore=getattr(args, "keystore", None),
        password=getattr(args, "password", ""),
        alias=getattr(args, "alias", None),
        runtime_apk=getattr(args, "runtime_apk", None),
        skeleton=getattr(args, "skeleton", False),
    )
    print(f"Successfully packaged Kivy APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_pack_pygame(args: argparse.Namespace) -> int:
    from pureapk.frameworks import PygameAppHelper
    PygameAppHelper.pack_app(
        args.source_dir,
        args.output,
        package_name=getattr(args, "package", None),
        app_title=args.title,
        release=getattr(args, "release", False),
        channel=getattr(args, "channel", None),
        keystore=getattr(args, "keystore", None),
        password=getattr(args, "password", ""),
        alias=getattr(args, "alias", None),
        runtime_apk=getattr(args, "runtime_apk", None),
        skeleton=getattr(args, "skeleton", False),
    )
    print(f"Successfully packaged Pygame APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_init_flet(args: argparse.Namespace) -> int:
    from pureapk.frameworks import FletAppHelper
    FletAppHelper.init_project(args.target_dir, title=args.title)
    print(f"Successfully initialized Flet project in: {args.target_dir}")
    return 0


def cmd_pack_flet(args: argparse.Namespace) -> int:
    from pureapk.frameworks import FletAppHelper
    FletAppHelper.pack_app(
        args.source_dir,
        args.output,
        package_name=getattr(args, "package", None),
        app_title=args.title,
        release=getattr(args, "release", False),
        channel=getattr(args, "channel", None),
        keystore=getattr(args, "keystore", None),
        password=getattr(args, "password", ""),
        alias=getattr(args, "alias", None),
    )
    print(f"Successfully packaged Flet APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_init_toga(args: argparse.Namespace) -> int:
    from pureapk.frameworks import TogaAppHelper
    TogaAppHelper.init_project(args.target_dir, title=args.title)
    print(f"Successfully initialized BeeWare Toga project in: {args.target_dir}")
    return 0


def cmd_pack_toga(args: argparse.Namespace) -> int:
    from pureapk.frameworks import TogaAppHelper
    TogaAppHelper.pack_app(
        args.source_dir,
        args.output,
        package_name=getattr(args, "package", None),
        app_title=args.title,
        release=getattr(args, "release", False),
        channel=getattr(args, "channel", None),
        keystore=getattr(args, "keystore", None),
        password=getattr(args, "password", ""),
        alias=getattr(args, "alias", None),
    )
    print(f"Successfully packaged BeeWare Toga APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_init_renpy(args: argparse.Namespace) -> int:
    from pureapk.frameworks import RenPyAppHelper
    RenPyAppHelper.init_project(args.target_dir, title=args.title)
    print(f"Successfully initialized Ren'Py project in: {args.target_dir}")
    return 0


def cmd_pack_renpy(args: argparse.Namespace) -> int:
    from pureapk.frameworks import RenPyAppHelper
    RenPyAppHelper.pack_app(
        args.source_dir,
        args.output,
        package_name=getattr(args, "package", None),
        app_title=args.title,
        release=getattr(args, "release", False),
        channel=getattr(args, "channel", None),
        keystore=getattr(args, "keystore", None),
        password=getattr(args, "password", ""),
        alias=getattr(args, "alias", None),
    )
    print(f"Successfully packaged Ren'Py APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_init_webview(args: argparse.Namespace) -> int:
    from pureapk.frameworks import WebViewAppHelper
    WebViewAppHelper.init_project(args.target_dir, title=args.title)
    print(f"Successfully initialized WebView project in: {args.target_dir}")
    return 0


def cmd_pack_webview(args: argparse.Namespace) -> int:
    from pureapk.frameworks import WebViewAppHelper
    WebViewAppHelper.pack_app(
        args.source_dir,
        args.output,
        package_name=getattr(args, "package", None),
        app_title=args.title,
        release=getattr(args, "release", False),
        channel=getattr(args, "channel", None),
        keystore=getattr(args, "keystore", None),
        password=getattr(args, "password", ""),
        alias=getattr(args, "alias", None),
    )
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
    PySideAppHelper.pack_app(
        args.source_dir,
        args.output,
        package_name=getattr(args, "package", None),
        app_title=args.title,
        release=getattr(args, "release", False),
        channel=getattr(args, "channel", None),
        keystore=getattr(args, "keystore", None),
        password=getattr(args, "password", ""),
        alias=getattr(args, "alias", None),
    )
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
    if getattr(args, "bundle_id", None):
        builder.set_bundle_id(args.bundle_id)
    if getattr(args, "profile", None):
        builder.set_provisioning_profile(args.profile)
    builder.add_directory(args.source_dir)
    builder.build(sign=getattr(args, "sign", True))
    print(f"Successfully packaged Apple App Store IPA: {args.output}")
    return 0


def cmd_sign_ipa(args: argparse.Namespace) -> int:
    from pureapk.signature import IPASigner
    report = IPASigner.sign_ipa(
        args.ipa_path,
        output_ipa=getattr(args, "output", None),
        p12_path=getattr(args, "p12", None),
        p12_password=getattr(args, "password", ""),
        mobileprovision_path=getattr(args, "profile", None),
        bundle_id=getattr(args, "bundle_id", None),
        app_name=getattr(args, "title", None),
    )
    if getattr(args, "json", False):
        _print_json(report)
    else:
        print(f"Successfully signed Apple iOS IPA: {report['ipa_path']}")
        print(f"  App Name:       {report['app_name']}")
        print(f"  Bundle ID:      {report['bundle_id']}")
        print(f"  Version:        {report['version']}")
        print(f"  Files Signed:   {report['files_signed']}")
        print(f"  Signature Spec: {report['signer']} (_CodeSignature/CodeResources)")
        if report.get("profile_info"):
            prof = report["profile_info"]
            print(f"  Profile Name:   {prof.get('name') or 'N/A'}")
            print(f"  Team ID:        {prof.get('team_identifier') or 'N/A'} ({prof.get('team_name') or 'N/A'})")
            print(f"  Expiration:     {prof.get('expiration_date') or 'N/A'} (Expired: {prof.get('is_expired')})")
    return 0


def cmd_ipa_profile(args: argparse.Namespace) -> int:
    from pureapk.stores import AppleAppHelper
    target = Path(args.profile_path)
    if not target.exists():
        print(f"Error: file not found: {args.profile_path}", file=sys.stderr)
        return 1

    profile_bytes: bytes
    if target.suffix.lower() == ".ipa":
        import zipfile
        with zipfile.ZipFile(target, "r") as zf:
            provs = [n for n in zf.namelist() if n.endswith("embedded.mobileprovision")]
            if not provs:
                print(f"Error: no embedded.mobileprovision found in {args.profile_path}", file=sys.stderr)
                return 1
            profile_bytes = zf.read(provs[0])
    else:
        profile_bytes = target.read_bytes()

    info = AppleAppHelper.parse_provisioning_profile(profile_bytes)
    if getattr(args, "json", False):
        info_copy = dict(info)
        info_copy.pop("raw_plist", None)
        _print_json(info_copy)
    else:
        if not info["valid"]:
            print(f"Error parsing profile: {info.get('error')}", file=sys.stderr)
            return 1
        print(f"Apple Provisioning Profile: {info.get('name')}")
        print(f"  Profile Type:     {info.get('profile_type')}")
        print(f"  App Identifier:   {info.get('app_id')}")
        print(f"  Team ID:          {info.get('team_identifier')}")
        print(f"  Team Name:        {info.get('team_name')}")
        print(f"  Created:          {info.get('creation_date')}")
        print(f"  Expires:          {info.get('expiration_date')} (Expired: {info.get('is_expired')})")
        print(f"  Devices Count:    {info.get('provisioned_devices_count')}")
        print(f"  Certs Count:      {info.get('certificates_count')}")
    return 0


def cmd_ipa_check(args: argparse.Namespace) -> int:
    from pureapk.stores import AppleAppHelper
    res = AppleAppHelper.verify_developer_credentials(
        p12_path=getattr(args, "p12", None),
        p12_password=getattr(args, "password", ""),
        profile_path=getattr(args, "profile", None),
        ipa_path=getattr(args, "ipa", None),
        target_bundle_id=getattr(args, "bundle_id", None),
        target_udid=getattr(args, "udid", None),
        check_ocsp=getattr(args, "ocsp", False),
    )
    if getattr(args, "json", False):
        _print_json(res)
    else:
        print("=" * 80)
        print("[APPLE] DEVELOPER CREDENTIALS & SIGNING COMPATIBILITY REPORT")
        print("=" * 80)
        status_icon = "[OK]" if res["ready"] else "[ERROR]"
        print(f"OVERALL STATUS: {status_icon} {res['status']}\n")

        if res.get("p12"):
            p12 = res["p12"]
            print("[CERTIFICATE] (.p12):")
            print(f"  Common Name:       {p12.get('common_name') or 'N/A'}")
            print(f"  Certificate Type:  {p12.get('cert_type') or 'N/A'}")
            print(f"  Team ID:           {p12.get('team_id') or 'N/A'}")
            print(f"  Team Name:         {p12.get('team_name') or 'N/A'}")
            print(f"  Serial Number:     {p12.get('serial') or 'N/A'}")
            print(f"  SHA-1 Fingerprint: {p12.get('sha1_fingerprint') or 'N/A'}")
            print(f"  Valid Period:      {p12.get('not_before')} -> {p12.get('not_after')}")
            print(f"  OCSP Status:       {res.get('ocsp_status')}\n")

        if res.get("profile"):
            prof = res["profile"]
            print("[PROVISIONING PROFILE] (.mobileprovision):")
            print(f"  Profile Name:      {prof.get('name') or 'N/A'}")
            print(f"  Profile Type:      {prof.get('profile_type') or 'N/A'}")
            print(f"  App Identifier:    {prof.get('app_id') or 'N/A'}")
            print(f"  Team:              {prof.get('team_identifier')} ({prof.get('team_name')})")
            print(f"  Expires:           {prof.get('expiration_date')} (Expired: {prof.get('is_expired')})")
            print(f"  Devices Count:     {prof.get('provisioned_devices_count')}")
            print(f"  Certs Registered:  {prof.get('certificates_count')}\n")

        print("[VERIFICATION CHECKLIST]")
        for chk in res["checks"]:
            mark = "  [+] PASS:" if chk["passed"] else "  [-] FAIL:"
            print(f"{mark:<11} {chk['name']:<32} {chk['detail']}")
        print("=" * 80)
        if res["issues"]:
            print("[!] ISSUES DETECTED:")
            for iss in res["issues"]:
                print(f"  - {iss}")
            print("=" * 80)

    return 0 if res["ready"] else 1


def cmd_ipa_ota(args: argparse.Namespace) -> int:
    from pureapk.stores import AppleAppHelper
    ipa_path = Path(args.ipa_path)
    bundle_id = args.bundle_id
    title = args.title
    version = args.version or "1.0.0"

    if ipa_path.is_file():
        rep = AppleAppHelper.verify_ipa(ipa_path)
        if not bundle_id and rep.get("bundle_id"):
            bundle_id = rep["bundle_id"]
        if not title and rep.get("app_name"):
            title = rep["app_name"]
        if (not args.version or args.version == "1.0.0") and rep.get("version"):
            version = rep["version"]

    bundle_id = bundle_id or "com.example.app"
    title = title or (ipa_path.stem if ipa_path.name else "iOS App")
    ipa_url = args.url or f"https://example.com/{ipa_path.name}"

    manifest_xml = AppleAppHelper.generate_ota_manifest(
        ipa_url=ipa_url,
        bundle_id=bundle_id,
        app_title=title,
        version=version,
        icon_url=args.icon_url,
    )

    out_manifest = Path(args.output) if args.output else (ipa_path.parent / "manifest.plist" if ipa_path.is_file() else Path("manifest.plist"))
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(manifest_xml, encoding="utf-8")

    out_html = None
    if args.html:
        manifest_url = args.manifest_url or f"https://example.com/{out_manifest.name}"
        html_content = AppleAppHelper.generate_ota_html(
            manifest_url=manifest_url,
            app_title=title,
            bundle_id=bundle_id,
            version=version,
            icon_url=args.icon_url,
        )
        out_html = out_manifest.parent / "index.html"
        out_html.write_text(html_content, encoding="utf-8")

    res = {
        "success": True,
        "manifest_path": str(out_manifest),
        "html_path": str(out_html) if out_html else None,
        "bundle_id": bundle_id,
        "title": title,
        "version": version,
        "ipa_url": ipa_url,
    }

    if args.json:
        _print_json(res)
    else:
        print("[APPLE OTA] Wireless Distribution Package Created:")
        print(f"  Manifest:  {out_manifest}")
        if out_html:
            print(f"  Web Page:  {out_html}")
        print(f"  Bundle ID: {bundle_id}")
        print(f"  Title:     {title} v{version}")
        print(f"  IPA URL:   {ipa_url}")
        print("  Install:   itms-services://?action=download-manifest&url=<MANIFEST_URL>")
    return 0


def cmd_ipa_csr(args: argparse.Namespace) -> int:
    from pureapk.stores import AppleAppHelper
    res = AppleAppHelper.generate_csr(
        output_csr_path=args.output,
        output_key_path=args.key,
        email=args.email,
        name=args.name,
        country=args.country,
    )
    if args.json:
        _print_json(res)
    else:
        if res.get("success"):
            print("[APPLE CSR] Certificate Signing Request generated:")
            print(f"  CSR File:    {res['csr_path']} (Upload to developer.apple.com)")
            print(f"  Private Key: {res['key_path']} (KEEP PRIVATE!)")
            print(f"  Subject:     {res['common_name']} <{res['email']}>")
        else:
            print(f"[ERROR] CSR generation failed: {res.get('error')}")
    return 0 if res.get("success") else 1


def cmd_ipa_import_cert(args: argparse.Namespace) -> int:
    from pureapk.stores import AppleAppHelper
    res = AppleAppHelper.import_apple_cer(
        cer_path=args.cer,
        key_path=args.key,
        output_p12_path=args.output,
        password=args.password or "",
    )
    if args.json:
        _print_json(res)
    else:
        if res.get("success"):
            print("[APPLE CERT] Official Apple Developer .p12 Keystore Created:")
            print(f"  P12 Output: {res['p12_path']}")
            print(f"  File Size:  {res['file_size']} bytes")
        else:
            print(f"[ERROR] Import failed: {res.get('error')}")
    return 0 if res.get("success") else 1


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
    parser.add_argument("-V", "--version", action="version", version="pureapk 1.0.1")

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
    p_verify = subparsers.add_parser("verify", aliases=["verify-ipa"], help="Verify APK or Apple iOS IPA integrity, signatures, and alignment")
    p_verify.add_argument("apk_path", help="Path to APK or Apple iOS IPA file")
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
    p_sign.add_argument("--keystore", help="Path to release keystore or signing profile")
    p_sign.add_argument("--password", default="", help="Keystore password")

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

    # pack-wheel
    p_pack_wheel = subparsers.add_parser("pack-wheel", help="Build a PEP 427 wheel (.whl) for Android or pure Python from a directory or framework")
    p_pack_wheel.add_argument("source_dir", nargs="?", default=None, help="Project source folder to pack (optional if --framework is provided)")
    p_pack_wheel.add_argument("--framework", choices=["kivy", "pygame", "flet", "toga", "renpy", "webview", "pyside", "pyqt"], help="Framework engine template to pack into wheel")
    p_pack_wheel.add_argument("--title", help="App title for framework wheel")
    p_pack_wheel.add_argument("-o", "--output", help="Output .whl file path or destination directory")
    p_pack_wheel.add_argument("-n", "--name", required=True, help="Distribution name (e.g. my-app)")
    p_pack_wheel.add_argument("-v", "--version", default="0.1.0", help="Distribution version (default: 0.1.0)")
    p_pack_wheel.add_argument("--python-tag", default="py3", help="Python version tag (e.g. py3, cp38, cp39, cp310, cp311, cp312, cp313, cp314, cp315, cp316)")
    p_pack_wheel.add_argument("--abi", help="Target ABI (e.g. arm64-v8a, armeabi-v7a, x86_64, x86, any)")
    p_pack_wheel.add_argument("--summary", default="Mobile Python package", help="Package summary description")
    p_pack_wheel.add_argument("--json", action="store_true", help="Output results as JSON")

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

    # prepare-runtime
    p_prep_rt = subparsers.add_parser("prepare-runtime", help="Extract native Python/Kivy runtime (lib/*.so, classes*.dex, resources.arsc) from a base APK or folder into a project")
    p_prep_rt.add_argument("target_dir", help="Target project folder to populate with runtime files")
    p_prep_rt.add_argument("--from-apk", required=True, help="Path to base runtime APK (e.g. WeatherTest.apk) or extracted runtime directory")
    p_prep_rt.add_argument("--json", action="store_true", help="Output results as JSON")

    # pack-kivy
    p_pack_kivy = subparsers.add_parser("pack-kivy", help="Pack a Kivy project directory into an APK")
    p_pack_kivy.add_argument("source_dir", help="Kivy project folder")
    p_pack_kivy.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_kivy.add_argument("-p", "--package", help="Android package name (e.g. com.example.app)")
    p_pack_kivy.add_argument("--title", default="Kivy App", help="App title")
    p_pack_kivy.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_kivy.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")
    p_pack_kivy.add_argument("--keystore", help="Path to release keystore or signing profile")
    p_pack_kivy.add_argument("--password", default="", help="Keystore password")
    p_pack_kivy.add_argument("--alias", help="Key alias in keystore")
    p_pack_kivy.add_argument("--runtime-apk", help="Path to base p4a/Kivy runtime APK or directory to bundle lib/*.so and classes*.dex")
    p_pack_kivy.add_argument("--skeleton", action="store_true", help="Build lightweight skeleton APK without bundling native Python/Kivy runtime")

    # pack-pygame
    p_pack_pygame = subparsers.add_parser("pack-pygame", help="Pack a Pygame project directory into an APK")
    p_pack_pygame.add_argument("source_dir", help="Pygame project folder")
    p_pack_pygame.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_pygame.add_argument("-p", "--package", help="Android package name (e.g. com.example.app)")
    p_pack_pygame.add_argument("--title", default="Pygame App", help="App title")
    p_pack_pygame.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_pygame.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")
    p_pack_pygame.add_argument("--keystore", help="Path to release keystore or signing profile")
    p_pack_pygame.add_argument("--password", default="", help="Keystore password")
    p_pack_pygame.add_argument("--alias", help="Key alias in keystore")
    p_pack_pygame.add_argument("--runtime-apk", help="Path to base p4a/Pygame runtime APK or directory to bundle lib/*.so and classes*.dex")
    p_pack_pygame.add_argument("--skeleton", action="store_true", help="Build lightweight skeleton APK without bundling native Python/Pygame runtime")

    # init-flet
    p_init_flet = subparsers.add_parser("init-flet", help="Scaffold a Flet (Flutter/Python) mobile project")
    p_init_flet.add_argument("target_dir", help="Target project folder")
    p_init_flet.add_argument("--title", default="Flet App", help="App title")

    # pack-flet
    p_pack_flet = subparsers.add_parser("pack-flet", help="Pack a Flet project directory into an APK")
    p_pack_flet.add_argument("source_dir", help="Flet project folder")
    p_pack_flet.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_flet.add_argument("-p", "--package", help="Android package name (e.g. com.example.app)")
    p_pack_flet.add_argument("--title", default="Flet App", help="App title")
    p_pack_flet.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_flet.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")
    p_pack_flet.add_argument("--keystore", help="Path to release keystore or signing profile")
    p_pack_flet.add_argument("--password", default="", help="Keystore password")
    p_pack_flet.add_argument("--alias", help="Key alias in keystore")

    # init-toga
    p_init_toga = subparsers.add_parser("init-toga", help="Scaffold a BeeWare Toga (native UI) mobile project")
    p_init_toga.add_argument("target_dir", help="Target project folder")
    p_init_toga.add_argument("--title", default="Toga App", help="App title")

    # pack-toga
    p_pack_toga = subparsers.add_parser("pack-toga", help="Pack a BeeWare Toga project directory into an APK")
    p_pack_toga.add_argument("source_dir", help="BeeWare Toga project folder")
    p_pack_toga.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_toga.add_argument("-p", "--package", help="Android package name (e.g. com.example.app)")
    p_pack_toga.add_argument("--title", default="Toga App", help="App title")
    p_pack_toga.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_toga.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")
    p_pack_toga.add_argument("--keystore", help="Path to release keystore or signing profile")
    p_pack_toga.add_argument("--password", default="", help="Keystore password")
    p_pack_toga.add_argument("--alias", help="Key alias in keystore")

    # init-renpy
    p_init_renpy = subparsers.add_parser("init-renpy", help="Scaffold a Ren'Py visual novel project")
    p_init_renpy.add_argument("target_dir", help="Target project folder")
    p_init_renpy.add_argument("--title", default="Visual Novel", help="App title")

    # pack-renpy
    p_pack_renpy = subparsers.add_parser("pack-renpy", help="Pack a Ren'Py visual novel project into an APK")
    p_pack_renpy.add_argument("source_dir", help="Ren'Py project folder")
    p_pack_renpy.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_renpy.add_argument("-p", "--package", help="Android package name (e.g. com.example.app)")
    p_pack_renpy.add_argument("--title", default="Visual Novel", help="App title")
    p_pack_renpy.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_renpy.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")
    p_pack_renpy.add_argument("--keystore", help="Path to release keystore or signing profile")
    p_pack_renpy.add_argument("--password", default="", help="Keystore password")
    p_pack_renpy.add_argument("--alias", help="Key alias in keystore")

    # init-webview
    p_init_web = subparsers.add_parser("init-webview", help="Scaffold a lightweight HTML5/CSS WebView project")
    p_init_web.add_argument("target_dir", help="Target project folder")
    p_init_web.add_argument("--title", default="WebView App", help="App title")

    # pack-webview
    p_pack_web = subparsers.add_parser("pack-webview", help="Pack a WebView project directory into an APK")
    p_pack_web.add_argument("source_dir", help="WebView project folder")
    p_pack_web.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_web.add_argument("-p", "--package", help="Android package name (e.g. com.example.app)")
    p_pack_web.add_argument("--title", default="WebView App", help="App title")
    p_pack_web.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_web.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")
    p_pack_web.add_argument("--keystore", help="Path to release keystore or signing profile")
    p_pack_web.add_argument("--password", default="", help="Keystore password")
    p_pack_web.add_argument("--alias", help="Key alias in keystore")

    # init-pyside / init-pyqt
    p_init_pyside = subparsers.add_parser("init-pyside", aliases=["init-pyqt"], help="Scaffold a PySide6 / PyQt6 Qt for Android project")
    p_init_pyside.add_argument("target_dir", help="Target project folder")
    p_init_pyside.add_argument("--title", default="PySide App", help="App display title")

    # pack-pyside / pack-pyqt
    p_pack_pyside = subparsers.add_parser("pack-pyside", aliases=["pack-pyqt"], help="Pack a PySide6 / PyQt6 Qt project into an APK")
    p_pack_pyside.add_argument("source_dir", help="PySide / PyQt project folder")
    p_pack_pyside.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_pyside.add_argument("-p", "--package", help="Android package name (e.g. com.example.app)")
    p_pack_pyside.add_argument("--title", default="PySide App", help="App title")
    p_pack_pyside.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")
    p_pack_pyside.add_argument("--channel", help="Distribution store channel tag (e.g. huawei, xiaomi, oppo, vivo, tencent, rustore)")
    p_pack_pyside.add_argument("--keystore", help="Path to release keystore or signing profile")
    p_pack_pyside.add_argument("--password", default="", help="Keystore password")
    p_pack_pyside.add_argument("--alias", help="Key alias in keystore")

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
    p_pack_ipa.add_argument("--bundle-id", help="Apple CFBundleIdentifier")
    p_pack_ipa.add_argument("--profile", help="Path to .mobileprovision file")
    p_pack_ipa.add_argument("--no-sign", action="store_false", dest="sign", help="Skip CodeResources generation")

    # sign-ipa / ipa-sign (Apple iOS IPA signing & sideloading)
    p_sign_ipa = subparsers.add_parser("sign-ipa", aliases=["ipa-sign"], help="Sign or re-sign an Apple iOS IPA with CodeResources and mobileprovision")
    p_sign_ipa.add_argument("ipa_path", help="Path to input .ipa package")
    p_sign_ipa.add_argument("-o", "--output", help="Output signed .ipa filename (defaults to in-place)")
    p_sign_ipa.add_argument("--profile", help="Path to .mobileprovision file")
    p_sign_ipa.add_argument("--p12", help="Path to .p12 certificate file")
    p_sign_ipa.add_argument("--password", default="", help="Password for .p12 certificate")
    p_sign_ipa.add_argument("--bundle-id", help="Override CFBundleIdentifier")
    p_sign_ipa.add_argument("--title", help="Override CFBundleDisplayName")
    p_sign_ipa.add_argument("--json", action="store_true", help="Output results as JSON")

    # ipa-profile / profile-ipa
    p_prof = subparsers.add_parser("ipa-profile", aliases=["profile-ipa"], help="Inspect Apple embedded.mobileprovision profile")
    p_prof.add_argument("profile_path", help="Path to .mobileprovision file or .ipa package")
    p_prof.add_argument("--json", action="store_true", help="Output results as JSON")

    # ipa-check / check-ipa / check-cert (Apple Developer Portal Style Validator)
    p_check = subparsers.add_parser("ipa-check", aliases=["check-ipa", "check-cert", "verify-cert"], help="Validate Apple certificates, profile compatibility, and sideload eligibility")
    p_check.add_argument("--p12", help="Path to .p12 developer certificate")
    p_check.add_argument("--password", default="", help="Password for .p12 certificate")
    p_check.add_argument("--profile", help="Path to .mobileprovision profile")
    p_check.add_argument("--ipa", help="Path to .ipa package")
    p_check.add_argument("--bundle-id", help="Target App CFBundleIdentifier")
    p_check.add_argument("--udid", help="Target iPhone/iPad UDID to check registration")
    p_check.add_argument("--ocsp", action="store_true", help="Check Apple OCSP online revocation status")
    p_check.add_argument("--json", action="store_true", help="Output results as JSON")

    # ipa-ota (Apple Over-The-Air manifest.plist & wireless web installer)
    p_ota = subparsers.add_parser("ipa-ota", aliases=["ota-ipa", "ota-manifest"], help="Generate Apple OTA manifest.plist and wireless web install page")
    p_ota.add_argument("ipa_path", help="Path to .ipa file")
    p_ota.add_argument("-o", "--output", help="Output manifest.plist path (default: alongside IPA)")
    p_ota.add_argument("--url", help="HTTPS download URL for the .ipa package")
    p_ota.add_argument("--title", help="Override App Title")
    p_ota.add_argument("--bundle-id", help="Override App CFBundleIdentifier")
    p_ota.add_argument("--version", help="Override App Version")
    p_ota.add_argument("--icon-url", help="HTTPS URL to app icon (512x512 PNG)")
    p_ota.add_argument("--html", action="store_true", help="Also generate wireless index.html install page")
    p_ota.add_argument("--manifest-url", help="HTTPS URL to manifest.plist for index.html")
    p_ota.add_argument("--json", action="store_true", help="Output results as JSON")

    # ipa-csr (Apple Certificate Signing Request)
    p_csr = subparsers.add_parser("ipa-csr", help="Generate .certSigningRequest (CSR) and private key for Apple Developer Portal")
    p_csr.add_argument("-o", "--output", required=True, help="Output .certSigningRequest file path")
    p_csr.add_argument("--key", help="Output private key path (default: same stem as CSR with .key)")
    p_csr.add_argument("--email", default="developer@example.com", help="Developer Apple ID email")
    p_csr.add_argument("--name", default="Apple Developer", help="Common name / Developer name")
    p_csr.add_argument("--country", default="US", help="Two-letter ISO country code (e.g. US, BY, RU)")
    p_csr.add_argument("--json", action="store_true", help="Output results as JSON")

    # ipa-import-cert (Import Apple .cer + private key -> .p12)
    p_imp = subparsers.add_parser("ipa-import-cert", aliases=["import-apple-cer"], help="Combine official Apple-issued .cer certificate with private key into .p12")
    p_imp.add_argument("--cer", required=True, help="Path to Apple-issued .cer certificate")
    p_imp.add_argument("--key", required=True, help="Path to private key matching the CSR")
    p_imp.add_argument("-o", "--output", required=True, help="Output .p12 keystore file path")
    p_imp.add_argument("--password", default="", help="Password to protect exported .p12 keystore")
    p_imp.add_argument("--json", action="store_true", help="Output results as JSON")

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
        "info", "manifest", "permissions", "dex", "files", "verify", "verify-ipa", "extract", "pack",
        "zipalign", "pack-wheel", "unpack-wheel", "install-wheel", "init-ci",
        "init-kivy", "init-pygame", "pack-kivy", "pack-pygame", "prepare-runtime",
        "init-flet", "pack-flet", "init-toga", "pack-toga",
        "init-renpy", "pack-renpy", "init-webview", "pack-webview", "init-pyside", "init-pyqt", "pack-pyside", "pack-pyqt",
        "pack-aab", "init-ios", "pack-ipa", "sign-ipa", "ipa-sign", "ipa-profile", "profile-ipa",
        "ipa-check", "check-ipa", "check-cert", "verify-cert", "init-windows", "pack-msix", "generate-keystore", "sign", "compile-manifest", "install-deps", "add-deps",
        "ipa-ota", "ota-ipa", "ota-manifest", "ipa-csr", "ipa-import-cert", "import-apple-cer",
    }
    has_subcommand = bool(args_list and not args_list[0].startswith("-") and args_list[0] in known_commands)
    is_direct_apk = bool(args_list and not args_list[0].startswith("-") and args_list[0].lower().endswith((".apk", ".ipa")))

    def _resolve_direct():
        if args_list[0].lower().endswith(".ipa"):
            return ["verify"] + list(args_list)
        return ["info"] + list(args_list)

    effective_args = {
        True: _resolve_direct,
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
        "verify-ipa": cmd_verify,
        "extract": cmd_extract,
        "pack": cmd_pack,
        "sign": cmd_sign,
        "zipalign": cmd_zipalign,
        "compile-manifest": cmd_compile_manifest,
        "install-deps": cmd_install_deps,
        "add-deps": cmd_install_deps,
        "pack-wheel": cmd_pack_wheel,
        "unpack-wheel": cmd_unpack_wheel,
        "install-wheel": cmd_unpack_wheel,
        "init-ci": cmd_init_ci,
        "init-kivy": cmd_init_kivy,
        "init-pygame": cmd_init_pygame,
        "prepare-runtime": cmd_prepare_runtime,
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
        "sign-ipa": cmd_sign_ipa,
        "ipa-sign": cmd_sign_ipa,
        "ipa-profile": cmd_ipa_profile,
        "profile-ipa": cmd_ipa_profile,
        "ipa-check": cmd_ipa_check,
        "check-ipa": cmd_ipa_check,
        "check-cert": cmd_ipa_check,
        "verify-cert": cmd_ipa_check,
        "ipa-ota": cmd_ipa_ota,
        "ota-ipa": cmd_ipa_ota,
        "ota-manifest": cmd_ipa_ota,
        "ipa-csr": cmd_ipa_csr,
        "ipa-import-cert": cmd_ipa_import_cert,
        "import-apple-cer": cmd_ipa_import_cert,
        "init-windows": cmd_init_windows,
        "pack-msix": cmd_pack_msix,
        "generate-keystore": cmd_generate_keystore,
    }

    handler = dispatch_table.get(parsed.command, lambda a: parser.print_help() or 0)  # type: ignore[func-returns-value]
    return handler(parsed)


if __name__ == "__main__":
    sys.exit(main())
