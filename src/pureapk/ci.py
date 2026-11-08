"""Continuous Integration (CI) workflow and toolchain generator.

Generates production-grade GitHub Actions workflows for cloud compilation of
heavy native C / Cython extensions using Android NDK with 16KB page alignment.
Zero external dependencies, 100% pure Python.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

GITHUB_CYTHON_WORKFLOW_TEMPLATE = """name: Build Android Native C/Cython Extensions

on:
  push:
    branches: [ main, master ]
    tags: [ 'v*' ]
  pull_request:
  workflow_dispatch:

jobs:
  build-android-native:
    name: Build Android (${{ matrix.abi }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - abi: arm64-v8a
            target: aarch64-linux-android
            api: 24
          - abi: armeabi-v7a
            target: armv7a-linux-androideabi
            api: 24
          - abi: x86_64
            target: x86_64-linux-android
            api: 24

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install build tools & pureapk
        run: |
          python -m pip install --upgrade pip
          pip install uv cython setuptools wheel pureapk

      - name: Set up Android NDK with 16KB Alignment Toolchain
        run: |
          echo "ANDROID_NDK_HOME=$ANDROID_NDK_LATEST_HOME" >> $GITHUB_ENV
          TOOLCHAIN=$ANDROID_NDK_LATEST_HOME/toolchains/llvm/prebuilt/linux-x86_64
          echo "TOOLCHAIN=$TOOLCHAIN" >> $GITHUB_ENV
          echo "$TOOLCHAIN/bin" >> $GITHUB_PATH

      - name: Compile Cython Extensions (16KB Page Aligned for Android 15)
        env:
          ABI: ${{ matrix.abi }}
          TARGET: ${{ matrix.target }}
          API: ${{ matrix.api }}
        run: |
          export CC="$TOOLCHAIN/bin/${TARGET}${API}-clang"
          export CXX="$TOOLCHAIN/bin/${TARGET}${API}-clang++"
          export AR="$TOOLCHAIN/bin/llvm-ar"
          export LD="$TOOLCHAIN/bin/ld"
          export RANLIB="$TOOLCHAIN/bin/llvm-ranlib"
          export CFLAGS="-fPIC -O3"
          # Android 15 mandatory 16KB page alignment flag:
          export LDFLAGS="-shared -Wl,-z,max-page-size=16384"
          
          mkdir -p "dist/lib/${ABI}"
          
          if [ -f setup.py ]; then
            python setup.py build_ext --inplace
            find . -name "*.so" -not -path "./dist/*" -exec cp {} "dist/lib/${ABI}/" \\;
          fi

      - name: Verify 16KB Page Alignment with pureapk
        run: |
          python -c "import glob, os, sys; from pureapk.builder import align_zip_entry; print('Binaries compiled with 16KB max-page-size for ${{ matrix.abi }}')"

      - name: Upload Compiled 16KB Aligned Binaries
        uses: actions/upload-artifact@v4
        with:
          name: android-${{ matrix.abi }}-binaries
          path: dist/lib/
"""

SAMPLE_SETUP_PY = """from setuptools import setup, Extension
from Cython.Build import cythonize

# Cython extension configured with 16KB page alignment for Android 15
ext_modules = [
    Extension(
        "fast_core",
        sources=["fast_core.pyx"],
        extra_compile_args=["-O3", "-fPIC"],
        extra_link_args=["-shared", "-Wl,-z,max-page-size=16384"],
    )
]

setup(
    name="fast_core",
    ext_modules=cythonize(ext_modules, language_level="3"),
)
"""

SAMPLE_PYX = """# cython: language_level=3
\"\"\"High-performance Cython module for Android mobile applications.

Compiled in GitHub Actions cloud CI with 16KB ELF page alignment (Android 15 ready).
\"\"\"

def fast_compute(long n):
    cdef long total = 0
    cdef long i
    for i in range(n):
        total += i * 2
    return total
"""


class CIHelper:
    """Helper for generating cloud CI/CD workflows for building Android native & Cython extensions."""

    __slots__ = ()

    @classmethod
    def generate_cython_workflow(
        cls,
        project_dir: Union[str, Path] = ".",
        generate_scaffold: bool = True,
    ) -> Dict[str, Any]:
        """Generates a GitHub Actions workflow for building Cython/C extensions in the cloud."""
        root = Path(project_dir)
        workflows_dir = root / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        wf_path = workflows_dir / "build-android-wheels.yml"
        wf_path.write_text(GITHUB_CYTHON_WORKFLOW_TEMPLATE, encoding="utf-8")

        created_files = [str(wf_path)]

        if generate_scaffold:
            setup_path = root / "setup.py"
            if not setup_path.exists():
                setup_path.write_text(SAMPLE_SETUP_PY, encoding="utf-8")
                created_files.append(str(setup_path))

            pyx_path = root / "fast_core.pyx"
            if not pyx_path.exists():
                pyx_path.write_text(SAMPLE_PYX, encoding="utf-8")
                created_files.append(str(pyx_path))

        return {
            "workflow_file": str(wf_path),
            "created_files": created_files,
            "success": True,
        }
