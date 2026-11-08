"""Builds universal py3-none-any wheels and sdists for both pureapk and pyapk."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)

PYPROJECT_PUREAPK = ROOT / "pyproject.toml"
PYPROJECT_PYAPK = ROOT / "pyproject_pyapk.toml"

PYAPK_TOML_CONTENT = """[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyapk"
version = "0.1.2"
description = "High-performance pure Python APK inspection and packaging toolkit."
readme = "README.md"
license = { text = "MIT" }
authors = [
    { name = "eminsk", email = "M_N_N@tut.by" }
]
requires-python = ">=3.8"
dependencies = []

classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Programming Language :: Python :: 3.15",
    "Programming Language :: Python :: 3.16",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Utilities",
]

[project.urls]
Homepage = "https://github.com/eminsk/pyapk"
Repository = "https://github.com/eminsk/pyapk.git"

[project.scripts]
pureapk = "pureapk.cli:main"
pyapk = "pureapk.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/pureapk", "src/pyapk"]
"""


def _run_build() -> None:
    if shutil.which("uv"):
        try:
            subprocess.run(["uv", "build"], cwd=ROOT, check=True)
            return
        except Exception as e:
            print(f"uv build failed ({e}), falling back to python -m build")
    subprocess.run([sys.executable, "-m", "build"], cwd=ROOT, check=True)


def build_package(name: str) -> None:
    print(f"=== Building {name} ===")
    if name == "pureapk":
        _run_build()
    elif name == "pyapk":
        # Temporarily swap pyproject.toml
        backup_toml = ROOT / "pyproject.toml.bak"
        shutil.copy2(PYPROJECT_PUREAPK, backup_toml)
        try:
            PYPROJECT_PYAPK.write_text(PYAPK_TOML_CONTENT, encoding="utf-8")
            shutil.copy2(PYPROJECT_PYAPK, PYPROJECT_PUREAPK)
            _run_build()
        finally:
            shutil.copy2(backup_toml, PYPROJECT_PUREAPK)
            if backup_toml.exists():
                backup_toml.unlink()
            if PYPROJECT_PYAPK.exists():
                PYPROJECT_PYAPK.unlink()


def main() -> None:
    build_package("pureapk")
    build_package("pyapk")
    print("\n=== Dist directory contents ===")
    for item in sorted(DIST.iterdir()):
        if item.is_file() and not item.name.startswith("."):
            print(f"  {item.name} ({item.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
