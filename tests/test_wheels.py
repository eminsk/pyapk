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

def test_build_wheel_pure_python(tmp_path: Path) -> None:
    src_dir = tmp_path / "my_pure_pkg"
    src_dir.mkdir()
    (src_dir / "my_pkg").mkdir()
    (src_dir / "my_pkg" / "__init__.py").write_text("x = 100\n", encoding="utf-8")
    (src_dir / "my_pkg" / "module.py").write_text("def hello(): return 'world'\n", encoding="utf-8")

    out_whl = tmp_path / "dist" / "my_pkg-2.5.0-py3-none-any.whl"
    res = AndroidWheelHelper.build_wheel(
        src_dir,
        output_whl=out_whl,
        distribution_name="my_pkg",
        version="2.5.0",
        python_tag="py3",
        summary="A pure python library",
    )

    assert out_whl.exists()
    assert res["distribution_name"] == "my_pkg"
    assert res["version"] == "2.5.0"
    assert res["python_tag"] == "py3"
    assert res["platform_tag"] == "any"

    # Verify wheel internal structure
    with zipfile.ZipFile(out_whl, "r") as zf:
        names = zf.namelist()
        assert "my_pkg/__init__.py" in names
        assert "my_pkg/module.py" in names
        assert "my_pkg-2.5.0.dist-info/METADATA" in names
        assert "my_pkg-2.5.0.dist-info/WHEEL" in names
        assert "my_pkg-2.5.0.dist-info/RECORD" in names

        wheel_meta = zf.read("my_pkg-2.5.0.dist-info/WHEEL").decode("utf-8")
        assert "Root-Is-Purelib: true" in wheel_meta
        assert "Tag: py3-none-any" in wheel_meta


def test_build_wheel_android_abi(tmp_path: Path) -> None:
    src_dir = tmp_path / "native_pkg"
    src_dir.mkdir()
    (src_dir / "engine").mkdir()
    (src_dir / "engine" / "__init__.py").write_text("# engine\n", encoding="utf-8")
    (src_dir / "engine" / "core.so").write_bytes(b"\x7fELF" + b"\x00" * 60)

    out_whl = tmp_path / "wheels" / "engine-1.0.0-cp310-cp310-android_24_arm64_v8a.whl"
    res = AndroidWheelHelper.build_wheel(
        src_dir,
        output_whl=out_whl,
        distribution_name="engine",
        version="1.0.0",
        python_tag="cp310",
        abi="arm64-v8a",
    )

    assert out_whl.exists()
    assert res["abi_tag"] == "cp310"
    assert res["platform_tag"] == "android_24_arm64_v8a"

    # Verify wheel inspection recognizes it as Android arm64
    info = AndroidWheelHelper.inspect_wheel(out_whl)
    assert info["detected_abi"] == "arm64-v8a"
    assert info["is_pure_python"] is False


def test_build_wheel_multi_python_versions(tmp_path: Path) -> None:
    src_dir = tmp_path / "multi_py"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("print('test')\n", encoding="utf-8")

    # Test all target Python versions from 3.8 up to 3.16 (including 3.16t No-GIL)
    for py_tag in ("cp38", "cp39", "cp310", "cp311", "cp312", "cp313", "cp314", "cp315", "cp316", "cp316t"):
        res = AndroidWheelHelper.build_wheel(
            src_dir,
            output_whl=tmp_path / "dist",
            distribution_name="multipy",
            version="1.0",
            python_tag=py_tag,
            abi="armeabi-v7a",
        )
        whl_path = Path(res["wheel_path"])
        assert whl_path.exists()
        assert f"-{py_tag}-" in whl_path.name
        assert "armeabi_v7a" in whl_path.name


def test_repack_wheel(tmp_path: Path) -> None:
    orig_whl = tmp_path / "old-1.0.0-cp312-cp312-android_24_arm64_v8a.whl"
    _create_mock_wheel(orig_whl)

    repacked_whl = tmp_path / "repacked-1.0.0-cp310-cp310-android_24_arm64_v8a.whl"
    res = AndroidWheelHelper.repack_wheel(
        orig_whl,
        repacked_whl,
        target_python_tag="cp310",
        target_abi="arm64-v8a",
    )
    assert repacked_whl.exists()
    assert res["python_tag"] == "cp310"
    assert res["platform_tag"] == "android_24_arm64_v8a"


def test_cli_pack_wheel(tmp_path: Path) -> None:
    src_dir = tmp_path / "cli_pkg"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('cli')\n", encoding="utf-8")

    out_file = tmp_path / "dist" / "cli_pkg-1.0.0-py3-none-any.whl"
    code = main([
        "pack-wheel",
        str(src_dir),
        "-o", str(out_file),
        "-n", "cli_pkg",
        "-v", "1.0.0",
        "--python-tag", "py3",
        "--json",
    ])
    assert code == 0
    assert out_file.exists()

def test_build_framework_wheels(tmp_path: Path) -> None:
    # Test packaging engine wheels for Kivy, Pygame, Flet, Toga, RenPy, WebView, PySide
    for fw in ("kivy", "pygame", "flet", "toga", "renpy", "webview", "pyside"):
        out_whl = tmp_path / "wheels" / f"{fw}-app-0.1.0-cp310-cp310-android_24_arm64_v8a.whl"
        res = AndroidWheelHelper.build_framework_wheel(
            framework=fw,
            output_whl=out_whl,
            python_tag="cp310",
            abi="arm64-v8a",
        )
        assert out_whl.exists()
        assert res["distribution_name"] == f"{fw}-app"
        assert res["python_tag"] == "cp310"
        assert res["abi_tag"] == "cp310"
        assert res["platform_tag"] == "android_24_arm64_v8a"


def test_cli_pack_wheel_with_framework(tmp_path: Path) -> None:
    out_whl = tmp_path / "kivy_wheel.whl"
    code = main([
        "pack-wheel",
        "-o", str(out_whl),
        "-n", "kivy-demo",
        "--framework", "kivy",
        "--python-tag", "py3",
        "--json",
    ])
    assert code == 0
    assert out_whl.exists()
