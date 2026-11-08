"""Tests for cross-platform compatibility, free-threading (No-GIL), and memory efficiency."""

from __future__ import annotations

import concurrent.futures
import threading
from typing import List
import pytest

from pureapk.apk import APK, APKFileInfo
from pureapk.dex import DexBuilder, DexHeader, MultiDexSummary
from pureapk.frameworks import (
    FletAppHelper,
    FrameworkDetector,
    KivyAppHelper,
    PygameAppHelper,
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


def test_classes_have_slots_and_no_dict() -> None:
    """Verifies that core classes strictly use __slots__ for minimal memory."""
    classes = [
        APK,
        APKFileInfo,
        DexHeader,
        MultiDexSummary,
        DexBuilder,
        AndroidManifest,
        AxmlAttribute,
        AxmlElement,
        AxmlEncoder,
        APKCertificate,
        APKSignature,
        APKSigner,
        FrameworkDetector,
        KivyAppHelper,
        PygameAppHelper,
        FletAppHelper,
        TogaAppHelper,
        RenPyAppHelper,
        WebViewAppHelper,
        AABBuilder,
        IPABuilder,
        MSIXBuilder,
        ReleaseHelper,
        AppleAppHelper,
        WindowsStoreHelper,
    ]
    for cls in classes:
        assert hasattr(cls, "__slots__"), f"{cls.__name__} must define __slots__"
        assert "__dict__" not in cls.__slots__, f"{cls.__name__} should not include __dict__ in slots"


def test_free_threading_concurrency(sample_apk_bytes: bytes) -> None:
    """Simulates Free-Threaded (No-GIL) multi-threaded concurrent access."""
    apk = APK(sample_apk_bytes)
    num_threads = 20
    iterations_per_thread = 50

    def worker(worker_id: int) -> List[str]:
        results = []
        for _ in range(iterations_per_thread):
            pkg = apk.package_name
            vc = apk.version_code
            perms = apk.permissions
            dex_classes = apk.dex.total_classes
            sig = apk.signature.is_signed
            archs = apk.native_architectures
            files = apk.filenames
            results.append(f"{pkg}:{vc}:{len(perms)}:{dex_classes}:{sig}:{len(archs)}:{len(files)}")
        return results

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, i) for i in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            assert len(res) == iterations_per_thread
            assert res[0] == "com.example.testapp:101:2:15:True:2:9"

    apk.close()
