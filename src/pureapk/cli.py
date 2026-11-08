"""Professional CLI interface for inspecting, analyzing, and building Android APKs.

Provides rich subcommands with JSON output options and high-speed execution.
"""

from __future__ import annotations

import argparse
import json
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
                f"Signed:          {res['is_signed']} ({', '.join(res['signature_schemes']) or 'none'})"
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
    pack(args.source_dir, args.output)
    print(f"Successfully packaged APK: {args.output}")
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
    KivyAppHelper.pack_app(args.source_dir, args.output, app_title=args.title, release=getattr(args, "release", False))
    print(f"Successfully packaged Kivy APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
    return 0


def cmd_pack_pygame(args: argparse.Namespace) -> int:
    from pureapk.frameworks import PygameAppHelper
    PygameAppHelper.pack_app(args.source_dir, args.output, app_title=args.title, release=getattr(args, "release", False))
    print(f"Successfully packaged Pygame APK ({'release' if getattr(args, 'release', False) else 'debug'}): {args.output}")
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
        description="High-performance pure Python APK inspection and packaging toolkit.",
    )
    parser.add_argument("-V", "--version", action="version", version="pureapk 0.1.0")

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
    p_verify = subparsers.add_parser("verify", help="Verify APK integrity and signatures")
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

    # pack-pygame
    p_pack_pygame = subparsers.add_parser("pack-pygame", help="Pack a Pygame project directory into an APK")
    p_pack_pygame.add_argument("source_dir", help="Pygame project folder")
    p_pack_pygame.add_argument("-o", "--output", required=True, help="Output APK filename")
    p_pack_pygame.add_argument("--title", default="Pygame App", help="App title")
    p_pack_pygame.add_argument("--release", action="store_true", help="Build release-ready APK (strip debuggable flags)")

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
        "init-kivy", "init-pygame", "pack-kivy", "pack-pygame",
        "pack-aab", "init-ios", "pack-ipa", "init-windows", "pack-msix", "generate-keystore",
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
        "init-kivy": cmd_init_kivy,
        "init-pygame": cmd_init_pygame,
        "pack-kivy": cmd_pack_kivy,
        "pack-pygame": cmd_pack_pygame,
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
