"""Tests for end-to-end self-contained executable APK packaging, DEX validity, and device install parity."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile
import zipfile
import pytest
from pureapk.apk import APK
from pureapk.cli import main as cli_main
from pureapk.dex import DexBuilder, DexHeader
from pureapk.frameworks import KivyAppHelper, PygameAppHelper, WebViewAppHelper
from pureapk.manifest import AndroidManifest, AxmlEncoder
from pureapk.resources import ArscBuilder
from pureapk.signature import _DEBUG_CERT_DER, _RELEASE_CERT_DER
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
        axml_bytes = apk.read("AndroidManifest.xml")
        manifest = AndroidManifest(axml_bytes)
        assert manifest.package_name == "org.mykivy.game"
        assert "org.kivy.android.PythonActivity" in manifest.activities
        assert manifest.application_icon == ""  # Safely omitted when no icon in res/
        # Verify RES_XML_RESOURCE_MAP_TYPE (0x0180) chunk is emitted after string pool
        sp_size = struct.unpack_from("<I", axml_bytes, 12)[0]
        res_map_type, _, res_map_size = struct.unpack_from("<HHI", axml_bytes, 8 + sp_size)
        assert res_map_type == 0x0180
        assert res_map_size > 8

        # 5. Verification checks separate structural parse readiness from runnable native runtime
        status = apk.verify()
        assert status["is_valid"] is True
        assert status["structural_parse_ready"] is True
        assert status["runnable_on_device"] is False
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
        assert status["structural_parse_ready"] is True
        assert status["runnable_on_device"] is True
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
    """Tests signing using user-provided release keystore file with unique RSA-2048 keys."""
    ks_path = tmp_path / "my_release.keystore"
    ReleaseHelper.generate_release_keystore(ks_path, key_alias="mykey", store_pass="secret123")
    assert ks_path.exists()

    meta = ReleaseHelper.load_release_keystore(ks_path, store_pass="secret123", key_alias="mykey")
    assert meta["key_alias"] == "mykey"
    assert isinstance(meta["cert_der"], bytes) and len(meta["cert_der"]) > 200
    assert meta["cert_der"] != _DEBUG_CERT_DER
    assert meta["cert_der"] != _RELEASE_CERT_DER

    # Wrong password must raise ValueError
    with pytest.raises(ValueError, match="Invalid keystore password"):
        ReleaseHelper.load_release_keystore(ks_path, store_pass="wrong_password", key_alias="mykey")

    # Second keystore must have a distinct RSA keypair and certificate fingerprint
    ks_path2 = tmp_path / "second_release.keystore"
    ReleaseHelper.generate_release_keystore(ks_path2, key_alias="other", store_pass="pass456")
    meta2 = ReleaseHelper.load_release_keystore(ks_path2, store_pass="pass456", key_alias="other")
    assert meta2["sha256_fingerprint"] != meta["sha256_fingerprint"]
    assert meta2["rsa_n"] != meta["rsa_n"]

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
        assert status["structural_parse_ready"] is True
        assert len(apk.signature.certificates) == 1
        cert = apk.signature.certificates[0]
        assert cert.cert_sha256 == meta["sha256_fingerprint"]
        assert cert.cert_der == meta["cert_der"]

        # Verify PKCS#7 signature via openssl cms -verify if openssl is installed
        if shutil.which("openssl"):
            cert_rsa_path = tmp_path / "CERT.RSA"
            cert_sf_path = tmp_path / "CERT.SF"
            cert_rsa_path.write_bytes(apk.read("META-INF/CERT.RSA"))
            cert_sf_path.write_bytes(apk.read("META-INF/CERT.SF"))
            res = subprocess.run(
                [
                    "openssl",
                    "cms",
                    "-verify",
                    "-inform",
                    "DER",
                    "-in",
                    str(cert_rsa_path),
                    "-content",
                    str(cert_sf_path),
                    "-noverify",
                    "-out",
                    str(tmp_path / "verified.sf"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            assert res.returncode == 0, f"openssl cms -verify failed: {res.stderr}"


def test_cli_pack_and_sign_keystore(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Tests CLI commands with release keystore and honest verify reporting."""
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
    assert "Structural Parse: True" in captured.out
    assert "Runnable App:     False (Skeleton" in captured.out
    assert "Runtime Mode:     Skeleton" in captured.out


