# perfect-screenshotter

Capture **pixel-perfect screenshots of a specific window** (not the whole
screen) by window title. Uses the Win32 `PrintWindow` GDI path so it captures
the real window contents, including for layered and partially-occluded windows.

The capture backend uses the Win32 API, so **screenshots only work on Windows.**
The package itself imports and its path/filename logic is tested on
**Linux, macOS, and Windows via CI** — the platform-specific backend is loaded
lazily and fails with a clear message off-Windows.

## Install

### Linux / macOS

The capture backend is Windows-only, but you can still install the package and
run the test suite (the Win32 tests are skipped automatically):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`pywin32` is installed only on Windows (it is gated by an environment marker in
`requirements.txt`).

## Usage (Windows)

List visible windows:

```powershell
python screenshotter.py --list
```

Capture a window whose title contains "Notepad":

```powershell
python screenshotter.py --window "Notepad"
```

Save to a specific file, capture only the client area, and bring the window to
the front first:

```powershell
python screenshotter.py --window "Code" --client --foreground -o out.png
```

Options:

```
-l, --list         List all visible windows
-w, --window       Window title to search for (partial, case-insensitive)
-o, --output       Output file path (default: screenshots/<title>_<timestamp>.png)
-c, --client       Capture only the client area (no title bar/borders)
-f, --foreground   Bring the window to the foreground before capture
-a, --all          With --list, also show windows that have no title
```

By default, screenshots are written to `screenshots/<sanitized-title>_<timestamp>.png`.

## Testing

```bash
pip install -r requirements-dev.txt
pytest -q
```

The pure path/filename logic and the CLI are tested on every OS. On Windows, the
suite additionally drives the real Win32 capture end to end (enumerating
windows, capturing the largest visible window, and decoding the saved PNG). Off
Windows, those tests are skipped and the "requires Windows" error path is
asserted instead. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Requirements

- Python 3.11+
- Windows (for the capture backend) with `pywin32`
- `Pillow`, `psutil`
- See `requirements.txt`
