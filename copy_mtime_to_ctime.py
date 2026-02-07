#!/usr/bin/env python3
"""
Copy a file's modification time to its creation time.

Useful when files are created with a wrong creation date (e.g. after copy/export)
and you want creation time to match modification time. Supports single files or
recursive directory scanning.

Platform support:
- Windows: Sets creation time via Win32 API.
- macOS: Sets creation time via SetFile (requires Xcode: xcode-select --install).
- Linux: Creation (birth) time is not settable by the kernel; script reports and skips.
"""

import argparse
import logging
import os
import platform
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Windows FILETIME: 100-nanosecond intervals since 1601-01-01 UTC
_WIN_EPOCH_OFFSET = 11644473600  # seconds from 1601 to 1970


def setup_logging(log_file: Optional[Path] = None, verbose: bool = False) -> None:
    """Configure logging to file and console."""
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file, mode="w", encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def _set_creation_time_windows(path: Path, mtime: float) -> bool:
    """Set file creation time on Windows using SetFileTime."""
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        GENERIC_WRITE = 0x40000000
        OPEN_EXISTING = 3
        FILE_SHARE_READ = 0x01

        # Convert Unix timestamp to Windows FILETIME (100-ns since 1601-01-01)
        ft = int((mtime + _WIN_EPOCH_OFFSET) * 10_000_000)
        low = wintypes.DWORD(ft & 0xFFFFFFFF)
        high = wintypes.DWORD(ft >> 32)

        class FILETIME(ctypes.Structure):
            _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

        creation_time = FILETIME(low, high)
        # Leave last write and last access as-is by passing None
        handle = kernel32.CreateFileW(
            str(path.resolve()),
            GENERIC_WRITE,
            FILE_SHARE_READ,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        if handle == -1:  # INVALID_HANDLE_VALUE
            return False
        try:
            return bool(kernel32.SetFileTime(ctypes.c_void_p(handle), ctypes.byref(creation_time), None, None))
        finally:
            kernel32.CloseHandle(handle)
    except Exception as e:
        logging.debug(f"Windows SetFileTime failed for {path}: {e}")
        return False


def _set_creation_time_macos(path: Path, mtime: float) -> bool:
    """Set file creation time on macOS using SetFile (Xcode)."""
    try:
        import subprocess
        from datetime import datetime

        # SetFile -d expects format "MM/DD/YYYY HH:MM:SS"
        dt = datetime.fromtimestamp(mtime)
        date_str = dt.strftime("%m/%d/%Y %H:%M:%S")
        result = subprocess.run(
            ["SetFile", "-d", date_str, str(path.resolve())],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logging.debug(f"SetFile failed for {path}: {result.stderr}")
            return False
        return True
    except FileNotFoundError:
        logging.debug("SetFile not found; install Xcode: xcode-select --install")
        return False
    except Exception as e:
        logging.debug(f"macOS SetFile failed for {path}: {e}")
        return False


def set_creation_time_from_mtime(path: Path, mtime: Optional[float] = None) -> bool:
    """
    Set the file's creation time to its modification time.

    Args:
        path: Path to the file.
        mtime: Modification time (seconds since epoch). If None, read from file.

    Returns:
        True if creation time was set, False otherwise.
    """
    path = path.resolve()
    if not path.is_file():
        logging.warning(f"Not a file: {path}")
        return False

    if mtime is None:
        try:
            st = path.stat()
            mtime = st.st_mtime
        except OSError as e:
            logging.error(f"Cannot stat {path}: {e}")
            return False

    system = platform.system()
    if system == "Windows":
        return _set_creation_time_windows(path, mtime)
    if system == "Darwin":
        return _set_creation_time_macos(path, mtime)
    # Linux and others: creation/birth time is not settable
    logging.debug(f"Creation time is not settable on {system}; skipping {path}")
    return False


def collect_files(path: Path, recursive: bool) -> List[Path]:
    """Collect files to process: single file or all files under directory."""
    path = path.resolve()
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    if not recursive:
        return [p for p in path.iterdir() if p.is_file()]
    return [p for p in path.rglob("*") if p.is_file()]


def copy_mtime_to_ctime(
    source: Path,
    recursive: bool = False,
    dry_run: bool = False,
) -> Tuple[int, int, int]:
    """
    Copy modification time to creation time for file(s).

    Args:
        source: File or directory to process.
        recursive: If source is a directory, process all files under it.
        dry_run: If True, only report what would be done.

    Returns:
        (processed, updated, skipped) counts.
    """
    files = collect_files(source, recursive)
    processed = 0
    updated = 0
    skipped = 0
    system = platform.system()

    if system not in ("Windows", "Darwin") and files:
        logging.warning(
            f"Creation time cannot be set on {system}. "
            "Only Windows and macOS are supported for setting creation time."
        )

    for f in files:
        processed += 1
        try:
            st = f.stat()
            mtime = st.st_mtime
        except OSError as e:
            logging.error(f"Cannot stat {f}: {e}")
            skipped += 1
            continue

        if dry_run:
            logging.info(f"[DRY RUN] Would set creation time of {f} to mtime {mtime}")
            updated += 1
            continue

        if set_creation_time_from_mtime(f, mtime):
            logging.info(f"Set creation time: {f}")
            updated += 1
        else:
            skipped += 1
            if system not in ("Windows", "Darwin"):
                pass  # already logged platform warning
            else:
                logging.warning(f"Could not set creation time: {f}")

    return processed, updated, skipped


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Copy each file's modification time to its creation time.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single file
  python copy_mtime_to_ctime.py /path/to/file.jpg

  # All files in a directory (recursive by default)
  python copy_mtime_to_ctime.py /path/to/folder

  # Only direct children, no subdirs
  python copy_mtime_to_ctime.py /path/to/folder --no-recursive

  # Preview only
  python copy_mtime_to_ctime.py /path/to/folder --dry-run
        """,
    )
    parser.add_argument(
        "path",
        type=Path,
        help="File or directory to process",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        default=True,
        help="If path is a directory, process all files under it (default: True)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_false",
        dest="recursive",
        help="If path is a directory, process only direct children (no subdirs)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report what would be done",
    )
    parser.add_argument(
        "--log",
        type=Path,
        help="Path to log file (optional)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args()

    setup_logging(args.log, args.verbose)

    if not args.path.exists():
        logging.error(f"Path does not exist: {args.path}")
        sys.exit(1)

    processed, updated, skipped = copy_mtime_to_ctime(
        args.path,
        recursive=args.recursive,
        dry_run=args.dry_run,
    )

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Processed: {processed}")
    print(f"Updated:   {updated}")
    print(f"Skipped:   {skipped}")
    if args.dry_run:
        print("\nThis was a DRY RUN. No files were modified.")
    print("=" * 60)

    sys.exit(0)


if __name__ == "__main__":
    main()
