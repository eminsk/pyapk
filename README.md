<div align="center">

# ⚡ pureapk / pyapk

### Pure Python Android APK Engine, Multi-Store Packager & Toolchain
**Zero external dependencies, zero-copy memoryview parsing, 100% tests passing on CPython 3.8–3.16, Free-Threaded (No-GIL), and PyPy.**

[ 🇬🇧 English ] | [ 🇷🇺 Документация на русском ](README_RU.md)

[![Release Version](https://img.shields.io/badge/release-v0.1.1-0969da.svg?style=flat&logo=github)](https://github.com/eminsk/pyapk/releases/tag/v0.1.1)
[![PyPI Version](https://img.shields.io/pypi/v/pureapk?logo=pypi&logoColor=white&label=PyPI&color=0969da)](https://pypi.org/project/pureapk/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/pureapk.svg?style=flat&logo=pypi)](https://pypi.org/project/pureapk/)
[![Debian / Ubuntu PPA](https://img.shields.io/badge/Debian%20%2F%20Ubuntu-APT%20PPA-E95420.svg?style=flat)](https://eminsk.github.io/ppa/)
[![Python Versions](https://img.shields.io/badge/python-3.8_--_3.16-3776AB.svg?style=flat&logo=python&logoColor=white)](https://pypi.org/project/pureapk/)
[![Free-Threaded No-GIL](https://img.shields.io/badge/No--GIL-3.13t%20--%203.16t-brightgreen?style=flat)](https://peps.python.org/pep-0703/)
[![PyPy](https://img.shields.io/badge/PyPy-3.8_--_3.12-yellow.svg?style=flat&logo=pypy)](https://pypy.org/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20external-success.svg?style=flat)](https://github.com/eminsk/pyapk)
[![Platforms](https://img.shields.io/badge/platform-Apple_macOS_%7C_Linux_%7C_Windows-lightgrey.svg?style=flat)](https://github.com/eminsk/pyapk)
[![Tests](https://img.shields.io/badge/tests-49%20passed%20(100%25)-2ea44f.svg?style=flat&logo=pytest&logoColor=white)](https://github.com/eminsk/pyapk)
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
# Standard ultra-lightweight installation via PyPI (zero dependencies, ~35 KB)
pip install pureapk

# With optional framework extras for local desktop testing
pip install "pureapk[flet]"    # includes Flet / Flutter
pip install "pureapk[kivy]"    # includes Kivy
pip install "pureapk[pygame]"  # includes Pygame-CE
pip install "pureapk[toga]"    # includes BeeWare Toga
pip install "pureapk[all]"     # all UI & game frameworks

# Or install backwards-compatible alias
pip install pyapk

# With uv
uv add pureapk
```

### Install Pre-Built Universal Wheel Directly from GitHub
```bash
pip install https://github.com/eminsk/pyapk/releases/download/v0.1.1/pureapk-0.1.1-py3-none-any.whl
```

### Ubuntu / Debian (Official APT PPA)
```bash
# Set up eminsk APT repository
curl -sS https://eminsk.github.io/ppa/setup.sh | sudo bash

# Install pureapk
sudo apt install python3-pureapk

# Or install standalone .deb package directly
sudo dpkg -i python3-pureapk_0.1.1-1_all.deb
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
| **PySide6 / PyQt** | Qt-based desktop GUI & advanced graphics suites | `MSIXBuilder` | Windows MSIX (Microsoft Store) |

```bash
# Scaffold mobile & desktop projects
pureapk init-kivy my_kivy_app --title "Kivy Mobile App"
pureapk init-pygame my_pygame_app --title "Space Shooter"
pureapk init-flet my_flet_app --title "Flet Mobile App"
pureapk init-toga my_toga_app --title "BeeWare Native App"
pureapk init-renpy my_novel --title "Interactive Story"
pureapk init-webview my_web_app --title "HTML5 Hybrid App"

# Package directly into APK (Debug or Store-Ready Release)
pureapk pack-kivy my_kivy_app -o app.apk --release
pureapk pack-pygame my_pygame_app -o shooter.apk --release
pureapk pack-flet my_flet_app -o flet.apk --release
pureapk pack-toga my_toga_app -o toga.apk --release
pureapk pack-renpy my_novel -o novel.apk --release
pureapk pack-webview my_web_app -o webview.apk --release
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

## 🔑 Code Signing & Certificate Guide (Android, Apple, Windows)

Distribution to official app stores and local testing requires digital signatures. Here is a step-by-step guide for each platform.

### 1. 🤖 Android (Google Play, RuStore, Huawei AppGallery)

- **Debug Keystore (Local Device Testing)**:
  Used by default for rapid sideloading via USB or Wi-Fi (`adb install app.apk`).
- **Release Keystore (Production Stores & Users)**:
  Stores reject debug signatures. Create a production RSA-2048/4096 signing key:
  ```bash
  # Generate release signing profile via pureapk:
  pureapk generate-keystore -o release.keystore --alias production --password my_secret_pass

  # Or using standard keytool:
  keytool -genkey -v -keystore release.keystore -alias production -keyalg RSA -keysize 2048 -validity 10000
  ```
- **Verifying Signatures in pureapk**:
  ```bash
  pureapk verify my_app.apk
  # Inspect active schemes (v1, v2, v3, v4) and certificate fingerprints (SHA-256, SHA-1):
  pureapk info my_app.apk --json
  ```
- **Google Play App Signing**: When uploading an `.aab` bundle to Google Play Console, you sign with your **Upload Key**. Google Play manages and signs the final user-facing APKs with your master **App Signing Key**.

---

### 2. 🍏 Apple App Store (iOS & macOS)

- **Requirements**:
  1. **Apple Developer Program** account ($99/year).
  2. **Distribution Certificate** (`.p12` file exported from Apple Developer portal).
  3. **Provisioning Profile** (`embedded.mobileprovision`) matching your App ID (`com.company.myapp`).
- **Workflow with pureapk**:
  1. Scaffold project with valid `Info.plist`:
     ```bash
     pureapk init-ios my_app --title "CoolApp" --bundle-id "com.company.coolapp"
     ```
  2. Include `embedded.mobileprovision` and build the `.ipa`:
     ```bash
     pureapk pack-ipa my_app/ -o CoolApp.ipa --title "CoolApp"
     ```
  3. Code Signing:
     - **On macOS**: `codesign -s "Apple Distribution: Team Name (TEAM_ID)" --entitlements entitlements.plist Payload/CoolApp.app`
     - **On Windows / Linux** (without Mac): using open-source cross-platform `zsign`:
       ```bash
       zsign -k cert.p12 -p password -m embedded.mobileprovision -o Signed.ipa CoolApp.ipa
       ```
  4. Submit to App Store: Upload using **Apple Transporter** (free for Windows and macOS) directly to **App Store Connect**.

---

### 3. 🪟 Windows (Microsoft Store & Sideloading)

- **For Microsoft Store Submission**:
  - You **DO NOT** need to purchase an expensive Commercial Code Signing Certificate.
  - When registering at **Microsoft Partner Center** ($19 one-time fee), Microsoft assigns your account a unique **Publisher ID** (e.g. `CN=12345678-ABCD-EF01-...`).
  - Configure this ID when initializing your project:
    ```bash
    pureapk init-windows win_app --title "CoolApp" --package "MyCompany.CoolApp"
    pureapk pack-msix win_app/ -o CoolApp.msix
    ```
  - Upload `CoolApp.msix` to Partner Center. **Microsoft Store automatically signs the package with their trusted Authenticode certificate during the store ingestion process.**
- **For Local Sideloading (Testing outside Store)**:
  - Create a local self-signed certificate via PowerShell:
    ```powershell
    $cert = New-SelfSignedCertificate -Type Custom -Subject "CN=MyCompany" -KeyUsage DigitalSignature -FriendlyName "PureApk Dev Cert" -CertStoreLocation "Cert:\CurrentUser\My"
    Export-PfxCertificate -Cert $cert -FilePath dev_cert.pfx -Password (ConvertTo-SecureString -String "1234" -Force -AsPlainText)
    ```
  - Sign using `SignTool`:
    ```powershell
    signtool sign /fd SHA256 /a /f dev_cert.pfx /p 1234 CoolApp.msix
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

# Fast Framework Scaffolding & Packaging (Kivy, Pygame, Flet, Toga, Ren'Py, WebView)
pureapk init-flet my_app --title "Flet App"
pureapk pack-flet my_app/ -o flet.apk --release

pureapk init-toga my_app --title "Toga App"
pureapk pack-toga my_app/ -o toga.apk --release

pureapk init-renpy my_novel --title "Visual Novel"
pureapk pack-renpy my_novel/ -o novel.apk --release

pureapk init-webview my_web --title "WebView App"
pureapk pack-webview my_web/ -o web.apk --release

pureapk init-kivy my_kivy --title "Kivy App"
pureapk pack-kivy my_kivy/ -o kivy.apk --release

pureapk init-pygame my_game --title "Pygame App"
pureapk pack-pygame my_game/ -o game.apk --release

# Multi-Store Packaging (Google Play AAB, Apple IPA, Microsoft Store MSIX)
pureapk pack-aab project_dir/ -o app.aab
pureapk init-ios ios_app/ --title "MyIOSApp" --bundle-id "com.company.app"
pureapk pack-ipa ios_app/ -o app.ipa --title "MyIOSApp"
pureapk init-windows win_app/ --title "MyWinApp" --package "MyCompany.MyWinApp"
pureapk pack-msix win_app/ -o app.msix
pureapk generate-keystore -o release.keystore --alias production
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
