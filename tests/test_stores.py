"""Tests for store packaging features: Google Play (AAB), Apple App Store (IPA), Microsoft Store (MSIX)."""

import os
from pathlib import Path
import zipfile

from pureapk.stores import (
    AABBuilder,
    AppleAppHelper,
    IPABuilder,
    MSIXBuilder,
    ReleaseHelper,
    WindowsStoreHelper,
)
from pureapk.cli import main as cli_main


def test_aab_builder(tmp_path: Path) -> None:
    src = tmp_path / "app_src"
    src.mkdir()
    (src / "AndroidManifest.xml").write_text("<manifest />", encoding="utf-8")
    (src / "classes.dex").write_bytes(b"dex\n035\x00")
    (src / "main.py").write_text("print('test')", encoding="utf-8")

    out_aab = tmp_path / "app.aab"
    builder = AABBuilder(out_aab)
    builder.add_base_directory(src)
    builder.build()

    assert out_aab.exists()
    with zipfile.ZipFile(out_aab, "r") as zf:
        names = zf.namelist()
        assert "BUNDLE-METADATA/com.android.tools.build.bundletool/BundleConfig.pb" in names
        assert "base/manifest/AndroidManifest.xml" in names
        assert "base/dex/classes.dex" in names
        assert "base/assets/main.py" in names


def test_release_helper(tmp_path: Path) -> None:
    raw_manifest = (
        '<application android:debuggable="true" android:label="Test">\n'
        '  <activity android:name=".MainActivity" />\n'
        '</application>'
    )
    sanitized = ReleaseHelper.sanitize_manifest_for_release(raw_manifest)
    assert 'android:debuggable="true"' not in sanitized

    ks_path = tmp_path / "release.keystore"
    meta = ReleaseHelper.generate_release_keystore(ks_path, key_alias="mykey", store_pass="secret123")
    assert ks_path.exists()
    assert meta["key_alias"] == "mykey"
    assert len(meta["sha256_fingerprint"]) == 64
    assert len(meta["sha1_fingerprint"]) == 40


def test_apple_ipa_packaging(tmp_path: Path) -> None:
    ios_dir = tmp_path / "ios_project"
    AppleAppHelper.init_project(ios_dir, app_name="CoolApp", bundle_id="com.cool.app")
    assert (ios_dir / "Info.plist").exists()
    assert (ios_dir / "main.py").exists()

    ipa_path = tmp_path / "CoolApp.ipa"
    builder = IPABuilder(ipa_path, app_name="CoolApp")
    builder.add_directory(ios_dir)
    builder.build()

    assert ipa_path.exists()
    with zipfile.ZipFile(ipa_path, "r") as zf:
        names = zf.namelist()
        assert "Payload/CoolApp.app/PkgInfo" in names
        assert "Payload/CoolApp.app/Info.plist" in names
        assert "Payload/CoolApp.app/main.py" in names

    # Automated Apple IPA validation without macOS
    report = AppleAppHelper.verify_ipa(ipa_path)
    assert report["valid"] is True
    assert report["app_name"] == "CoolApp"
    assert report["bundle_id"] == "com.cool.app"
    assert report["has_pkginfo"] is True
    assert report["sideload_ready"] is True

    # Test CLI IPA verification
    assert cli_main(["verify", str(ipa_path), "--json"]) == 0
    assert cli_main(["verify-ipa", str(ipa_path)]) == 0
    assert cli_main([str(ipa_path)]) == 0


def test_windows_msix_packaging(tmp_path: Path) -> None:
    win_dir = tmp_path / "win_project"
    WindowsStoreHelper.init_project(win_dir, display_name="CoolGame", package_name="CoolCo.CoolGame")
    assert (win_dir / "AppxManifest.xml").exists()
    assert (win_dir / "Assets" / "StoreLogo.png").exists()

    msix_path = tmp_path / "CoolGame.msix"
    builder = MSIXBuilder(msix_path)
    builder.add_directory(win_dir)
    builder.build()

    assert msix_path.exists()
    with zipfile.ZipFile(msix_path, "r") as zf:
        names = zf.namelist()
        assert "AppxManifest.xml" in names
        assert "AppxBlockMap.xml" in names
        assert "Assets/StoreLogo.png" in names
        # Verify block map has SHA-256 blocks
        block_map_data = zf.read("AppxBlockMap.xml").decode("utf-8")
        assert "<BlockMap" in block_map_data
        assert "HashMethod=" in block_map_data


def test_cli_store_commands(tmp_path: Path) -> None:
    # 1. generate-keystore
    ks = tmp_path / "test.keystore"
    assert cli_main(["generate-keystore", "-o", str(ks), "--alias", "testalias", "--json"]) == 0
    assert ks.exists()

    # 2. init-ios & pack-ipa
    ios_dir = tmp_path / "cli_ios"
    ipa_out = tmp_path / "cli_app.ipa"
    assert cli_main(["init-ios", str(ios_dir), "--title", "CliIosApp", "--bundle-id", "com.test.ios"]) == 0
    assert cli_main(["pack-ipa", str(ios_dir), "-o", str(ipa_out), "--title", "CliIosApp"]) == 0
    assert ipa_out.exists()

    # 3. init-windows & pack-msix
    win_dir = tmp_path / "cli_win"
    msix_out = tmp_path / "cli_app.msix"
    assert cli_main(["init-windows", str(win_dir), "--title", "CliWinApp", "--package", "Test.WinApp"]) == 0
    assert cli_main(["pack-msix", str(win_dir), "-o", str(msix_out)]) == 0
    assert msix_out.exists()

    # 4. pack-aab
    aab_out = tmp_path / "cli_app.aab"
    assert cli_main(["pack-aab", str(win_dir), "-o", str(aab_out)]) == 0
    assert aab_out.exists()
