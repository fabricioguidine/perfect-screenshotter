"""
Perfect Screenshotter - Capture pixel-perfect screenshots of specific windows.

Window capture uses the Win32 GDI API and therefore only runs on Windows. The
module still imports cleanly on any platform so the filename/path helpers can be
reused and tested; the Win32 backend is loaded lazily on first use.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Prefer UTF-8 for window titles with non-ASCII characters. reconfigure is
# guarded for streams that don't support it.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _load_win32():
    """Import the Win32 backend, failing with a clear, OS-specific message."""
    try:
        import ctypes

        import win32con
        import win32gui
        import win32process
        import win32ui
        from PIL import Image
    except ImportError as exc:  # off-Windows: pywin32 is unavailable
        raise RuntimeError(
            "Window capture requires Windows with pywin32 and Pillow installed."
        ) from exc

    # Enable DPI awareness for accurate window dimensions.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # Fallback
        except Exception:
            pass

    return ctypes, win32gui, win32ui, win32con, win32process, Image


def sanitize_title(window_title):
    """Turn a window title into a safe filename stem (<=50 chars)."""
    return "".join(
        c if c.isalnum() or c in " -_" else "_" for c in window_title
    )[:50]


def default_output_path(window_title, out_dir="screenshots", now=None):
    """Build the default timestamped output path for a capture."""
    now = now or datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    return Path(out_dir) / f"{sanitize_title(window_title)}_{timestamp}.png"


def get_process_name(hwnd):
    """Get the process name for a window handle."""
    try:
        import psutil

        win32process = _load_win32()[4]
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return psutil.Process(pid).name()
    except Exception:
        return "Unknown"


def list_windows(show_all=False):
    """List all visible windows with their titles and handles."""
    _, win32gui, _, _, _, _ = _load_win32()
    windows = []

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title or show_all:
                rect = win32gui.GetWindowRect(hwnd)
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                if width > 0 and height > 0:  # Only windows with size
                    windows.append({
                        'hwnd': hwnd,
                        'title': title if title else "(No Title)",
                        'width': width,
                        'height': height
                    })
        return True

    win32gui.EnumWindows(enum_callback, None)
    return windows


def find_window(search_term):
    """Find a window by partial title match (case-insensitive)."""
    windows = list_windows()
    search_lower = search_term.lower()

    matches = []
    for w in windows:
        if search_lower in w['title'].lower():
            matches.append(w)

    return matches


def capture_window(hwnd, client_only=False):
    """
    Capture a pixel-perfect screenshot of a window.

    Args:
        hwnd: Window handle
        client_only: If True, capture only the client area (no title bar/borders)

    Returns:
        PIL Image object
    """
    ctypes, win32gui, win32ui, win32con, _, Image = _load_win32()

    if client_only:
        # Get client area dimensions
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        width = right - left
        height = bottom - top

        # Convert client coordinates to screen coordinates
        point = win32gui.ClientToScreen(hwnd, (left, top))
        left, top = point
    else:
        # Get full window dimensions including borders and title bar
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

    # Create device contexts
    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()

    # Create bitmap
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(bitmap)

    # Use PrintWindow for accurate capture (handles layered windows)
    # PW_RENDERFULLCONTENT = 2 for better capture of modern apps
    if client_only:
        result = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 1)  # PW_CLIENTONLY
    else:
        result = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)  # PW_RENDERFULLCONTENT

    # If PrintWindow failed, try BitBlt as fallback
    if not result:
        save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

    # Convert to PIL Image
    bmp_info = bitmap.GetInfo()
    bmp_bits = bitmap.GetBitmapBits(True)

    img = Image.frombuffer(
        'RGB',
        (bmp_info['bmWidth'], bmp_info['bmHeight']),
        bmp_bits,
        'raw',
        'BGRX',
        0,
        1
    )

    # Cleanup
    win32gui.DeleteObject(bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)

    return img


def bring_window_to_front(hwnd):
    """Bring a window to the foreground."""
    _, win32gui, _, win32con, _, _ = _load_win32()
    try:
        # Restore if minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def save_screenshot(img, output_path=None, window_title="screenshot"):
    """Save the screenshot to a file."""
    if output_path is None:
        output_path = default_output_path(window_title)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Capture pixel-perfect screenshots of specific windows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                    List all visible windows
  %(prog)s --window "Notepad"        Screenshot window containing "Notepad"
  %(prog)s --window "Chrome" -o out.png  Save to specific file
  %(prog)s --window "Code" --client  Capture only client area (no borders)
        """
    )

    parser.add_argument('-l', '--list', action='store_true',
                        help='List all visible windows')
    parser.add_argument('-w', '--window', type=str,
                        help='Window title to search for (partial match)')
    parser.add_argument('-o', '--output', type=str,
                        help='Output file path (default: screenshots/<title>_<timestamp>.png)')
    parser.add_argument('-c', '--client', action='store_true',
                        help='Capture only client area (exclude title bar and borders)')
    parser.add_argument('-f', '--foreground', action='store_true',
                        help='Bring window to foreground before capture')
    parser.add_argument('-a', '--all', action='store_true',
                        help='With --list, show windows without titles too')

    args = parser.parse_args()

    if args.list:
        windows = list_windows(show_all=args.all)
        if not windows:
            print("No visible windows found.")
            return

        print(f"\n{'Handle':<12} {'Size':<15} {'Title'}")
        print("-" * 70)
        for w in sorted(windows, key=lambda x: x['title'].lower()):
            size = f"{w['width']}x{w['height']}"
            print(f"{w['hwnd']:<12} {size:<15} {w['title'][:50]}")
        print(f"\nTotal: {len(windows)} windows")
        return

    if args.window:
        matches = find_window(args.window)

        if not matches:
            print(f"No window found matching '{args.window}'")
            print("Use --list to see all available windows.")
            sys.exit(1)

        if len(matches) > 1:
            print(f"Multiple windows match '{args.window}':")
            for i, w in enumerate(matches, 1):
                print(f"  {i}. [{w['hwnd']}] {w['title']} ({w['width']}x{w['height']})")

            try:
                choice = input("\nEnter number to capture (or 'q' to quit): ").strip()
                if choice.lower() == 'q':
                    return
                idx = int(choice) - 1
                if 0 <= idx < len(matches):
                    target = matches[idx]
                else:
                    print("Invalid selection.")
                    sys.exit(1)
            except (ValueError, KeyboardInterrupt):
                print("\nCancelled.")
                sys.exit(1)
        else:
            target = matches[0]

        print(f"Capturing: {target['title']} ({target['width']}x{target['height']})")

        if args.foreground:
            bring_window_to_front(target['hwnd'])
            import time
            time.sleep(0.2)  # Brief delay for window to fully appear

        img = capture_window(target['hwnd'], client_only=args.client)
        output_path = save_screenshot(img, args.output, target['title'])

        print(f"Screenshot saved: {output_path}")
        print(f"Image size: {img.width}x{img.height} pixels")
        return

    # No arguments provided - show help
    parser.print_help()


if __name__ == "__main__":
    main()
