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


def test_ipa_signer_and_code_resources(tmp_path: Path) -> None:
    from pureapk.signature import IPASigner

    # 1. Test generate_self_signed_profile & parse_provisioning_profile
    prof_bytes = AppleAppHelper.generate_self_signed_profile(
        bundle_id="com.company.magic",
        app_name="MagicApp",
        team_name="Magic Studio",
        team_id="MGC12345",
    )
    assert b"MagicApp Development Profile" in prof_bytes
    parsed_prof = AppleAppHelper.parse_provisioning_profile(prof_bytes)
    assert parsed_prof["valid"] is True
    assert parsed_prof["name"] == "MagicApp Development Profile"
    assert parsed_prof["team_identifier"] == "MGC12345"
    assert parsed_prof["is_expired"] is False

    # 2. Test generate_developer_p12
    p12_path = tmp_path / "developer.p12"
    p12_res = AppleAppHelper.generate_developer_p12(p12_path, password="secret", common_name="Apple Developer: Test")
    assert p12_path.exists()
    assert p12_res["valid"] is True

    # 3. Test generate_code_resources
    files_map = {
        "Info.plist": b"<plist><dict/></plist>",
        "PkgInfo": b"APPL????",
        "main.py": b"print('Hello iOS')",
        "assets/icon.png": b"\x89PNG\r\n\x1a\n",
    }
    cr_bytes = AppleAppHelper.generate_code_resources(files_map)
    import plistlib
    cr_dict = plistlib.loads(cr_bytes)
    assert "files" in cr_dict
    assert "files2" in cr_dict
    assert "Info.plist" in cr_dict["files2"]
    assert "main.py" in cr_dict["files2"]
    assert "hash" in cr_dict["files2"]["main.py"]
    assert "hash2" in cr_dict["files2"]["main.py"]

    # 4. Build unsigned/raw IPA
    raw_ipa = tmp_path / "Unsigned.ipa"
    builder = IPABuilder(raw_ipa, app_name="MagicApp")
    builder.add_bytes("main.py", b"print('Magic iOS')")
    builder.add_bytes("assets/data.json", b'{"key": "value"}')
    builder.build(sign=False)
    assert raw_ipa.exists()

    # 5. Sign IPA with IPASigner
    signed_ipa = tmp_path / "Signed.ipa"
    prof_file = tmp_path / "embedded.mobileprovision"
    prof_file.write_bytes(prof_bytes)

    res = IPASigner.sign_ipa(
        raw_ipa,
        output_ipa=signed_ipa,
        p12_path=p12_path,
        p12_password="secret",
        mobileprovision_path=prof_file,
        bundle_id="com.company.magic",
        app_name="MagicApp Pro",
    )
    assert res["success"] is True
    assert signed_ipa.exists()
    assert res["has_code_resources"] is True
    assert res["has_provisioning_profile"] is True

    # 6. Verify signed IPA
    verify_rep = AppleAppHelper.verify_ipa(signed_ipa)
    assert verify_rep["valid"] is True
    assert verify_rep["has_pkginfo"] is True
    assert verify_rep["has_code_resources"] is True
    assert verify_rep["signature_valid"] is True
    assert verify_rep["has_provisioning_profile"] is True
    assert verify_rep["profile_info"]["team_identifier"] == "MGC12345"
    assert verify_rep["sideload_ready"] is True

    # 7. Test CLI commands: sign-ipa & ipa-profile & ipa-check
    cli_signed = tmp_path / "cli_signed.ipa"
    assert cli_main(["sign-ipa", str(raw_ipa), "-o", str(cli_signed), "--bundle-id", "com.cli.app", "--json"]) == 0
    assert cli_signed.exists()
    assert cli_main(["ipa-profile", str(cli_signed), "--json"]) == 0
    assert cli_main(["ipa-profile", str(prof_file)]) == 0

    # 8. Test Apple Developer Portal credentials validation & ipa-check
    cred_rep = AppleAppHelper.verify_developer_credentials(
        p12_path=p12_path,
        p12_password="secret",
        profile_path=prof_file,
        target_bundle_id="com.company.magic",
        target_udid="0000000000000000000000000000000000000000",
    )
    assert cred_rep["ready"] is True
    assert cred_rep["status"] == "ACTIVE & COMPATIBLE"
    assert len(cred_rep["checks"]) >= 5

    # Test CLI ipa-check command
    assert cli_main(["ipa-check", "--ipa", str(signed_ipa)]) == 0
    assert cli_main(["ipa-check", "--p12", str(p12_path), "--password", "secret", "--profile", str(prof_file), "--bundle-id", "com.company.magic", "--json"]) == 0

    # 9. Test Apple OTA Manifest & Web Installer Generation
    ota_xml = AppleAppHelper.generate_ota_manifest(
        ipa_url="https://example.com/MagicApp.ipa",
        bundle_id="com.company.magic",
        app_title="MagicApp Pro",
        version="2.0.0",
        icon_url="https://example.com/icon.png",
    )
    assert "software-package" in ota_xml
    assert "https://example.com/MagicApp.ipa" in ota_xml
    assert "com.company.magic" in ota_xml
    assert "MagicApp Pro" in ota_xml

    ota_html = AppleAppHelper.generate_ota_html(
        manifest_url="https://example.com/manifest.plist",
        app_title="MagicApp Pro",
        bundle_id="com.company.magic",
        version="2.0.0",
        icon_url="https://example.com/icon.png",
    )
    assert "itms-services://?action=download-manifest" in ota_html
    assert "https://example.com/manifest.plist" in ota_html
    assert "MagicApp Pro" in ota_html

    # Test CLI ipa-ota
    ota_manifest_file = tmp_path / "ota_manifest.plist"
    assert cli_main([
        "ipa-ota", str(signed_ipa),
        "-o", str(ota_manifest_file),
        "--url", "https://example.com/app.ipa",
        "--html",
        "--json",
    ]) == 0
    assert ota_manifest_file.exists()
    assert (tmp_path / "index.html").exists()

    # 10. Test Apple CSR Generation
    csr_file = tmp_path / "developer.certSigningRequest"
    key_file = tmp_path / "developer.key"
    csr_res = AppleAppHelper.generate_csr(
        output_csr_path=csr_file,
        output_key_path=key_file,
        email="john@appledev.com",
        name="John Apple",
    )
    assert csr_res["success"] is True
    assert csr_file.exists()
    assert key_file.exists()

    # Test CLI ipa-csr
    cli_csr = tmp_path / "cli.certSigningRequest"
    assert cli_main(["ipa-csr", "-o", str(cli_csr), "--email", "test@apple.com", "--json"]) == 0
    assert cli_csr.exists()
