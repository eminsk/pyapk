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
    "flet": (
        "libflet.so",
        "io.flet",
        "flet",
    ),
    "beeware": (
        "org.beeware",
        "toga",
        "rubicon",
    ),
    "renpy": (
        "librenpy.so",
        ".rpy",
        ".rpyc",
        "renpy",
    ),
    "webview": (
        "android.webkit.WebView",
        "assets/index.html",
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
        release: bool = False,
    ) -> None:
        """Packs a Kivy project directory into a standard Android APK."""
        from pureapk.builder import APKBuilder
        from pureapk.stores import ReleaseHelper
        src = Path(source_dir)
        builder = APKBuilder(output_apk)
        manifest_path = src / "AndroidManifest.xml"
        if not manifest_path.exists():
            manifest_str = KivyAppHelper.generate_manifest_xml(package_name, app_title)
            if release:
                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)
            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))
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
        release: bool = False,
    ) -> None:
        """Packs a Pygame project directory into a standard Android APK."""
        from pureapk.builder import APKBuilder
        from pureapk.stores import ReleaseHelper
        src = Path(source_dir)
        builder = APKBuilder(output_apk)
        manifest_path = src / "AndroidManifest.xml"
        if not manifest_path.exists():
            manifest_str = PygameAppHelper.generate_manifest_xml(package_name, app_title)
            if release:
                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)
            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))
        builder.add_directory(src)
        builder.build()


class FletAppHelper:
    """Helper utilities and template generators for Flet (Flutter/Python) mobile applications."""

    __slots__ = ()

    @staticmethod
    def generate_manifest_xml(
        package_name: str,
        app_title: str,
        version_code: int = 1,
        version_name: str = "0.1",
        orientation: str = "sensor",
    ) -> str:
        return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}"
    android:versionCode="{version_code}"
    android:versionName="{version_name}">

    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />

    <application
        android:label="{app_title}"
        android:icon="@mipmap/ic_launcher"
        android:hardwareAccelerated="true">
        <activity
            android:name="io.flet.FletActivity"
            android:label="{app_title}"
            android:screenOrientation="{orientation}"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize"
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
    def init_project(target_dir: Union[str, Path], title: str = "Flet App") -> None:
        path = Path(target_dir)
        path.mkdir(parents=True, exist_ok=True)
        main_py = path / "main.py"
        if not main_py.exists():
            main_py.write_text(
                "import flet as ft\n\n"
                "def main(page: ft.Page):\n"
                f"    page.title = '{title}'\n"
                "    page.vertical_alignment = ft.MainAxisAlignment.CENTER\n"
                "    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER\n\n"
                "    txt_number = ft.TextField(value='0', text_align=ft.TextAlign.RIGHT, width=100)\n\n"
                "    def minus_click(e):\n"
                "        txt_number.value = str(int(txt_number.value) - 1)\n"
                "        page.update()\n\n"
                "    def plus_click(e):\n"
                "        txt_number.value = str(int(txt_number.value) + 1)\n"
                "        page.update()\n\n"
                "    page.add(\n"
                "        ft.Row(\n"
                "            [\n"
                "                ft.IconButton(ft.icons.REMOVE, on_click=minus_click),\n"
                "                txt_number,\n"
                "                ft.IconButton(ft.icons.ADD, on_click=plus_click),\n"
                "            ],\n"
                "            alignment=ft.MainAxisAlignment.CENTER,\n"
                "        )\n"
                "    )\n\n"
                "if __name__ == '__main__':\n"
                "    ft.app(target=main)\n",
                encoding="utf-8",
            )

    @staticmethod
    def pack_app(
        source_dir: Union[str, Path],
        output_apk: Union[str, Path],
        package_name: str = "com.flet.app",
        app_title: str = "Flet App",
        release: bool = False,
    ) -> None:
        from pureapk.builder import APKBuilder
        from pureapk.stores import ReleaseHelper
        src = Path(source_dir)
        builder = APKBuilder(output_apk)
        manifest_path = src / "AndroidManifest.xml"
        if not manifest_path.exists():
            manifest_str = FletAppHelper.generate_manifest_xml(package_name, app_title)
            if release:
                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)
            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))
        builder.add_directory(src)
        builder.build()


class TogaAppHelper:
    """Helper utilities and template generators for BeeWare Toga (native UI) applications."""

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

    <application
        android:label="{app_title}"
        android:icon="@mipmap/ic_launcher">
        <activity
            android:name="org.beeware.android.MainActivity"
            android:label="{app_title}"
            android:screenOrientation="{orientation}"
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
    def init_project(target_dir: Union[str, Path], title: str = "Toga App") -> None:
        path = Path(target_dir)
        path.mkdir(parents=True, exist_ok=True)
        app_py = path / "app.py"
        if not app_py.exists():
            app_py.write_text(
                "import toga\n"
                "from toga.style import Pack\n"
                "from toga.style.pack import COLUMN, ROW\n\n"
                f"def build(app):\n"
                "    box = toga.Box(style=Pack(direction=COLUMN, padding=20))\n"
                f"    label = toga.Label('Welcome to {title}!', style=Pack(padding=(0, 0, 10, 0)))\n"
                "    button = toga.Button('Click Me', on_press=lambda widget: app.main_window.info_dialog('Hello', 'Button pressed!'))\n"
                "    box.add(label)\n"
                "    box.add(button)\n"
                "    return box\n\n"
                "def main():\n"
                f"    return toga.App('{title}', 'org.beeware.app', startup=build)\n\n"
                "if __name__ == '__main__':\n"
                "    main().main_loop()\n",
                encoding="utf-8",
            )

    @staticmethod
    def pack_app(
        source_dir: Union[str, Path],
        output_apk: Union[str, Path],
        package_name: str = "org.beeware.app",
        app_title: str = "Toga App",
        release: bool = False,
    ) -> None:
        from pureapk.builder import APKBuilder
        from pureapk.stores import ReleaseHelper
        src = Path(source_dir)
        builder = APKBuilder(output_apk)
        manifest_path = src / "AndroidManifest.xml"
        if not manifest_path.exists():
            manifest_str = TogaAppHelper.generate_manifest_xml(package_name, app_title)
            if release:
                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)
            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))
        builder.add_directory(src)
        builder.build()


