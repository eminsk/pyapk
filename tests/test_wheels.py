"""Tests for Android wheel (.whl) inspection and extraction toolkit."""

from __future__ import annotations

import io
from pathlib import Path
import zipfile
import pytest

from pureapk.cli import main
from pureapk.wheels import AndroidWheelHelper


def _create_mock_wheel(wheel_path: Path, abi_tag: str = "android_24_arm64_v8a") -> Path:
    """Helper to generate a mock PEP 427 wheel archive for testing."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Python module
        zf.writestr("my_math/__init__.py", "from ._fast import add\n")
        zf.writestr("my_math/utils.py", "def helper(): return 42\n")
        # Native shared library
        zf.writestr("my_math/_fast.cpython-312.so", b"\x7fELF" + b"\x00" * 50)
        # Dist info
        zf.writestr(
            "my_math-1.0.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: my_math\nVersion: 1.0.0\nSummary: Fast math\n",
        )
        zf.writestr("my_math-1.0.0.dist-info/RECORD", "records...\n")

    wheel_path.parent.mkdir(parents=True, exist_ok=True)
    wheel_path.write_bytes(buf.getvalue())
    return wheel_path


def test_detect_abi_from_filename() -> None:
    assert AndroidWheelHelper.detect_abi_from_filename("numpy-1.26.4-cp312-cp312-android_24_arm64_v8a.whl") == "arm64-v8a"
    assert AndroidWheelHelper.detect_abi_from_filename("pkg-1.0-cp311-cp311-linux_aarch64.whl") == "arm64-v8a"
    assert AndroidWheelHelper.detect_abi_from_filename("scipy-1.11.0-cp310-cp310-android_armeabi_v7a.whl") == "armeabi-v7a"
    assert AndroidWheelHelper.detect_abi_from_filename("torch-2.1-cp312-cp312-android_x86_64.whl") == "x86_64"
    assert AndroidWheelHelper.detect_abi_from_filename("pkg-1.0-cp310-cp310-android_x86.whl") == "x86"
    assert AndroidWheelHelper.detect_abi_from_filename("requests-2.31.0-py3-none-any.whl") is None


def test_inspect_wheel(tmp_path: Path) -> None:
    wheel_file = tmp_path / "my_math-1.0.0-cp312-cp312-android_24_arm64_v8a.whl"
    _create_mock_wheel(wheel_file)

    info = AndroidWheelHelper.inspect_wheel(wheel_file)
    assert info["distribution_name"] == "my_math"
    assert info["version"] == "1.0.0"
    assert info["detected_abi"] == "arm64-v8a"
    assert info["is_pure_python"] is False
    assert len(info["native_libraries"]) == 1
    assert "my_math/_fast.cpython-312.so" in info["native_libraries"]


def test_unpack_wheel(tmp_path: Path) -> None:
    wheel_file = tmp_path / "my_math-1.0.0-cp312-cp312-android_24_arm64_v8a.whl"
    _create_mock_wheel(wheel_file)

    project_dir = tmp_path / "my_mobile_app"
    res = AndroidWheelHelper.unpack_wheel(wheel_file, project_dir)

    assert res["target_abi"] == "arm64-v8a"
    assert (project_dir / "lib" / "arm64-v8a" / "_fast.cpython-312.so").exists()
    assert (project_dir / "my_math" / "__init__.py").exists()
    assert (project_dir / "my_math" / "utils.py").exists()
    assert (project_dir / "my_math" / "_fast.cpython-312.so").exists()


def test_cli_unpack_wheel(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    wheel_file = tmp_path / "my_math-1.0.0-cp312-cp312-android_24_arm64_v8a.whl"
    _create_mock_wheel(wheel_file)

    project_dir = tmp_path / "cli_app"
    code = main(["unpack-wheel", str(wheel_file), str(project_dir), "--json"])
    assert code == 0

    assert (project_dir / "lib" / "arm64-v8a" / "_fast.cpython-312.so").exists()
