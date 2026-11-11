"""Tests for pureapk.telemetry crash diagnostics and reporting."""

import os
from pathlib import Path
import pytest

from pureapk.telemetry import (
    CrashReporter,
    get_device_info,
    setup_crash_reporter,
    make_kivy_emergency_screen,
)


def test_device_info():
    info = get_device_info()
    assert "platform" in info
    assert "python" in info
    assert "machine" in info
    assert "time" in info


def test_crash_reporter_instance(tmp_path):
    reporter = CrashReporter(app_name="testapp", webhook_url=None, auto_hook_kivy=False)
    test_log = tmp_path / "test_debug.log"
    reporter.log_paths = [str(test_log)]

    reporter.emit("INFO", "Test event 123", extra_val=42)
    assert test_log.exists()
    content = test_log.read_text(encoding="utf-8")
    assert "Test event 123" in content
    assert "INFO" in content

    # Test fatal logging
    try:
        raise ValueError("Simulated fatal crash")
    except ValueError as e:
        import sys
        reporter.fatal(*sys.exc_info(), where="in test_telemetry")

    crash_log = tmp_path / "test_debug_last_crash.txt"
    assert crash_log.exists()
    crash_content = crash_log.read_text(encoding="utf-8")
    assert "Simulated fatal crash" in crash_content
    assert "in test_telemetry" in crash_content


def test_setup_crash_reporter():
    rep = setup_crash_reporter("myquickapp")
    assert rep.app_name == "myquickapp"
    assert CrashReporter.get_instance() is rep
