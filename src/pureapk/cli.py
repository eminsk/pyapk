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

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args_list = argv if argv is not None else sys.argv[1:]

    # Fallback to info command if first argument is a file ending in .apk
    has_subcommand = bool(args_list and not args_list[0].startswith("-") and args_list[0] in [
        "info", "manifest", "permissions", "dex", "files", "verify", "extract", "pack"
    ])
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
    }

    handler = dispatch_table.get(parsed.command, lambda a: parser.print_help() or 0)  # type: ignore[func-returns-value]
    return handler(parsed)


if __name__ == "__main__":
    sys.exit(main())