def _create_mock_p4a_runtime_apk(apk_path: Path, py_ver: Optional[str] = None) -> str:
    """Builds a minimal mock p4a runtime APK with native .so libraries, multi-dex, arsc, and manifest."""
    import sys
    if py_ver is None:
        py_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    arsc_bytes = ArscBuilder.generate_minimal_arsc(
        package_name="org.test.baseapp",
        app_name="Base Template App",
        private_version="0000000000000000000000000000000000000000",
    )
    xml_manifest = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    package="org.test.baseapp"\n'
        '    android:versionCode="1"\n'
        '    android:versionName="1.0">\n'
        '    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="33" />\n'
        '    <application android:label="Base Template App" android:icon="@mipmap/ic_launcher">\n'
        '        <activity android:name="org.kivy.android.PythonActivity" android:exported="true">\n'
        "            <intent-filter>\n"
        '                <action android:name="android.intent.action.MAIN" />\n'
        '                <category android:name="android.intent.category.LAUNCHER" />\n'
        "            </intent-filter>\n"
        "        </activity>\n"
        "    </application>\n"
        "</manifest>\n"
    )
    axml_bytes = AxmlEncoder.encode(xml_manifest)
    dex1 = DexBuilder.generate_bootstrap_dex(activity_classes=["org.kivy.android.PythonActivity"])
    dex2 = DexBuilder.generate_bootstrap_dex(activity_classes=["org.renpy.android.Hardware"])
    with zipfile.ZipFile(apk_path, "w") as zf:
        zf.writestr("AndroidManifest.xml", axml_bytes)
        zf.writestr("resources.arsc", arsc_bytes)
        zf.writestr("classes.dex", dex1)
        zf.writestr("classes2.dex", dex2)
        zf.writestr(f"lib/arm64-v8a/libpython{py_ver}.so", b"\x7fELF" + b"\x01" * 128)
        zf.writestr("lib/arm64-v8a/libpybundle.so", b"\x7fELF" + b"\x02" * 128)
        zf.writestr("lib/arm64-v8a/libSDL2.so", b"\x7fELF" + b"\x03" * 128)
        zf.writestr("res/drawable-mdpi-v4/icon.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
        zf.writestr("res/mipmap-hdpi/ic_launcher.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    return py_ver


def test_prepare_runtime_and_pack_runnable_kivy_apk(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Tests both --runtime-apk direct packaging and prepare-runtime seeding for runnable Kivy APKs."""
    import sys
    base_runtime_apk = tmp_path / "base_runtime.apk"
    py_ver = _create_mock_p4a_runtime_apk(base_runtime_apk)

    project_dir = tmp_path / "calc_project"
    KivyAppHelper.init_project(project_dir, title="Scientific Calculator")
    (project_dir / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\xaa" * 40)

    # 1. Pack directly using --runtime-apk via CLI
    out_apk = tmp_path / "calc_runnable.apk"
    ret = cli_main([
        "pack-kivy",
        str(project_dir),
        "-o",
        str(out_apk),
        "--package",
        "org.kivy.scicalc",
        "--title",
        "Scientific Calculator",
        "--runtime-apk",
        str(base_runtime_apk),
    ])
    assert ret == 0
    assert out_apk.exists()

    with APK(out_apk) as apk:
        assert f"lib/arm64-v8a/libpython{py_ver}.so" in apk.filenames
        assert "lib/arm64-v8a/libpybundle.so" in apk.filenames
        assert "classes.dex" in apk.filenames
        assert "classes2.dex" in apk.filenames
        assert "assets/private.tar" in apk.filenames

        # Check sitecustomize and main inside private.tar
        tar_bytes = apk.read("assets/private.tar")
        expected_priv_ver = hashlib.sha1(tar_bytes).hexdigest()
        with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tf:
            names = tf.getnames()
            assert "sitecustomize.py" in names
            assert "main.py" in names
            host_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
            if host_ver == py_ver and not hasattr(sys, "pypy_version_info"):
                assert "sitecustomize.pyc" in names
                assert "main.pyc" in names

        # Check patched AndroidManifest.xml
        manifest = AndroidManifest(apk.read("AndroidManifest.xml"))
        assert manifest.package_name == "org.kivy.scicalc"

        # Check patched resources.arsc
        arsc_bytes = apk.read("resources.arsc")
        assert ArscBuilder.is_valid_arsc(arsc_bytes) is True
        assert "org.kivy.scicalc".encode("utf-16le") in arsc_bytes
        assert b"Scientific Calculator" in arsc_bytes
        assert expected_priv_ver.encode("utf-8") in arsc_bytes

        # Check custom icon replaced template icon
        assert apk.read("res/drawable-mdpi-v4/icon.png") == b"\x89PNG\r\n\x1a\n" + b"\xaa" * 40

        status = apk.verify()
        assert status["structural_parse_ready"] is True
        assert status["runnable_on_device"] is True
        assert status["is_skeleton"] is False
        assert status["has_native_runtime"] is True

    # Verify CLI reports Full Native Python Runtime
    capsys.readouterr()
    assert cli_main(["verify", str(out_apk)]) == 0
    out_text = capsys.readouterr().out
    assert "Structural Parse: True" in out_text
    assert "Runnable App:     True (Full Native Python Runtime)" in out_text

    # 2. Test prepare-runtime CLI into a second project directory
    seeded_project = tmp_path / "seeded_calc"
    KivyAppHelper.init_project(seeded_project, title="Seeded App")
    assert cli_main(["prepare-runtime", "--from-apk", str(base_runtime_apk), str(seeded_project)]) == 0
    assert (seeded_project / "lib" / "arm64-v8a" / f"libpython{py_ver}.so").exists()
    assert (seeded_project / "classes2.dex").exists()

    out_seeded_apk = tmp_path / "seeded_out.apk"
    KivyAppHelper.pack_app(seeded_project, out_seeded_apk, package_name="org.seeded.app", app_title="Seeded App")
    with APK(out_seeded_apk) as apk2:
        st2 = apk2.verify()
        assert st2["runnable_on_device"] is True
        assert st2["is_skeleton"] is False


def test_independent_pyaxmlparser_verification(tmp_path: Path) -> None:
    """Verifies generated and patched APKs using the independent pyaxmlparser library if installed."""
    pyaxmlparser = pytest.importorskip("pyaxmlparser")
    from pyaxmlparser.arscparser import ARSCParser

    base_runtime_apk = tmp_path / "base.apk"
    _create_mock_p4a_runtime_apk(base_runtime_apk)

    project_dir = tmp_path / "indep_project"
    KivyAppHelper.init_project(project_dir, title="Independent Verified App")
    out_apk = tmp_path / "indep_verified.apk"
    KivyAppHelper.pack_app(
        project_dir,
        out_apk,
        package_name="com.independent.kivyapp",
        app_title="Independent Verified App",
        runtime_apk=base_runtime_apk,
    )

    with APK(out_apk) as apk:
        arsc_parser = ARSCParser(apk.read("resources.arsc"))
        assert arsc_parser.get_packages_names() == ["com.independent.kivyapp"]
        strings_xml = arsc_parser.get_string_resources("com.independent.kivyapp")
        assert b"Independent Verified App" in strings_xml

    ext_apk = pyaxmlparser.APK(str(out_apk))
    try:
        assert ext_apk.is_valid_APK() is True
        assert ext_apk.package == "com.independent.kivyapp"
        assert "org.kivy.android.PythonActivity" in ext_apk.get_activities()
    finally:
        if hasattr(ext_apk, "zip") and ext_apk.zip is not None:
            ext_apk.zip.close()


def test_kivy_pack_app_cross_version_safety(tmp_path: Path) -> None:
    """Tests that when target python version differs from host, safe fallback to .py is maintained."""
    base_runtime_apk = tmp_path / "cross_runtime.apk"
    _create_mock_p4a_runtime_apk(base_runtime_apk, py_ver="3.99")

    project_dir = tmp_path / "cross_project"
    KivyAppHelper.init_project(project_dir, title="Cross Version App")

    out_apk = tmp_path / "cross.apk"
    ret = cli_main([
        "pack-kivy",
        str(project_dir),
        "-o",
        str(out_apk),
        "--runtime-apk",
        str(base_runtime_apk),
    ])
    assert ret == 0
    with APK(out_apk) as apk:
        tar_bytes = apk.read("assets/private.tar")
        with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tf:
            names = tf.getnames()
            assert "sitecustomize.py" in names
            assert "main.py" in names
            assert "sitecustomize.pyc" not in names
            assert "main.pyc" not in names


