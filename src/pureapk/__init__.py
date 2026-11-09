"""pureapk: High-performance, pure Python APK inspection and packaging toolkit.

100% standard library, zero C dependencies.
Full cross-platform support (Apple macOS, Linux, Windows),
compatible with CPython 3.8 - 3.16, Free-Threaded (No-GIL), and PyPy.
"""

from __future__ import annotations

from typing import Any
from pureapk.apk import APK, APKFileInfo
from pureapk.builder import APKBuilder, align_zip_entry, pack, zipalign
from pureapk.ci import CIHelper
from pureapk.dex import DexBuilder, DexHeader, MultiDexSummary
from pureapk.frameworks import (
    FletAppHelper,
    FrameworkDetector,
    KivyAppHelper,
    PygameAppHelper,
    PyQtAppHelper,
    PySideAppHelper,
    RenPyAppHelper,
    TogaAppHelper,
    WebViewAppHelper,
)
from pureapk.manifest import AndroidManifest, AxmlAttribute, AxmlElement, AxmlEncoder
from pureapk.signature import APKCertificate, APKSigner, APKSignature
from pureapk.stores import (
    AABBuilder,
    AppleAppHelper,
    IPABuilder,
    MSIXBuilder,
    ReleaseHelper,
    WindowsStoreHelper,
)
from pureapk.wheels import AndroidWheelHelper

__version__ = "1.0.2"
__author__ = "eminsk"
__all__ = [
    "APK",
    "APKFileInfo",
    "APKBuilder",
    "pack",
    "zipalign",
    "align_zip_entry",
    "AndroidWheelHelper",
    "CIHelper",
    "DexHeader",
    "MultiDexSummary",
    "DexBuilder",
    "AndroidManifest",
    "AxmlElement",
    "AxmlAttribute",
    "AxmlEncoder",
    "APKSignature",
    "APKCertificate",
    "APKSigner",
    "FrameworkDetector",
    "KivyAppHelper",
    "PygameAppHelper",
    "FletAppHelper",
    "TogaAppHelper",
    "RenPyAppHelper",
    "WebViewAppHelper",
    "PySideAppHelper",
    "PyQtAppHelper",
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
