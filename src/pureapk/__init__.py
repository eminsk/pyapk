"""pureapk: High-performance, pure Python APK inspection and packaging toolkit.

100% standard library, zero C dependencies.
Full cross-platform support (Apple macOS, Linux, Windows),
compatible with CPython 3.8 - 3.16, Free-Threaded (No-GIL), and PyPy.
"""

from __future__ import annotations

from pureapk.apk import APK, APKFileInfo
from pureapk.builder import APKBuilder, pack
from pureapk.dex import DexHeader, MultiDexSummary
from pureapk.frameworks import FrameworkDetector, KivyAppHelper, PygameAppHelper
from pureapk.manifest import AndroidManifest, AxmlAttribute, AxmlElement
from pureapk.signature import APKCertificate, APKSignature
from pureapk.stores import (
    AABBuilder,
    AppleAppHelper,
    IPABuilder,
    MSIXBuilder,
    ReleaseHelper,
    WindowsStoreHelper,
)

__version__ = "0.1.0"
__author__ = "eminsk"
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
    "FrameworkDetector",
    "KivyAppHelper",
    "PygameAppHelper",
    "AABBuilder",
    "IPABuilder",
    "MSIXBuilder",
    "ReleaseHelper",
    "AppleAppHelper",
    "WindowsStoreHelper",
    "load",
    "inspect",
    "__version__",
]


def load(source: Any) -> APK:
    """Convenience factory to load an APK instance."""
    return APK(source)


def inspect(source: Any) -> dict:
    """Convenience helper to extract all APK metadata as a dict."""
    with APK(source) as apk:
        return apk.info()
