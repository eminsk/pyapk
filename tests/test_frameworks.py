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


def test_pack_kivy_and_pygame(tmp_path: Path) -> None:
    k_dir = tmp_path / "kivy_pack_src"
    p_dir = tmp_path / "pygame_pack_src"
    KivyAppHelper.init_project(k_dir, title="PackKivy")
    PygameAppHelper.init_project(p_dir, title="PackPygame")

    k_apk = tmp_path / "kivy_out.apk"
    p_apk = tmp_path / "pygame_out.apk"

    KivyAppHelper.pack_app(k_dir, k_apk, app_title="PackKivy")
    assert k_apk.exists()
    with APK(k_apk) as apk:
        assert "assets/private.tar" in apk.filenames
        assert "AndroidManifest.xml" in apk.filenames

    PygameAppHelper.pack_app(p_dir, p_apk, app_title="PackPygame")
    assert p_apk.exists()
    with APK(p_apk) as apk:
        assert "assets/private.tar" in apk.filenames
        assert "AndroidManifest.xml" in apk.filenames


def test_cli_pack_kivy_and_pygame(tmp_path: Path) -> None:
    k_dir = tmp_path / "cli_k_src"
    p_dir = tmp_path / "cli_p_src"
    KivyAppHelper.init_project(k_dir)
    PygameAppHelper.init_project(p_dir)

    k_apk = str(tmp_path / "cli_k.apk")
    p_apk = str(tmp_path / "cli_p.apk")

    code_k = main(["pack-kivy", str(k_dir), "-o", k_apk, "--title", "KivyCLI"])
    assert code_k == 0
    assert Path(k_apk).exists()

    code_p = main(["pack-pygame", str(p_dir), "-o", p_apk, "--title", "PygameCLI"])
    assert code_p == 0
    assert Path(p_apk).exists()


def test_flet_toga_renpy_webview_helpers(tmp_path: Path) -> None:
    from pureapk.frameworks import FletAppHelper, TogaAppHelper, RenPyAppHelper, WebViewAppHelper

    # Flet
    f_dir = tmp_path / "flet_proj"
    f_apk = tmp_path / "flet.apk"
    FletAppHelper.init_project(f_dir, title="MyFlet")
    assert (f_dir / "main.py").exists()
    FletAppHelper.pack_app(f_dir, f_apk, app_title="MyFlet", release=True)
    assert f_apk.exists()

    # Toga
    t_dir = tmp_path / "toga_proj"
    t_apk = tmp_path / "toga.apk"
    TogaAppHelper.init_project(t_dir, title="MyToga")
    assert (t_dir / "app.py").exists()
    TogaAppHelper.pack_app(t_dir, t_apk, app_title="MyToga", release=True)
    assert t_apk.exists()

    # Ren'Py
    r_dir = tmp_path / "renpy_proj"
    r_apk = tmp_path / "renpy.apk"
    RenPyAppHelper.init_project(r_dir, title="MyNovel")
    assert (r_dir / "game" / "script.rpy").exists()
    RenPyAppHelper.pack_app(r_dir, r_apk, app_title="MyNovel", release=True)
    assert r_apk.exists()

    # WebView
    w_dir = tmp_path / "web_proj"
    w_apk = tmp_path / "webview.apk"
    WebViewAppHelper.init_project(w_dir, title="MyWeb")
    assert (w_dir / "assets" / "index.html").exists()
    WebViewAppHelper.pack_app(w_dir, w_apk, app_title="MyWeb", release=True)
    assert w_apk.exists()

    # PySide / PyQt
    from pureapk.frameworks import PySideAppHelper, PyQtAppHelper
    py_dir = tmp_path / "pyside_proj"
    py_apk = tmp_path / "pyside.apk"
    PySideAppHelper.init_project(py_dir, title="MyPySide")
    assert (py_dir / "main.py").exists()
    PySideAppHelper.pack_app(py_dir, py_apk, app_title="MyPySide", release=True)
    assert py_apk.exists()

    with APK(py_apk) as apk:
        assert "org.qtproject.qt.android.bindings.QtActivity" in apk.manifest.activities
        assert apk.framework == "pyside"
        assert apk.signature.is_signed is True

def test_cli_pack_frameworks_with_custom_package(tmp_path: Path) -> None:
    k_dir = tmp_path / "custom_k_src"
    KivyAppHelper.init_project(k_dir)
    k_apk = str(tmp_path / "custom_k.apk")

    code_k = main(["pack-kivy", str(k_dir), "-o", k_apk, "--title", "CustomApp", "-p", "com.custom.weather"])
    assert code_k == 0
    with APK(k_apk) as apk:
        assert apk.package_name == "com.custom.weather"
        assert apk.manifest.package_name == "com.custom.weather"
