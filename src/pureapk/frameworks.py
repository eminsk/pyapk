"""First-class support and templates for Kivy, Pygame, and Python-for-Android frameworks.

Provides framework detection, manifest generators, and project scaffolding.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

FRAMEWORK_SIGNATURES: Dict[str, Tuple[str, ...]] = {
    "kivy": (
        "libkivy.so",
        "org.kivy.android.PythonActivity",
        "org/kivy/android",
        ".kv",
    ),
    "pygame": (
        "libpygame.so",
        "org.renpy.android.PythonSDLActivity",
        "org.renpy.android",
        "pygame",
    ),
    "flutter": ("libflutter.so", "io.flutter.app.FlutterActivity"),
    "react-native": ("libreactnativejni.so", "com.facebook.react"),
    "unity": ("libunity.so", "com.unity3d.player"),
    "godot": ("libgodot_android.so", "org.godotengine.godot"),
}


class FrameworkDetector:
    """Detects mobile game/app frameworks inside APK archives."""

    __slots__ = ()

    @staticmethod
    def detect(filenames: Sequence[str], activities: Sequence[str]) -> str:
        files_lower = tuple(map(str.lower, filenames))
        acts_lower = tuple(map(str.lower, activities))

        def has_marker(marker: str) -> bool:
            m = marker.lower()
            return any(m in f for f in files_lower) or any(m in a for a in acts_lower)

        for fw, markers in FRAMEWORK_SIGNATURES.items():
            if any(map(has_marker, markers)):
                return fw

        # Check generic python
        if any("libpython" in f for f in files_lower):
            return "python"

        return "native"


class KivyAppHelper:
    """Helper utilities and template generators for Kivy Android applications."""

    __slots__ = ()

    @staticmethod
    def generate_manifest_xml(
        package_name: str,
        app_title: str,
        version_code: int = 1,
        version_name: str = "0.1",
        orientation: str = "portrait",
    ) -> str:
        return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}"
    android:versionCode="{version_code}"
    android:versionName="{version_name}">

    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    <uses-feature android:glEsVersion="0x00020000" android:required="true" />

    <application
        android:label="{app_title}"
        android:icon="@mipmap/ic_launcher"
        android:hardwareAccelerated="true">
        <activity
            android:name="org.kivy.android.PythonActivity"
            android:label="{app_title}"
            android:screenOrientation="{orientation}"
            android:configChanges="keyboard|keyboardHidden|orientation|screenSize"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""

    @staticmethod
    def generate_buildozer_spec(
        title: str = "Kivy App",
        package_name: str = "kivyapp",
        package_domain: str = "org.kivy",
        orientation: str = "portrait",
    ) -> str:
        return f"""[app]
title = {title}
package.name = {package_name}
package.domain = {package_domain}
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
version = 0.1
requirements = python3,kivy
orientation = {orientation}
android.minapi = 21
android.sdk = 34
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET
"""

    @staticmethod
    def init_project(target_dir: Union[str, Path], title: str = "Kivy App") -> None:
        path = Path(target_dir)
        path.mkdir(parents=True, exist_ok=True)
        main_py = path / "main.py"
        if not main_py.exists():
            main_py.write_text(
                "from kivy.app import App\n"
                "from kivy.uix.label import Label\n\n"
                "class MainApp(App):\n"
                "    def build(self):\n"
                f"        return Label(text='Hello from {title}!')\n\n"
                "if __name__ == '__main__':\n"
                "    MainApp().run()\n",
                encoding="utf-8",
            )
        spec = path / "buildozer.spec"
        if not spec.exists():
            spec.write_text(KivyAppHelper.generate_buildozer_spec(title=title), encoding="utf-8")

    @staticmethod
    def pack_app(
        source_dir: Union[str, Path],
        output_apk: Union[str, Path],
        package_name: str = "org.kivy.app",
        app_title: str = "Kivy App",
    ) -> None:
        """Packs a Kivy project directory into a standard Android APK."""
        from pureapk.builder import APKBuilder
        src = Path(source_dir)
        builder = APKBuilder(output_apk)
        manifest_path = src / "AndroidManifest.xml"
        if not manifest_path.exists():
            manifest_bytes = KivyAppHelper.generate_manifest_xml(package_name, app_title).encode("utf-8")
            builder.add_bytes("AndroidManifest.xml", manifest_bytes)
        builder.add_directory(src)
        builder.build()


class PygameAppHelper:
    """Helper utilities and template generators for Pygame Android applications."""

    __slots__ = ()

    @staticmethod
    def generate_manifest_xml(
        package_name: str,
        app_title: str,
        version_code: int = 1,
        version_name: str = "0.1",
        orientation: str = "landscape",
    ) -> str:
        return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}"
    android:versionCode="{version_code}"
    android:versionName="{version_name}">

    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.VIBRATE" />
    <uses-feature android:glEsVersion="0x00020000" android:required="true" />

    <application
        android:label="{app_title}"
        android:icon="@mipmap/ic_launcher"
        android:hardwareAccelerated="true">
        <activity
            android:name="org.renpy.android.PythonSDLActivity"
            android:label="{app_title}"
            android:screenOrientation="{orientation}"
            android:configChanges="keyboard|keyboardHidden|orientation|screenSize"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""

    @staticmethod
    def generate_buildozer_spec(
        title: str = "Pygame App",
        package_name: str = "pygameapp",
        package_domain: str = "org.pygame",
        orientation: str = "landscape",
    ) -> str:
        return f"""[app]
title = {title}
package.name = {package_name}
package.domain = {package_domain}
source.dir = .
source.include_exts = py,png,jpg,ogg,wav,mp3,ttf,json
version = 0.1
requirements = python3,pygame
orientation = {orientation}
android.minapi = 21
android.sdk = 34
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET,VIBRATE
"""

    @staticmethod
    def init_project(target_dir: Union[str, Path], title: str = "Pygame App") -> None:
        path = Path(target_dir)
        path.mkdir(parents=True, exist_ok=True)
        main_py = path / "main.py"
        if not main_py.exists():
            main_py.write_text(
                "import pygame\n"
                "import sys\n\n"
                "pygame.init()\n"
                "screen = pygame.display.set_mode((800, 600))\n"
                f"pygame.display.set_caption('{title}')\n"
                "clock = pygame.time.Clock()\n\n"
                "running = True\n"
                "while running:\n"
                "    for event in pygame.event.get():\n"
                "        if event.type == pygame.QUIT:\n"
                "            running = False\n"
                "    screen.fill((30, 30, 30))\n"
                "    pygame.display.flip()\n"
                "    clock.tick(60)\n"
                "pygame.quit()\n"
                "sys.exit()\n",
                encoding="utf-8",
            )
        spec = path / "buildozer.spec"
        if not spec.exists():
            spec.write_text(PygameAppHelper.generate_buildozer_spec(title=title), encoding="utf-8")

    @staticmethod
    def pack_app(
        source_dir: Union[str, Path],
        output_apk: Union[str, Path],
        package_name: str = "org.pygame.app",
        app_title: str = "Pygame App",
    ) -> None:
        """Packs a Pygame project directory into a standard Android APK."""
        from pureapk.builder import APKBuilder
        src = Path(source_dir)
        builder = APKBuilder(output_apk)
        manifest_path = src / "AndroidManifest.xml"
        if not manifest_path.exists():
            manifest_bytes = PygameAppHelper.generate_manifest_xml(package_name, app_title).encode("utf-8")
            builder.add_bytes("AndroidManifest.xml", manifest_bytes)
        builder.add_directory(src)
        builder.build()
