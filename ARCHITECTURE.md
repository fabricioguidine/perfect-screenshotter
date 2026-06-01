# Architecture

`perfect-screenshotter` is a single-file command-line tool
(`screenshotter.py`) that captures a pixel-perfect PNG of a specific window,
selected by a partial title match, using the Win32 GDI `PrintWindow` API.

## Components

- **`main()`** — CLI entrypoint (`argparse`). Modes:
  - `--list` / `--all`: enumerate visible windows.
  - `--window <term>`: find matching window(s), optionally bring to front
    (`--foreground`), capture (`--client` for client-area only), and save
    (`-o/--output`).
- **`sanitize_title(title)`** — pure helper; turns a window title into a safe
  filename stem (alnum / space / `-` / `_` kept, others -> `_`, capped at 50
  chars).
- **`default_output_path(title, out_dir, now)`** — pure helper; builds the
  default `<out_dir>/<stem>_<YYYYMMDD_HHMMSS>.png` path with `pathlib`.
- **`save_screenshot(img, output_path, title)`** — creates the parent directory
  and writes the PNG; defaults to `default_output_path` when no path is given.
- **`_load_win32()`** — lazily imports the Win32 backend (`ctypes`,
  `win32gui/ui/con/process`, `PIL.Image`), sets DPI awareness, and raises a
  clear `RuntimeError` when the backend is unavailable (i.e. off-Windows).
- **`list_windows()` / `find_window()`** — enumerate and filter visible,
  sized windows via `win32gui.EnumWindows`.
- **`capture_window(hwnd, client_only)`** — the actual GDI capture: create a
  compatible DC and bitmap, `PrintWindow` (with a `BitBlt` fallback), convert
  the `BGRX` bitmap bits into a PIL `RGB` image, and clean up all GDI handles.
- **`bring_window_to_front(hwnd)`** — restore-if-minimized + set foreground.
- **`get_process_name(hwnd)`** — owning process name via `win32process` +
  `psutil`.

## Data flow

```
argv -> main()
          |-- list:    list_windows() -> print table
          '-- window:  find_window(term)
                         |-- [optional] bring_window_to_front(hwnd)
                         |-- capture_window(hwnd, client_only)  (Win32 GDI -> PIL Image)
                         '-- save_screenshot(img, output, title)
                               '-- default_output_path()/sanitize_title()  (pathlib)
                             -> PNG on disk
```

## Cross-platform strategy

The capture itself is inherently Windows-only: it relies on window handles
(`HWND`), device contexts, `PrintWindow`, and `ctypes.windll`, none of which
exist on Linux/macOS. Rather than pretend otherwise, the design makes the
Windows dependency explicit and isolates it:

- **Lazy backend import.** All `win32*`/`ctypes.windll`/`PIL` usage is funneled
  through `_load_win32()`, which is only called inside the capture functions. The
  module therefore **imports cleanly on any OS**, so the pure helpers can be
  imported and unit-tested everywhere, and tooling (linters, CI) runs on Linux.
- **Clear failure off-Windows.** When the backend can't be imported,
  `_load_win32()` raises `RuntimeError("Window capture requires Windows ...")`
  instead of a cryptic `ImportError`/`AttributeError`.
- **Platform-gated dependency.** `requirements.txt` installs `pywin32` only on
  `sys_platform == "win32"`, so `pip install -r requirements.txt` succeeds on
  Linux/macOS CI runners.
- **`pathlib` paths and UTF-8.** Output paths are built with `pathlib` (no
  hardcoded separators), and stdout/stderr are reconfigured to UTF-8 (guarded)
  so non-ASCII window titles print correctly regardless of console code page.

## Testing strategy

The CI matrix is `ubuntu`/`macos`/`windows` x Python `3.11`/`3.12`/`3.13`.

- **All OSes:** `sanitize_title`, `default_output_path` (asserting `pathlib`
  output and OS-native joins), the `save_screenshot` pipeline with a fake image,
  and the real CLI via `subprocess` (`--help`, no-args help). Off Windows, the
  `RuntimeError` capture path is asserted (both as a direct call and via the
  CLI's `--list`).
- **Windows only:** the real Win32 path — `list_windows()` shape,
  `find_window()`, and `capture_window()` of the largest visible window with the
  saved PNG decoded and size-checked via Pillow. These are skipped off Windows.

All tests are hermetic (writes go under pytest's `tmp_path`) and require no
network.
