"""Built-in crash diagnostics and remote telemetry for pureapk mobile applications.

100% standard library, zero external dependencies.
Automatically captures:
- System and device diagnostics (Android release, SDK, ABIs, machine, Python)
- Unhandled exceptions via sys.excepthook and Kivy ExceptionManager
- Framework logger streams (Kivy, Pygame)
- Writes crash reports to /sdcard/Download/<app>_crash.log and local app storage
- Uploads events to Webhook.site or private telemetry collector
- Provides on-screen emergency UI fallback for Kivy and mobile apps
"""

from __future__ import annotations

import atexit
import json
import logging
import os
from pathlib import Path
import platform
import queue
import ssl
import sys
import threading
import time
import traceback
from typing import Any, Callable, Dict, List, Optional
import urllib.request

IS_ANDROID = "ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ

try:
    _SSL_CTX = ssl._create_unverified_context()
except Exception:
    _SSL_CTX = None


def get_device_info() -> Dict[str, Any]:
    """Collects runtime device and environment metadata."""
    active_inst = getattr(CrashReporter, "_active_instance", None)
    sess_id = getattr(active_inst, "session_id", time.strftime("%Y%m%d_%H%M%S"))
    info: Dict[str, Any] = {
        "platform": sys.platform,
        "python": platform.python_version(),
        "machine": platform.machine(),
        "is_android": IS_ANDROID,
        "session": sess_id,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if IS_ANDROID:
        try:
            import jnius
            from jnius import autoclass

            build = autoclass("android.os.Build")
            ver = autoclass("android.os.Build$VERSION")
            info.update(
                manufacturer=str(getattr(build, "MANUFACTURER", "unknown")),
                model=str(getattr(build, "MODEL", "unknown")),
                android=str(getattr(ver, "RELEASE", "unknown")),
                sdk=int(getattr(ver, "SDK_INT", 0)),
                abis=[str(a) for a in getattr(build, "SUPPORTED_ABIS", [])],
            )
        except Exception as exc:
            info["android_info_error"] = str(exc)
    return info


class CrashReporter:
    """Manages local crash dumps and optional remote webhook telemetry."""

    _instance: Optional["CrashReporter"] = None

    def __init__(
        self,
        app_name: str = "app",
        webhook_url: Optional[str] = None,
        secondary_url: Optional[str] = None,
        auto_hook_kivy: bool = True,
    ) -> None:
        self.app_name = app_name
        self.webhook_url = webhook_url or os.environ.get("PUREAPK_TELEMETRY_URL")
        self.secondary_url = secondary_url or os.environ.get("PUREAPK_SECONDARY_URL")
        self.auto_hook_kivy = auto_hook_kivy
        self.log_paths: List[str] = []
        self._queue: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=3000)
        self._session = time.strftime("%Y%m%d-%H%M%S")
        self._started = False
        self._device_cache: Dict[str, Any] = {}
        self._orig_excepthook = sys.excepthook

    @classmethod
    def get_instance(cls) -> "CrashReporter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _setup_paths(self) -> None:
        paths = []
        if IS_ANDROID:
            for env in ("ANDROID_PRIVATE", "ANDROID_ARGUMENT", "ANDROID_APP_PATH"):
                base = os.environ.get(env)
                if base:
                    paths.append(os.path.join(base, f"{self.app_name}_debug.log"))
                    paths.append(os.path.join(base, "last_crash.txt"))
            paths.append(f"/sdcard/Download/{self.app_name}_crash.log")
            paths.append(f"/storage/emulated/0/Download/{self.app_name}_crash.log")
        else:
            paths.append(f"{self.app_name}_debug.log")
            paths.append(f"{self.app_name}_last_crash.txt")

        seen = set()
        cleaned = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                cleaned.append(p)
                try:
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                except Exception:
                    pass
        self.log_paths = cleaned

    def _send_http(self, url: str, payload_bytes: bytes, timeout: float) -> bool:
        try:
            req = urllib.request.Request(
                url,
                data=payload_bytes,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "User-Agent": f"pureapk-telemetry/{self.app_name}",
                },
            )
            kwargs: Dict[str, Any] = {"timeout": timeout}
            if url.startswith("https://") and _SSL_CTX is not None:
                kwargs["context"] = _SSL_CTX
            with urllib.request.urlopen(req, **kwargs) as resp:
                resp.read()
            return True
        except Exception:
            return False

    def _post(self, item: Dict[str, Any], timeout: float = 3.0) -> bool:
        try:
            payload = json.dumps(item, ensure_ascii=False).encode("utf-8")
        except Exception:
            return False

        success = False
        if self.webhook_url:
            if self._send_http(self.webhook_url, payload, timeout=timeout):
                success = True
        if self.secondary_url:
            if self._send_http(self.secondary_url, payload, timeout=min(timeout, 2.0)):
                success = True
        return success

    def _worker(self) -> None:
        while True:
            try:
                item = self._queue.get()
                self._post(item, timeout=3.5)
                self._queue.task_done()
            except Exception:
                pass

    def _write_local(self, item: Dict[str, Any]) -> None:
        line = f"[{item.get('time')}] [{item.get('level')}] {item.get('msg')}\n"
        if item.get("extra") and "traceback" in item["extra"]:
            line += f"--- TRACEBACK ---\n{item['extra']['traceback']}\n-----------------\n"

        for p in self.log_paths:
            try:
                with open(p, "a", encoding="utf-8") as fh:
                    fh.write(line)
            except Exception:
                pass

    def emit(self, level: str, msg: str, **extra: Any) -> None:
        """Asynchronously dispatches a log or telemetry event."""
        if not self._device_cache:
            self._device_cache = get_device_info()
        item = {
            "time": time.strftime("%H:%M:%S"),
            "level": level.upper(),
            "msg": msg,
            "device": self._device_cache,
            "extra": extra,
        }
        self._write_local(item)
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            pass

    def emit_sync(self, level: str, msg: str, timeout: float = 3.5, **extra: Any) -> bool:
        """Synchronously delivers critical errors and crash logs."""
        if not self._device_cache:
            self._device_cache = get_device_info()
        item = {
            "time": time.strftime("%H:%M:%S"),
            "level": level.upper(),
            "msg": msg,
            "device": self._device_cache,
            "extra": extra,
        }
        self._write_local(item)
        return self._post(item, timeout=timeout)

    def fatal(self, exc_type: Any, exc_val: Any, exc_tb: Any, where: str = "") -> None:
        """Logs a fatal unhandled exception to disk and remote telemetry."""
        tb = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        try:
            sys.__stderr__.write(f"\n[pureapk FATAL {where}]\n{tb}\n")
        except Exception:
            pass

        self.emit_sync("CRITICAL", f"FATAL CRASH {where}:\n{tb}", traceback=tb, timeout=4.0)

        for p in self.log_paths:
            try:
                crash_file = p.replace(".log", "_last_crash.txt") if p.endswith(".log") else p
                with open(crash_file, "w", encoding="utf-8") as fh:
                    fh.write(f"PUREAPK CRASH AT {time.ctime()}\nLocation: {where}\n\n{tb}\n")
            except Exception:
                pass

    def _global_excepthook(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.fatal(exc_type, exc_val, exc_tb, where="(sys.excepthook)")
        if self._orig_excepthook:
            try:
                self._orig_excepthook(exc_type, exc_val, exc_tb)
            except Exception:
                pass

    def hook_kivy(self) -> None:
        """Hooks Kivy's Logger and ExceptionManager if Kivy is present."""
        try:
            from kivy.logger import Logger

            class _KivyHandler(logging.Handler):
                def emit(_self, record):
                    try:
                        self.emit(record.levelname, f"[Kivy] {_self.format(record)}")
                    except Exception:
                        pass

            h = _KivyHandler()
            h.setFormatter(logging.Formatter("%(message)s"))
            Logger.addHandler(h)
        except Exception:
            pass

        try:
            from kivy.base import ExceptionHandler, ExceptionManager

            class _KivyLoopHandler(ExceptionHandler):
                def handle_exception(_self, inst):
                    tb = traceback.format_exc()
                    self.emit("CRITICAL", f"Kivy EventLoop Exception:\n{tb}", traceback=tb)
                    return ExceptionManager.PASS

            ExceptionManager.add_handler(_KivyLoopHandler())
        except Exception:
            pass

    def start(self) -> None:
        """Initializes logging paths, worker thread, and crash handlers."""
        if self._started:
            return
        self._started = True

        self._setup_paths()
        sys.excepthook = self._global_excepthook

        th = threading.Thread(target=self._worker, name="PureAPKTeleWorker", daemon=True)
        th.start()

        if self.auto_hook_kivy:
            self.hook_kivy()

        self.emit(
            "INFO",
            f"🚀 pureapk diagnostics initialized for '{self.app_name}' (session {self._session})",
            log_paths=self.log_paths,
            webhook=self.webhook_url,
        )

        atexit.register(lambda: self.emit_sync("INFO", "Process exiting cleanly (atexit)", timeout=1.0))


def setup_crash_reporter(
    app_name: str = "app",
    webhook_url: Optional[str] = None,
    secondary_url: Optional[str] = None,
) -> CrashReporter:
    """Convenience helper to start crash reporting and telemetry."""
    reporter = CrashReporter(app_name=app_name, webhook_url=webhook_url, secondary_url=secondary_url)
    CrashReporter._instance = reporter
    reporter.start()
    return reporter


def make_kivy_emergency_screen(err_text: str, app_title: str = "Application") -> Any:
    """Creates a responsive Kivy widget displaying traceback when build() crashes."""
    try:
        from kivy.core.clipboard import Clipboard
        from kivy.metrics import dp
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        from kivy.uix.textinput import TextInput

        layout = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        lbl_head = Label(
            text=f"⚠️ {app_title}: Ошибка запуска",
            font_size="15sp",
            bold=True,
            color=[1.0, 0.35, 0.35, 1],
            size_hint_y=None,
            height=dp(36),
        )
        layout.add_widget(lbl_head)

        txt = TextInput(
            text=err_text,
            readonly=True,
            font_size="11sp",
            foreground_color=[1, 0.9, 0.9, 1],
            background_color=[0.08, 0.05, 0.05, 1],
            size_hint_y=1,
        )
        layout.add_widget(txt)

        btn_copy = Button(
            text="📋 Скопировать лог ошибки",
            font_size="13sp",
            bold=True,
            size_hint_y=None,
            height=dp(46),
            background_normal="",
            background_color=[0.0, 0.824, 0.416, 1],
            color=[0.03, 0.05, 0.08, 1],
        )

        def _do_copy(*_):
            try:
                Clipboard.copy(err_text)
                btn_copy.text = "✓ Скопировано в буфер обмена!"
            except Exception as e:
                btn_copy.text = f"Ошибка: {e}"

        btn_copy.bind(on_release=_do_copy)
        layout.add_widget(btn_copy)
        return layout
    except Exception:
        return None


# Convenience module-level aliases and functions
device_info = get_device_info


def start(app_name: str = "Application") -> CrashReporter:
    """Convenience module-level initializer."""
    return setup_crash_reporter(app_name=app_name)


def emit(level: str, msg: str, **extra: Any) -> None:
    """Convenience module-level logger."""
    CrashReporter.get_instance().emit(level, msg, **extra)


def fatal(exc_type: Any, exc_val: Any, exc_tb: Any, where: str = "") -> None:
    """Convenience module-level fatal crash reporter."""
    CrashReporter.get_instance().fatal(exc_type, exc_val, exc_tb, where=where)


def hook_kivy_logger() -> None:
    """Convenience module-level Kivy hook."""
    CrashReporter.get_instance().hook_kivy()


