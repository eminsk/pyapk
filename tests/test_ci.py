"""Tests for continuous integration (CI) workflow generation."""

from __future__ import annotations

from pathlib import Path
import pytest

from pureapk.ci import CIHelper
from pureapk.cli import main


def test_generate_cython_workflow(tmp_path: Path) -> None:
    res = CIHelper.generate_cython_workflow(tmp_path, generate_scaffold=True)
    assert res["success"] is True

    workflow_file = tmp_path / ".github" / "workflows" / "build-android-wheels.yml"
    assert workflow_file.exists()
    content = workflow_file.read_text(encoding="utf-8")

    # Critical Android 15 16KB max page size flag
    assert "-Wl,-z,max-page-size=16384" in content
    # Architecture matrix
    assert "arm64-v8a" in content
    assert "armeabi-v7a" in content
    assert "x86_64" in content

    # Scaffold files
    assert (tmp_path / "setup.py").exists()
    assert (tmp_path / "fast_core.pyx").exists()


def test_cli_init_ci(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["init-ci", str(tmp_path), "--cython", "--json"])
    assert code == 0

    wf = tmp_path / ".github" / "workflows" / "build-android-wheels.yml"
    assert wf.exists()
