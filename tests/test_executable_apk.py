"""Tests for end-to-end self-contained executable APK packaging."""

from __future__ import annotations

import io
from pathlib import Path
import tarfile
import pytest
from pureapk.apk import APK
from pureapk.dex import DexHeader
from pureapk.frameworks import KivyAppHelper, PygameAppHelper, WebViewAppHelper
from pureapk.manifest import AndroidManifest


def test_kivy_pack_app_produces_fully_runnable_apk(tmp_path: Path) -> None:
    project_dir = tmp_path / "kivy_game"
    KivyAppHelper.init_project(project_dir, title="My Awesome Kivy App")

    output_apk = tmp_path / "runnable_kivy.apk"
    KivyAppHelper.pack_app(project_dir, output_apk, package_name="org.mykivy.game", app_title="My Awesome Kivy App")

    assert output_apk.exists()

    with APK(output_apk) as apk:
        # 1. Contains bundled assets/private.tar and private.mp3 (p4a standard)
        assert "assets/private.tar" in apk.filenames
        assert "assets/private.mp3" in apk.filenames
        assert "main.py" not in apk.filenames
        assert "main.pyc" not in apk.filenames
        assert "buildozer.spec" not in apk.filenames

        # Verify tar content has python code and compiled bytecode
        tar_bytes = apk.read("assets/private.tar")
        with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tf:
            names = tf.getnames()
            assert any("main.py" in n for n in names)
            assert any("main.pyc" in n for n in names)

        # 2. Contains valid bootstrap DEX
        assert "classes.dex" in apk.filenames
        dex_bytes = apk.read("classes.dex")
        header = DexHeader.from_bytes(dex_bytes)
        assert header.is_valid is True

        # 3. Contains resources table
        assert "resources.arsc" in apk.filenames

        # 4. Manifest is valid binary AXML
        assert "AndroidManifest.xml" in apk.filenames
        manifest = AndroidManifest(apk.read("AndroidManifest.xml"))
        assert manifest.package_name == "org.mykivy.game"
        assert "org.kivy.android.PythonActivity" in manifest.activities

        # 5. APK is digitally signed with both v1 and v2 schemes
        sig = apk.signature
        assert sig.is_signed is True
        assert sig.has_v1 is True
        assert sig.has_v2 is True
        assert len(sig.certificates) >= 1


def test_kivy_pack_app_with_native_lib(tmp_path: Path) -> None:
    """Tests packaging when project includes compiled native architecture libraries in lib/."""
    project_dir = tmp_path / "kivy_native"
    KivyAppHelper.init_project(project_dir, title="Native Kivy App")
    lib_dir = project_dir / "lib" / "arm64-v8a"
    lib_dir.mkdir(parents=True)
    fake_so = lib_dir / "libpython3.so"
    fake_so.write_bytes(b"\x7fELF" + b"\x00" * 100)

    output_apk = tmp_path / "native_kivy.apk"
    KivyAppHelper.pack_app(project_dir, output_apk)

    with APK(output_apk) as apk:
        assert "lib/arm64-v8a/libpython3.so" in apk.filenames
        assert "assets/private.tar" in apk.filenames
        assert "classes.dex" in apk.filenames
        assert "AndroidManifest.xml" in apk.filenames
        assert "main.py" not in apk.filenames


def test_pygame_pack_app_produces_fully_runnable_apk(tmp_path: Path) -> None:
    project_dir = tmp_path / "pygame_game"
    PygameAppHelper.init_project(project_dir, title="My Pygame App")

    output_apk = tmp_path / "runnable_pygame.apk"
    PygameAppHelper.pack_app(project_dir, output_apk, package_name="org.mypygame.game", app_title="My Pygame App")

    assert output_apk.exists()

    with APK(output_apk) as apk:
        assert "assets/private.tar" in apk.filenames
        assert "assets/private.mp3" in apk.filenames
        assert "classes.dex" in apk.filenames
        assert "AndroidManifest.xml" in apk.filenames
        assert "main.py" not in apk.filenames

        sig = apk.signature
        assert sig.is_signed is True
        assert sig.has_v1 is True
        assert sig.has_v2 is True


def test_webview_pack_app_produces_fully_runnable_apk(tmp_path: Path) -> None:
    project_dir = tmp_path / "web_app"
    WebViewAppHelper.init_project(project_dir, title="Web Mobile App")

    output_apk = tmp_path / "runnable_web.apk"
    WebViewAppHelper.pack_app(project_dir, output_apk, package_name="org.myweb.app", app_title="Web Mobile App")

    assert output_apk.exists()

    with APK(output_apk) as apk:
        assert "assets/index.html" in apk.filenames
        assert "classes.dex" in apk.filenames
        assert "AndroidManifest.xml" in apk.filenames

        sig = apk.signature
        assert sig.is_signed is True
        assert sig.has_v1 is True
        assert sig.has_v2 is True
