# perfect-screenshotter

A tiny Windows command-line utility that captures a pixel-perfect screenshot of a single window matched by partial title. It uses the Win32 `PrintWindow` API for accurate capture even when the window is occluded or layered, and is DPI-aware so dimensions match the real on-screen pixels.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org) [![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](#)

## Features

- List visible windows with handle, size, and title.
- Match a window by case-insensitive partial title, with interactive selection when several match.
- Capture the full window or only the client area (no title bar or borders).
- Optionally bring the window to the foreground before capturing.
- Save as PNG to a chosen path, or auto-name as `screenshots/<title>_<timestamp>.png`.

## Installation

Requires Windows and Python 3.8+.

```powershell
git clone https://github.com/fabricioguidine/perfect-screenshotter.git
cd perfect-screenshotter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

```powershell
# List all visible windows (add --all to include untitled windows)
python screenshotter.py --list

# Capture a window whose title contains "Notepad"
python screenshotter.py --window "Notepad"

# Save to a specific file
python screenshotter.py --window "Chrome" -o out.png

# Capture only the client area (no title bar or borders)
python screenshotter.py --window "Code" --client

# Bring the window to the foreground before capturing
python screenshotter.py --window "Notepad" --foreground
```

| Flag | Short | Description |
| --- | --- | --- |
| `--list` | `-l` | List all visible windows |
| `--window TERM` | `-w` | Window title to search for (partial match) |
| `--output PATH` | `-o` | Output file path (default: `screenshots/<title>_<timestamp>.png`) |
| `--client` | `-c` | Capture only the client area (exclude title bar and borders) |
| `--foreground` | `-f` | Bring the window to the foreground before capture |
| `--all` | `-a` | With `--list`, also show windows that have no title |

## License

[MIT](LICENSE)
