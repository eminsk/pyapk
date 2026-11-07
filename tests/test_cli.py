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
    assert pyapk.__version__ == "0.1.0"
