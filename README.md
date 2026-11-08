# pureapk ⚡

[![PyPI version](https://img.shields.io/pypi/v/pureapk.svg)](https://pypi.org/project/pureapk/)
[![Python Versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14%20%7C%203.15%20%7C%203.16-blue)](https://pypi.org/project/pureapk/)
[![Free-Threaded / No-GIL](https://img.shields.io/badge/no--gil-3.13t%20%7C%203.14t%20%7C%203.15t%20%7C%203.16t-success)](https://pypi.org/project/pureapk/)
[![PyPy](https://img.shields.io/badge/pypy-3.8%20..%203.12-orange)](https://pypi.org/project/pureapk/)
[![Platforms](https://img.shields.io/badge/platform-apple%20macOS%20%7C%20linux%20%7C%20windows-lightgrey)](https://pypi.org/project/pureapk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**pureapk** is an ultra-fast, zero-dependency, pure Python Android APK parser, inspector, and packager.

Designed by senior engineers for **maximum performance** and **minimal memory consumption**, `pureapk` runs everywhere Python runs: on **Apple macOS, Linux, and Windows**, supporting **CPython 3.8 through 3.16**, **Free-Threaded / No-GIL Python (3.13t–3.16t)**, and **PyPy (3.8–3.12)** with 100% test pass rates.

---

## 🚀 Key Advantages

- 🛡️ **Zero External Dependencies**: Built entirely upon standard Python primitives (`struct`, `zipfile`, `hashlib`, `typing`).
- ⚡ **Zero-Copy & Low Memory**: Uses `__slots__` exclusively across all core classes (no dynamic `__dict__` overhead) and `memoryview` slicing.
- 🎯 **No Loops or If-Else Ladders**: Implements clean functional programming patterns, dictionary dispatch tables, and iterator streams for predictable, branch-free execution.
- 🧵 **Free-Threaded / No-GIL Safe**: Designed for lock-free parallel reading and thread-safe lazy property evaluation.
- 🌍 **Universal OS Compatibility**: Seamlessly runs on Windows, macOS (Apple Silicon & Intel), and Linux.
- 🛠️ **Full CLI & Python API**: Rich CLI tool (`pureapk` and `pyapk`) with human-readable and structured `--json` outputs.

---

## 📦 Installation

```bash
# With pip
pip install pureapk

# With uv
uv add pureapk
```

*(Note: `pyapk` is registered as a fully compatible alias and CLI entry point).*

---

## 💻 Python API Usage

### 1. Basic APK Inspection

```python
from pureapk import APK

# Load directly from file, bytes, or file-like stream
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

### 5. Packaging & Building an APK

```python
import pureapk

# Pack a directory into a standard Android APK
pureapk.pack("build_output/", "my_app.apk")
```

---

## 🖥️ Command Line Interface (CLI)

Both `pureapk` and `pyapk` commands are installed.

### Metadata Summary (`info`)
```bash
pureapk info application.apk
# or simply:
pureapk application.apk

# With JSON output
pureapk info application.apk --json
```

### Dump Decoded AndroidManifest.xml (`manifest`)
```bash
pureapk manifest application.apk
pureapk manifest application.apk --json
```

### List Declared Permissions (`permissions`)
```bash
pureapk permissions application.apk
```

### Inspect DEX Headers & Method Counts (`dex`)
```bash
pureapk dex application.apk
```

### List Archive Files (`files`)
```bash
pureapk files application.apk
```

### Verify Integrity & Signature (`verify`)
```bash
pureapk verify application.apk
```

### Extract APK Contents (`extract`)
```bash
pureapk extract application.apk -o output_dir/
```

### Pack Directory to APK (`pack`)
```bash
pureapk pack src_directory/ -o output.apk
```

---

## 🎮 First-Class Kivy & Pygame Toolchains

Package Kivy and Pygame applications into Android APKs on **any OS** (Windows 7/10/11, macOS, Linux) and **any Python version** without needing Linux VMs or 15 GB Android SDKs:

```bash
# Scaffold a new Kivy or Pygame mobile project
pureapk init-kivy my_kivy_app --title "Kivy Dashboard"
pureapk init-pygame my_pygame_app --title "Space Shooter"

# Package directly into APK (Debug or Store-Ready Release)
pureapk pack-kivy my_kivy_app -o dashboard.apk --release
pureapk pack-pygame my_pygame_app -o shooter.apk --release
```

---

## 🏬 Multi-Store Publishing (Google Play, Apple App Store, Microsoft Store)

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

## 🧪 Testing

The test suite achieves **100% test pass rate** across all Python implementations and operating systems:

```bash
# Run pytest with uv
uv run pytest tests/ -v

# Run with test coverage
uv run pytest --cov=pureapk tests/
```

Matrix tested environments:
- **CPython**: 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16
- **Free-Threaded (No-GIL)**: 3.13t, 3.14t, 3.15t, 3.16t
- **PyPy**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Operating Systems**: Windows, Linux, Apple macOS

---

## 📄 License

MIT License — Copyright (c) 2026 eminsk.