class RenPyAppHelper:
    """Helper utilities and template generators for Ren'Py visual novels."""

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
    def init_project(target_dir: Union[str, Path], title: str = "Visual Novel") -> None:
        path = Path(target_dir)
        game_dir = path / "game"
        game_dir.mkdir(parents=True, exist_ok=True)
        script_rpy = game_dir / "script.rpy"
        if not script_rpy.exists():
            script_rpy.write_text(
                "define e = Character('Eileen')\n\n"
                "label start:\n"
                f"    e 'Welcome to {title} on Android!'\n"
                "    e 'You created this game in pure Python without Android Studio.'\n"
                "    return\n",
                encoding="utf-8",
            )

    @staticmethod
    def pack_app(
        source_dir: Union[str, Path],
        output_apk: Union[str, Path],
        package_name: str = "org.renpy.game",
        app_title: str = "Visual Novel",
        release: bool = False,
    ) -> None:
        from pureapk.builder import APKBuilder
        from pureapk.stores import ReleaseHelper
        src = Path(source_dir)
        builder = APKBuilder(output_apk)
        manifest_path = src / "AndroidManifest.xml"
        if not manifest_path.exists():
            manifest_str = RenPyAppHelper.generate_manifest_xml(package_name, app_title)
            if release:
                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)
            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))
        builder.add_directory(src)
        builder.build()


class WebViewAppHelper:
    """Helper utilities and template generators for Python + HTML5/CSS/JS WebView applications."""

    __slots__ = ()

    @staticmethod
    def generate_manifest_xml(
        package_name: str,
        app_title: str,
        version_code: int = 1,
        version_name: str = "0.1",
        orientation: str = "sensor",
    ) -> str:
        return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}"
    android:versionCode="{version_code}"
    android:versionName="{version_name}">

    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />

    <application
        android:label="{app_title}"
        android:icon="@mipmap/ic_launcher"
        android:hardwareAccelerated="true">
        <activity
            android:name="android.webkit.WebViewActivity"
            android:label="{app_title}"
            android:screenOrientation="{orientation}"
            android:configChanges="orientation|screenSize"
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
    def init_project(target_dir: Union[str, Path], title: str = "WebView App") -> None:
        path = Path(target_dir)
        assets_dir = path / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        html_file = assets_dir / "index.html"
        if not html_file.exists():
            html_file.write_text(
                "<!DOCTYPE html>\n"
                "<html>\n"
                "<head>\n"
                "    <meta charset='utf-8'>\n"
                "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
                f"    <title>{title}</title>\n"
                "    <style>\n"
                "        body { font-family: system-ui, sans-serif; background: #121212; color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }\n"
                "        .card { background: #1e1e1e; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); text-align: center; }\n"
                "        button { background: #6200ee; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 6px; cursor: pointer; margin-top: 1rem; }\n"
                "    </style>\n"
                "</head>\n"
                "<body>\n"
                "    <div class='card'>\n"
                f"        <h1>{title}</h1>\n"
                "        <p>Ultra-lightweight Python WebView Mobile Application</p>\n"
                "        <button onclick='alert(\"Clicked from Mobile!\")'>Click Me</button>\n"
                "    </div>\n"
                "</body>\n"
                "</html>\n",
                encoding="utf-8",
            )
        main_py = path / "main.py"
        if not main_py.exists():
            main_py.write_text('#!/usr/bin/env python3\nprint("Running WebView backend...")\n', encoding="utf-8")

    @staticmethod
    def pack_app(
        source_dir: Union[str, Path],
        output_apk: Union[str, Path],
        package_name: str = "com.webview.app",
        app_title: str = "WebView App",
        release: bool = False,
    ) -> None:
        from pureapk.builder import APKBuilder
        from pureapk.stores import ReleaseHelper
        src = Path(source_dir)
        builder = APKBuilder(output_apk)
        manifest_path = src / "AndroidManifest.xml"
        if not manifest_path.exists():
            manifest_str = WebViewAppHelper.generate_manifest_xml(package_name, app_title)
            if release:
                manifest_str = ReleaseHelper.sanitize_manifest_for_release(manifest_str)
            builder.add_bytes("AndroidManifest.xml", manifest_str.encode("utf-8"))
        builder.add_directory(src)
        builder.build()
