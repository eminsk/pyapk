"""Tests for CLI subcommands and argument handling."""

from __future__ import annotations

import io
import json
from pathlib import Path
import pytest
from pureapk.cli import main


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "pureapk" in captured.out
    assert "info" in captured.out
    assert "manifest" in captured.out


def test_cli_info_human(sample_apk_file: str, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["info", sample_apk_file])
    assert code == 0
    captured = capsys.readouterr()
    assert "Package:        com.example.testapp" in captured.out
    assert "Version Code:   101" in captured.out


def test_cli_info_json(sample_apk_file: str, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["info", sample_apk_file, "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["package_name"] == "com.example.testapp"
    assert data["version_code"] == 101


def test_cli_manifest(sample_apk_file: str, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["manifest", sample_apk_file, "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["package_name"] == "com.example.testapp"


def test_cli_permissions(sample_apk_file: str, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["permissions", sample_apk_file, "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "android.permission.INTERNET" in data["permissions"]


def test_cli_dex(sample_apk_file: str, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["dex", sample_apk_file, "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["dex_count"] == 2
    assert data["total_classes"] == 15


def test_cli_files(sample_apk_file: str, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["files", sample_apk_file, "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data["files"]) >= 5


def test_cli_verify(sample_apk_file: str, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["verify", sample_apk_file, "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["is_valid"] is True


def test_cli_extract(sample_apk_file: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = str(tmp_path / "cli_extracted")
    code = main(["extract", sample_apk_file, "-o", out_dir])
    assert code == 0
    assert (tmp_path / "cli_extracted" / "AndroidManifest.xml").exists()


def test_cli_direct_apk_argument(sample_apk_file: str, capsys: pytest.CaptureFixture[str]) -> None:
    code = main([sample_apk_file, "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["package_name"] == "com.example.testapp"


def test_cli_pyapk_entrypoint() -> None:
    import pyapk
    assert pyapk.APK is not None
    assert pyapk.__version__ == "1.0.2"


def test_cli_framework_subcommands(tmp_path: Path) -> None:
    # 1. flet
    f_dir = tmp_path / "cli_flet"
    f_apk = tmp_path / "flet.apk"
    assert main(["init-flet", str(f_dir), "--title", "FletCLI"]) == 0
    assert (f_dir / "main.py").exists()
    assert main(["pack-flet", str(f_dir), "-o", str(f_apk), "--title", "FletCLI", "--release"]) == 0
    assert f_apk.exists()

    # 2. toga
    t_dir = tmp_path / "cli_toga"
    t_apk = tmp_path / "toga.apk"
    assert main(["init-toga", str(t_dir), "--title", "TogaCLI"]) == 0
    assert (t_dir / "app.py").exists()
    assert main(["pack-toga", str(t_dir), "-o", str(t_apk), "--title", "TogaCLI", "--release"]) == 0
    assert t_apk.exists()

    # 3. renpy
    r_dir = tmp_path / "cli_renpy"
    r_apk = tmp_path / "renpy.apk"
    assert main(["init-renpy", str(r_dir), "--title", "RenPyCLI"]) == 0
    assert (r_dir / "game" / "script.rpy").exists()
    assert main(["pack-renpy", str(r_dir), "-o", str(r_apk), "--title", "RenPyCLI", "--release"]) == 0
    assert r_apk.exists()

    # 4. webview
    w_dir = tmp_path / "cli_web"
    w_apk = tmp_path / "web.apk"
    assert main(["init-webview", str(w_dir), "--title", "WebCLI"]) == 0
    assert (w_dir / "assets" / "index.html").exists()
    assert main(["pack-webview", str(w_dir), "-o", str(w_apk), "--title", "WebCLI", "--release"]) == 0
    assert w_apk.exists()

    # 5. pyside / pyqt
    p_dir = tmp_path / "cli_pyside"
    p_apk = tmp_path / "pyside.apk"
    assert main(["init-pyside", str(p_dir), "--title", "PySideCLI"]) == 0
    assert (p_dir / "main.py").exists()
    assert main(["pack-pyside", str(p_dir), "-o", str(p_apk), "--title", "PySideCLI", "--release"]) == 0
    assert p_apk.exists()


def test_cli_install_deps_validation(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty_proj"
    # Fails gracefully if no packages provided
    assert main(["install-deps", str(empty_dir)]) == 1
