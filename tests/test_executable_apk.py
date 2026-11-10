"""Tests for end-to-end self-contained executable APK packaging, DEX validity, and device install parity."""

from __future__ import annotations

import io
from pathlib import Path
import tarfile
import pytest
from pureapk.apk import APK
from pureapk.cli import main as cli_main
from pureapk.dex import DexBuilder, DexHeader
from pureapk.frameworks import KivyAppHelper, PygameAppHelper, WebViewAppHelper
from pureapk.manifest import AndroidManifest
from pureapk.resources import ArscBuilder
from pureapk.stores import ReleaseHelper


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

        # 2. Contains valid bootstrap DEX with real launcher activity
        assert "classes.dex" in apk.filenames
        dex_bytes = apk.read("classes.dex")
        header = DexHeader.from_bytes(dex_bytes)
        assert header.is_valid is True
        dex_classes = DexBuilder.extract_class_names(dex_bytes)
        assert "org.kivy.android.PythonActivity" in dex_classes

        # 3. Contains valid binary resources table (not a 12-byte stub)
        assert "resources.arsc" in apk.filenames
        arsc_bytes = apk.read("resources.arsc")
        assert ArscBuilder.is_valid_arsc(arsc_bytes) is True
        assert len(arsc_bytes) >= 300

        # 4. Manifest is valid binary AXML and omits missing @mipmap/ic_launcher
        assert "AndroidManifest.xml" in apk.filenames
        manifest = AndroidManifest(apk.read("AndroidManifest.xml"))
        assert manifest.package_name == "org.mykivy.game"
        assert "org.kivy.android.PythonActivity" in manifest.activities
        assert manifest.application_icon == ""  # Safely omitted when no icon in res/

        # 5. Verification checks pass for real Android device install
        status = apk.verify()
        assert status["is_valid"] is True
        assert status["device_installable"] is True
        assert status["has_valid_arsc"] is True
        assert status["launcher_activity_present"] is True
        assert status["is_skeleton"] is True  # 0 .so files, so marked as skeleton
        assert status["has_native_runtime"] is False

        # 6. APK is digitally signed with both v1 and v2 schemes
        sig = apk.signature
        assert sig.is_signed is True
        assert sig.has_v1 is True
        assert sig.has_v2 is True
        assert len(sig.certificates) >= 1


def test_kivy_pack_app_with_icon_in_res(tmp_path: Path) -> None:
    """Tests that @mipmap/ic_launcher is included in AndroidManifest when icon exists."""
    project_dir = tmp_path / "kivy_icon_app"
    KivyAppHelper.init_project(project_dir, title="Icon App")

    # Add icon to res/mipmap-hdpi/
    icon_dir = project_dir / "res" / "mipmap-hdpi"
    icon_dir.mkdir(parents=True)
    (icon_dir / "ic_launcher.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    output_apk = tmp_path / "icon_app.apk"
    KivyAppHelper.pack_app(project_dir, output_apk, package_name="com.test.iconapp")

    with APK(output_apk) as apk:
        manifest = AndroidManifest(apk.read("AndroidManifest.xml"))
        assert manifest.application_icon == "@mipmap/ic_launcher"
        assert "res/mipmap-hdpi/ic_launcher.png" in apk.filenames


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

        status = apk.verify()
        assert status["device_installable"] is True
        assert status["has_native_runtime"] is True
        assert status["is_skeleton"] is False


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

        dex_classes = DexBuilder.extract_class_names(apk.read("classes.dex"))
        assert "org.renpy.android.PythonSDLActivity" in dex_classes

        status = apk.verify()
        assert status["device_installable"] is True
        assert status["launcher_activity_present"] is True

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

        dex_classes = DexBuilder.extract_class_names(apk.read("classes.dex"))
        assert "android.webkit.WebViewActivity" in dex_classes

        sig = apk.signature
        assert sig.is_signed is True
        assert sig.has_v1 is True
        assert sig.has_v2 is True


def test_pack_app_with_channel_tag(tmp_path: Path) -> None:
    project_dir = tmp_path / "kivy_store_app"
    KivyAppHelper.init_project(project_dir, title="Store App")

    output_huawei = tmp_path / "app_huawei.apk"
    KivyAppHelper.pack_app(project_dir, output_huawei, channel="huawei", release=True)

    assert output_huawei.exists()
    with APK(output_huawei) as apk:
        assert "assets/channel.txt" in apk.filenames
        assert apk.read("assets/channel.txt") == b"huawei"
        assert apk.signature.is_signed is True
        assert apk.signature.has_v2 is True


def test_pack_with_release_keystore(tmp_path: Path) -> None:
    """Tests signing using user-provided release keystore file."""
    ks_path = tmp_path / "my_release.keystore"
    ReleaseHelper.generate_release_keystore(ks_path, key_alias="mykey", store_pass="secret123")
    assert ks_path.exists()

    project_dir = tmp_path / "kivy_release_app"
    KivyAppHelper.init_project(project_dir, title="Release App")

    output_apk = tmp_path / "signed_release.apk"
    KivyAppHelper.pack_app(
        project_dir,
        output_apk,
        release=True,
        keystore=ks_path,
        password="secret123",
        alias="mykey",
    )
    assert output_apk.exists()

    with APK(output_apk) as apk:
        status = apk.verify()
        assert status["is_valid"] is True
        assert status["is_signed"] is True
        assert status["device_installable"] is True


def test_cli_pack_and_sign_keystore(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Tests CLI commands with release keystore and verify reporting."""
    ks_path = tmp_path / "cli_release.keystore"
    assert cli_main(["generate-keystore", "-o", str(ks_path), "--alias", "clikey", "--password", "clipass"]) == 0
    assert ks_path.exists()

    project_dir = tmp_path / "cli_kivy_app"
    KivyAppHelper.init_project(project_dir, title="CLI Kivy App")

    out_apk = tmp_path / "cli_packed.apk"
    ret = cli_main([
        "pack-kivy",
        str(project_dir),
        "-o",
        str(out_apk),
        "--keystore",
        str(ks_path),
        "--password",
        "clipass",
        "--alias",
        "clikey",
        "--release",
    ])
    assert ret == 0
    assert out_apk.exists()

    # CLI verify
    ret_verify = cli_main(["verify", str(out_apk)])
    assert ret_verify == 0
    captured = capsys.readouterr()
    assert "Device Ready:    True" in captured.out
    assert "Runtime Mode:    Skeleton" in captured.out
