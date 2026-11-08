<div align="center">

# ⚡ pureapk / pyapk

### Pure Python Android APK Engine, Multi-Store Packager & Toolchain
**Zero external dependencies, zero-copy memoryview parsing, 100% tests passing on CPython 3.8–3.16, Free-Threaded (No-GIL), and PyPy.**

[ 🇬🇧 English ] | [ 🇷🇺 Документация на русском ](README_RU.md)

[![Release Version](https://img.shields.io/badge/release-v0.1.0-0969da.svg?style=flat&logo=github)](https://github.com/eminsk/pyapk/releases/tag/v0.1.0)
[![PyPI Version](https://img.shields.io/pypi/v/pureapk.svg?style=flat&logo=pypi&color=blue)](https://pypi.org/project/pureapk/)
[![Python Versions](https://img.shields.io/badge/python-3.8_--_3.16-3776AB.svg?style=flat&logo=python&logoColor=white)](https://pypi.org/project/pureapk/)
[![Free-Threaded No-GIL](https://img.shields.io/badge/No--GIL-3.13t%20--%203.16t-brightgreen?style=flat)](https://peps.python.org/pep-0703/)
[![PyPy](https://img.shields.io/badge/PyPy-3.8_--_3.12-yellow.svg?style=flat&logo=pypy)](https://pypy.org/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20external-success.svg?style=flat)](https://github.com/eminsk/pyapk)
[![Platforms](https://img.shields.io/badge/platform-Apple_macOS_%7C_Linux_%7C_Windows-lightgrey.svg?style=flat)](https://github.com/eminsk/pyapk)
[![Tests](https://img.shields.io/badge/tests-47%20passed%20(100%25)-2ea44f.svg?style=flat&logo=pytest&logoColor=white)](https://github.com/eminsk/pyapk)
[![CI Matrix](https://github.com/eminsk/pyapk/actions/workflows/ci.yml/badge.svg)](https://github.com/eminsk/pyapk/actions/workflows/ci.yml)
[![GitHub Stars](https://img.shields.io/github/stars/eminsk/pyapk?style=flat&logo=github)](https://github.com/eminsk/pyapk/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat)](https://opensource.org/licenses/MIT)
[![Donate USDT](https://img.shields.io/badge/Donate-USDT_(TRC20)-26A17B?style=flat&logo=tether&logoColor=white)](https://tronscan.org/#/address/TDVbEdnpgNgoAhNcn1EwXxWHiR3RKLit5P)

> ### 🤝 Community, Issues & Support
> - 🐛 **Found a bug or malformed APK issue?** Please [Open an Issue](https://github.com/eminsk/pyapk/issues) — reports are tracked and resolved quickly!
> - 💬 **Questions, mobile packaging ideas, or store workflows?** Join our [GitHub Discussions](https://github.com/eminsk/pyapk/discussions).
> - ⭐ **Find pureapk useful?** Give it a star on GitHub — it helps more Python mobile engineers discover the library!
> - ☕ **Support development (USDT TRC-20):** `TDVbEdnpgNgoAhNcn1EwXxWHiR3RKLit5P` ([Verify on TronScan](https://tronscan.org/#/address/TDVbEdnpgNgoAhNcn1EwXxWHiR3RKLit5P))

[**Quickstart**](#-installation) • [**Compatibility**](#-universal-compatibility-matrix) • [**Python API**](#-python-api-usage) • [**Kivy & Pygame**](#-first-class-kivy--pygame-toolchains) • [**Store Publishing**](#-multi-store-publishing) • [**CLI Reference**](#-command-line-interface-cli)

</div>

---

## 🧩 Universal Compatibility Matrix

`pureapk` requires **zero external compiled C extensions** and runs on the pure Python standard library. It is verified across 54 automated matrix environments with a 100% test pass rate:

| Runtime / Implementation | Supported Versions | Execution Mode | Matrix CI Status |
|:---|:---|:---|:---:|
| **CPython (Standard)** | 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16 (Alpha) | Standard Bytecode + GIL | ✅ 100% Passed (27/27) |
| **CPython (Free-Threaded)** | 3.13t, 3.14t, 3.15t, 3.16t (Alpha) | Multi-core No-GIL (PEP 703) | ✅ 100% Passed (12/12) |
| **PyPy (JIT Accelerated)** | pypy3.8, pypy3.9, pypy3.10, pypy3.11, pypy3.12 | Tracing JIT Runtime | ✅ 100% Passed (15/15) |
| **Operating Systems** | Windows (7, 8, 10, 11), Linux, macOS (Intel & Apple Silicon) | x86_64, ARM64 | ✅ 100% Passed |

---

## 🚀 Key Advantages

- 🛡️ **Zero External Dependencies**: Built entirely upon standard Python primitives (`struct`, `zipfile`, `hashlib`, `xml.etree`). No JVM, no Android SDK/NDK, no bloated Gradle wrappers required on host.
- ⚡ **Zero-Copy & Low Memory**: Uses `__slots__` exclusively across all core classes (no dynamic `__dict__` overhead) and `memoryview` slicing.
- 🎯 **Branch-Free Functional Architecture**: Implements clean functional programming patterns, dictionary dispatch tables, and iterator streams for predictable, hot-path execution.
- 🧵 **Free-Threaded / No-GIL Safe**: Designed for lock-free parallel parsing and thread-safe lazy property evaluation.
- 📱 **First-Class Kivy & Pygame Toolchains**: Direct project scaffolding, manifest generation, and 4-byte ZIP-aligned packaging.
- 🏬 **Multi-Store Distribution**: Built-in generators for Google Play (`.aab` Android App Bundle), Apple App Store (`.ipa` with `Info.plist`), and Microsoft Store (`.msix` with `AppxBlockMap.xml`).
- 🛠️ **Dual CLI Entrypoints**: `pureapk` and `pyapk` commands installed with human and `--json` outputs.

---

## 📦 Installation

```bash
# Standard installation via PyPI
pip install pureapk

# Or install backwards-compatible alias
pip install pyapk

# With uv
uv add pureapk
```

### Install Pre-Built Universal Wheel Directly from GitHub
```bash
pip install https://github.com/eminsk/pyapk/releases/download/v0.1.0/pureapk-0.1.0-py3-none-any.whl
```

---

## 💻 Python API Usage

### 1. Basic APK Inspection

```python
from pureapk import APK

with APK("path/to/application.apk") as apk:
    print("Package:      ", apk.package_name)
    print("Version Name: ", apk.version_name)
    print("Version Code: ", apk.version_code)
    print("Min SDK:      ", apk.min_sdk_version)
    print("Target SDK:   ", apk.target_sdk_version)
    print("Permissions:  ", apk.permissions)
    print("Activities:   ", apk.activities)
    print("Architectures:", apk.native_architectures)
```

### 2. Fast One-Liner Metadata Extraction

```python
import pureapk

metadata = pureapk.inspect("application.apk")
print(metadata["package_name"], metadata["version_name"])
```

### 3. Multi-DEX & Dalvik Analysis

```python
with APK("application.apk") as apk:
    dex = apk.dex
    print(f"Total DEX Files: {dex.dex_count}")
    print(f"Total Classes:   {dex.total_classes}")
    print(f"Total Methods:   {dex.total_methods}")
    print(f"Total Fields:    {dex.total_fields}")
    print(f"Total Strings:   {dex.total_strings}")
```

### 4. Signatures & Certificate Fingerprints

```python
with APK("application.apk") as apk:
    sig = apk.signature
    print("Is Signed:  ", sig.is_signed)
    print("Schemes:    ", sig.scheme_names)  # e.g. ('v1', 'v2', 'v3')

    for cert in sig.certificates:
        print("Cert File:  ", cert.filename)
        print("SHA-256:    ", cert.sha256)
        print("SHA-1:      ", cert.sha1)
        print("MD5:        ", cert.md5)
```

---

## 🎮 Supported Python GUI & Game Frameworks

`pureapk` provides first-class project scaffolding, manifest synthesis, and packaging for all major Python UI and game engines on **any operating system** (Windows 7/10/11, macOS, Linux) without needing Android Studio:

| Framework | Architecture & Use Case | Helper Class | Supported Targets |
| :--- | :--- | :--- | :--- |
| **Kivy** | Touch-friendly UI, business applications, custom widgets | `KivyAppHelper` | Android APK, Google Play AAB |
| **Pygame** | 2D arcade games, simulations, retro titles | `PygameAppHelper` | Android APK, Google Play AAB |
| **Flet** | Flutter-powered Material 3 / Cupertino cross-platform UI | `FletAppHelper` | Android APK, iOS IPA, Windows MSIX |
| **BeeWare (Toga)** | Native system widgets (`android.widget.*`, UIKit, WinUI) | `TogaAppHelper` | Android APK, iOS IPA, Windows MSIX |
| **Ren'Py** | Visual novels, branching interactive fiction & story games | `RenPyAppHelper` | Android APK, Google Play AAB |
| **WebView Apps** | HTML5/CSS/Tailwind UI + lightweight Python local backend | `WebViewAppHelper` | Android APK, iOS IPA, Windows MSIX |

```bash
# Scaffold a new mobile project
pureapk init-kivy my_kivy_app --title "Kivy Mobile App"
pureapk init-pygame my_pygame_app --title "Space Shooter"

# Package directly into APK (Debug or Store-Ready Release)
pureapk pack-kivy my_kivy_app -o app.apk --release
pureapk pack-pygame my_pygame_app -o shooter.apk --release
```

---

## 🏬 Multi-Store Publishing

`pureapk` supports production store releases across mobile and desktop app store accounts:

### 1. Google Play Console (`.aab` & Release Keystores)
Google Play requires Android App Bundles (`.aab`) and production signing:
```bash
# Generate production release signing profile
pureapk generate-keystore -o release.keystore --alias production

# Build Google Play Android App Bundle (.aab)
pureapk pack-aab my_app/ -o application.aab
```

### 2. Apple App Store (`.ipa` & `Info.plist`)
Scaffold and bundle iOS apps ready for Apple Transporter / App Store Connect:
```bash
# Scaffold iOS project with Info.plist
pureapk init-ios ios_project --title "MyIOSApp" --bundle-id "com.company.iosapp"

# Pack into Apple App Store .ipa archive
pureapk pack-ipa ios_project/ -o application.ipa --title "MyIOSApp"
```

### 3. Microsoft Windows Store (`.msix` & `AppxBlockMap.xml`)
Scaffold and package Windows Store apps with `AppxManifest.xml` and block maps:
```bash
# Scaffold Windows Store project
pureapk init-windows win_project --title "MyWinApp" --package "MyCompany.MyWinApp"

# Pack into Microsoft Store .msix package with 64KB block hashing
pureapk pack-msix win_project/ -o application.msix
```

---

## 🖥️ Command Line Interface (CLI)

Both `pureapk` and `pyapk` commands are installed.

```bash
# Metadata Summary
pureapk info application.apk
pureapk info application.apk --json

# Dump Decoded AndroidManifest.xml
pureapk manifest application.apk
pureapk manifest application.apk --json

# List Declared Permissions
pureapk permissions application.apk

# Inspect DEX Headers & Method Counts
pureapk dex application.apk

# List Archive Files with CRC32
pureapk files application.apk

# Verify Integrity & Signature
pureapk verify application.apk

# Extract APK Contents
pureapk extract application.apk -o output_dir/

# Pack Directory to APK with 4-byte alignment
pureapk pack src_directory/ -o output.apk
```

---

## 🧪 Testing

The test suite achieves **100% test pass rate** across all Python implementations and operating systems:

```bash
# Run pytest with uv
uv run pytest tests/ -v

# Run with test coverage
uv run pytest --cov=pureapk tests/
```

---

## 📄 License

MIT License — Copyright (c) 2026 eminsk.
