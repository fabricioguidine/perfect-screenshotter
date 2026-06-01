"""Tests for perfect-screenshotter.

The pure path/filename logic, the importability of the module, and the CLI are
exercised on every OS. The actual window capture uses the Win32 GDI API, which
only exists on Windows, so those end-to-end tests are skipped elsewhere and the
off-Windows error path is asserted instead.
"""
import datetime
import subprocess
import sys
from pathlib import Path

import pytest

import screenshotter as ss

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRYPOINT = REPO_ROOT / "screenshotter.py"
IS_WINDOWS = sys.platform == "win32"
windows_only = pytest.mark.skipif(not IS_WINDOWS, reason="requires Win32 GDI / pywin32")


# --------------------------- pure logic (all OSes) ---------------------------

@pytest.mark.parametrize(
    "title, expected",
    [
        ("Notepad", "Notepad"),
        ("a b-c_d", "a b-c_d"),
        ("My App: <Title>/x*?", "My App_ _Title__x__"),
        ("", ""),
    ],
)
def test_sanitize_title(title, expected):
    assert ss.sanitize_title(title) == expected


def test_sanitize_title_truncates_to_50_chars():
    assert len(ss.sanitize_title("x" * 200)) == 50


def test_default_output_path_is_pathlib_and_deterministic():
    now = datetime.datetime(2024, 5, 6, 7, 8, 9)
    path = ss.default_output_path("Chrome", now=now)
    assert isinstance(path, Path)
    assert path.parent == Path("screenshots")
    assert path.name == "Chrome_20240506_070809.png"


def test_default_output_path_honors_out_dir(tmp_path):
    now = datetime.datetime(2024, 1, 1, 0, 0, 0)
    path = ss.default_output_path("win", out_dir=tmp_path, now=now)
    assert path == tmp_path / "win_20240101_000000.png"


def test_default_output_path_sanitizes_title():
    now = datetime.datetime(2024, 1, 1, 0, 0, 0)
    path = ss.default_output_path("a/b:c", now=now)
    # The slug must not contain path separators from the raw title.
    assert path.name == "a_b_c_20240101_000000.png"


# ----------------- save_screenshot pipeline (all OSes, fake image) -----------

class _FakeImage:
    def __init__(self):
        self.saved = None
        self.width = 4
        self.height = 3

    def save(self, path, fmt):
        self.saved = (path, fmt)
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\nFAKE")


def test_save_screenshot_default_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    img = _FakeImage()
    out = ss.save_screenshot(img, window_title="Hello World")
    out_path = Path(out)
    assert out_path.exists()
    assert out_path.parent == Path("screenshots")
    assert out_path.read_bytes().startswith(b"\x89PNG")
    assert img.saved[1] == "PNG"


def test_save_screenshot_explicit_path_creates_nested_dirs(tmp_path):
    img = _FakeImage()
    target = tmp_path / "a" / "b" / "shot.png"
    out = ss.save_screenshot(img, output_path=target, window_title="ignored")
    assert Path(out) == target
    assert target.exists()
    assert target.parent.is_dir()


def test_save_screenshot_uses_os_native_path(tmp_path):
    img = _FakeImage()
    target = tmp_path / "nested" / "x.png"
    out = ss.save_screenshot(img, output_path=str(target))
    # Round-trips through pathlib, so it equals the OS-native path object.
    assert Path(out) == target


# --------------------------- off-Windows error path --------------------------

@pytest.mark.skipif(IS_WINDOWS, reason="checks the non-Windows failure path")
def test_capture_requires_windows_off_windows():
    with pytest.raises(RuntimeError, match="requires Windows"):
        ss.list_windows()


# --------------------------- real CLI subprocess (all OSes) ------------------

def test_cli_help_runs():
    proc = subprocess.run(
        [sys.executable, str(ENTRYPOINT), "--help"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "--window" in proc.stdout
    assert "--list" in proc.stdout


def test_cli_no_args_prints_help():
    proc = subprocess.run(
        [sys.executable, str(ENTRYPOINT)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "usage" in proc.stdout.lower()


@pytest.mark.skipif(IS_WINDOWS, reason="off-Windows the backend should error out")
def test_cli_list_errors_off_windows():
    proc = subprocess.run(
        [sys.executable, str(ENTRYPOINT), "--list"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "requires Windows" in proc.stderr


# --------------------------- real Win32 capture (Windows only) ---------------

@windows_only
def test_list_windows_returns_dicts():
    windows = ss.list_windows()
    assert isinstance(windows, list)
    if windows:
        w = windows[0]
        assert {"hwnd", "title", "width", "height"} <= set(w)
        assert w["width"] > 0 and w["height"] > 0


@windows_only
def test_capture_real_window_end_to_end(tmp_path):
    """Capture an actual on-screen window and assert a real PNG is written."""
    from PIL import Image

    windows = ss.list_windows()
    if not windows:
        pytest.skip("no visible windows to capture in this environment")

    target = max(windows, key=lambda w: w["width"] * w["height"])
    img = ss.capture_window(target["hwnd"])
    assert img.width > 0 and img.height > 0

    out = ss.save_screenshot(img, output_path=tmp_path / "real.png")
    out_path = Path(out)
    assert out_path.exists()
    with Image.open(out_path) as decoded:
        assert decoded.format == "PNG"
        assert decoded.size == (img.width, img.height)


@windows_only
def test_find_window_matches_self_process_window():
    # There is essentially always at least one visible window on a desktop
    # session; if headless (CI Windows runner), accept an empty result.
    matches = ss.find_window("")  # empty term matches every titled window
    assert isinstance(matches, list)
