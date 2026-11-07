"""Tests for Kivy and Pygame framework integration and detection."""

from __future__ import annotations

import io
from pathlib import Path
import zipfile
import pytest

from pureapk.apk import APK
from pureapk.cli import main
from pureapk.frameworks import FrameworkDetector, KivyAppHelper, PygameAppHelper
from tests.conftest import make_test_axml, make_test_dex


def test_framework_detector_kivy() -> None:
    files = ["lib/arm64-v8a/libkivy.so", "main.py", "app.kv"]
    activities = ["org.kivy.android.PythonActivity"]
    fw = FrameworkDetector.detect(files, activities)
    assert fw == "kivy"


def test_framework_detector_pygame() -> None:
    files = ["lib/arm64-v8a/libpygame.so", "main.py", "sound.ogg"]
    activities = ["org.renpy.android.PythonSDLActivity"]
    fw = FrameworkDetector.detect(files, activities)
    assert fw == "pygame"


def test_framework_detector_native() -> None:
    files = ["lib/arm64-v8a/libnative.so", "classes.dex"]
    activities = ["com.example.MainActivity"]
    fw = FrameworkDetector.detect(files, activities)
    assert fw == "native"


def test_kivy_apk_detection() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("AndroidManifest.xml", make_test_axml(activities=("org.kivy.android.PythonActivity",)))
        zf.writestr("classes.dex", make_test_dex())
        zf.writestr("lib/arm64-v8a/libkivy.so", b"\x7fELF_KIVY")
        zf.writestr("ui.kv", b"<RootWidget>:\n")

    with APK(buf.getvalue()) as apk:
        assert apk.framework == "kivy"
        assert apk.is_python_app is True
        info = apk.info()
        assert info["framework"] == "kivy"
        assert info["is_python_app"] is True


def test_pygame_apk_detection() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("AndroidManifest.xml", make_test_axml(activities=("org.renpy.android.PythonSDLActivity",)))
        zf.writestr("classes.dex", make_test_dex())
        zf.writestr("lib/arm64-v8a/libpygame.so", b"\x7fELF_PYGAME")

    with APK(buf.getvalue()) as apk:
        assert apk.framework == "pygame"
        assert apk.is_python_app is True


def test_kivy_scaffolding(tmp_path: Path) -> None:
    target = tmp_path / "kivy_project"
    KivyAppHelper.init_project(target, title="My Kivy Game")
    assert (target / "main.py").exists()
    assert (target / "buildozer.spec").exists()
    assert "kivy" in (target / "buildozer.spec").read_text(encoding="utf-8")

    manifest = KivyAppHelper.generate_manifest_xml("com.example.kivy", "My Kivy Game")
    assert "org.kivy.android.PythonActivity" in manifest
    assert "glEsVersion" in manifest


def test_pygame_scaffolding(tmp_path: Path) -> None:
    target = tmp_path / "pygame_project"
    PygameAppHelper.init_project(target, title="My Pygame Game")
    assert (target / "main.py").exists()
    assert (target / "buildozer.spec").exists()
    assert "pygame" in (target / "buildozer.spec").read_text(encoding="utf-8")

    manifest = PygameAppHelper.generate_manifest_xml("com.example.pygame", "My Pygame Game")
    assert "org.renpy.android.PythonSDLActivity" in manifest
    assert "glEsVersion" in manifest


def test_cli_init_kivy_and_pygame(tmp_path: Path) -> None:
    k_dir = str(tmp_path / "cli_kivy")
    p_dir = str(tmp_path / "cli_pygame")

    code_k = main(["init-kivy", k_dir, "--title", "CLI Kivy"])
    assert code_k == 0
    assert (tmp_path / "cli_kivy" / "buildozer.spec").exists()

    code_p = main(["init-pygame", p_dir, "--title", "CLI Pygame"])
    assert code_p == 0
    assert (tmp_path / "cli_pygame" / "buildozer.spec").exists()
