"""pyapk backward compatibility alias to pureapk."""

from __future__ import annotations

import pureapk
from pureapk import (
    APK,
    APKBuilder,
    APKCertificate,
    APKFileInfo,
    APKSignature,
    AndroidManifest,
    AxmlAttribute,
    AxmlElement,
    DexHeader,
    MultiDexSummary,
    __version__,
    inspect,
    load,
    pack,
)

__all__ = [
    "APK",
    "APKFileInfo",
    "APKBuilder",
    "pack",
    "DexHeader",
    "MultiDexSummary",
    "AndroidManifest",
    "AxmlElement",
    "AxmlAttribute",
    "APKSignature",
    "APKCertificate",
    "load",
    "inspect",
    "__version__",
]


def main() -> None:
    from pureapk.cli import main as cli_main
    cli_main()
