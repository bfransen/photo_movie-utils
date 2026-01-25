#!/usr/bin/env python3
"""
Integrity verification script.

Scans a directory tree, computes SHA-256 hashes for new or changed files,
and stores results in a local SQLite database.
"""

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set


DEFAULT_DB_NAME = "integrity.db"
DEFAULT_HASH_ALGO = "sha256"
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024
COMMIT_EVERY = 250


def setup_logging(log_file: Optional[Path] = None, verbose: bool = False) -> None:
    """Configure logging to file and console."""
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file, mode='w', encoding='utf-8'))

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def parse_exclude_extensions(exclude_args: List[str]) -> Set[str]:
    """Normalize exclude extensions into a set of lowercase suffixes."""
    extensions: Set[str] = set()
    for item in exclude_args:
        for part in item.split(','):
            ext = part.strip().lower()
            if not ext:
                continue
            if not ext.startswith('.'):
                ext = f".{ext}"
            extensions.add(ext)
    return extensions


def iter_files(root: Path) -> Iterable[Path]:
    """Iterate through files under root without following symlinks."""
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            yield Path(entry.path)
                    except OSError as exc:
                        logging.warning(f"Skipping entry {entry.path}: {exc}")
        except OSError as exc:
            logging.warning(f"Skipping directory {current}: {exc}")


def compute_hash(file_path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """Compute SHA-256 hash for a file."""
    hasher = hashlib.sha256()
    with file_path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def connect_database(db_path: Path) -> sqlite3.Connection:
    """Open database connection and initialize schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            hash TEXT NOT NULL,
            hash_algo TEXT NOT NULL,
            last_seen INTEGER NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_last_seen ON files(last_seen)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_filename ON files(filename)")
    return conn


def open_database_readonly(db_path: Path) -> sqlite3.Connection:
    """Open the database in read-only mode."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def is_under_root(file_path: Path, root: Path) -> bool:
    """Return True if file_path is under root."""
    try:
        file_path.relative_to(root)
    except ValueError:
        return False
    return True


def build_report(
    root: Path,
    db_path: Path,
    hash_algo: str,
    exclude_exts: Set[str],
    stats: Dict[str, int],
    run_started: int,
    run_finished: int,
    mode: str,
    details: Optional[Dict[str, object]],
) -> Dict[str, object]:
    """Build JSON-compatible report."""
    report: Dict[str, object] = {
        "run_started": datetime.fromtimestamp(run_started).isoformat(),
        "run_finished": datetime.fromtimestamp(run_finished).isoformat(),
        "duration_seconds": run_finished - run_started,
        "root": str(root),
        "db": str(db_path),
        "hash_algo": hash_algo,
        "mode": mode,
        "exclude_exts": sorted(exclude_exts),
        "stats": stats,
    }
    if details:
        report.update(details)
    return report


def index_files(
    root: Path,
    db_path: Path,
    exclude_exts: Set[str],
    report_path: Optional[Path],
) -> Dict[str, object]:
    """Scan files, hash new or changed entries, and update the database."""
    stats = {
        "scanned": 0,
        "excluded": 0,
        "hashed_new": 0,
        "hashed_updated": 0,
        "unchanged": 0,
        "errors": 0,
    }
    include_details = report_path is not None
    added: Optional[List[Dict[str, object]]] = [] if include_details else None
    updated: Optional[List[Dict[str, object]]] = [] if include_details else None
    errors: Optional[List[Dict[str, object]]] = [] if include_details else None

    run_started = int(time.time())
    excluded_paths = {str(db_path.resolve())}
    if report_path:
        excluded_paths.add(str(report_path.resolve()))

    conn = connect_database(db_path)
    processed_since_commit = 0

    try:
        for file_path in iter_files(root):
            path_str = str(file_path)
            if path_str in excluded_paths:
                stats["excluded"] += 1
                continue
            if file_path.suffix.lower() in exclude_exts:
                stats["excluded"] += 1
                continue

            stats["scanned"] += 1
            try:
                file_stat = file_path.stat()
            except OSError as exc:
                stats["errors"] += 1
                logging.warning(f"Failed to stat {file_path}: {exc}")
                if errors is not None:
                    errors.append({"path": path_str, "error": str(exc)})
                continue

            size = file_stat.st_size
            mtime_ns = file_stat.st_mtime_ns
            filename = file_path.name
            existing = conn.execute(
                "SELECT size, mtime_ns, hash FROM files WHERE path = ?",
                (path_str,),
            ).fetchone()

            if existing and existing["size"] == size and existing["mtime_ns"] == mtime_ns:
                conn.execute(
                    "UPDATE files SET last_seen = ? WHERE path = ?",
                    (run_started, path_str),
                )
                stats["unchanged"] += 1
            else:
                try:
                    digest = compute_hash(file_path)
                except OSError as exc:
                    stats["errors"] += 1
                    logging.warning(f"Failed to hash {file_path}: {exc}")
                    if errors is not None:
                        errors.append({"path": path_str, "error": str(exc)})
                    continue

                if existing:
                    stats["hashed_updated"] += 1
                    if updated is not None:
                        updated.append(
                            {
                                "path": path_str,
                                "size": size,
                                "mtime_ns": mtime_ns,
                                "hash": digest,
                                "previous_hash": existing["hash"],
                            }
                        )
                else:
                    stats["hashed_new"] += 1
                    if added is not None:
                        added.append(
                            {
                                "path": path_str,
                                "size": size,
                                "mtime_ns": mtime_ns,
                                "hash": digest,
                            }
                        )

                conn.execute(
                    """
                    INSERT INTO files (path, filename, size, mtime_ns, hash, hash_algo, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(path) DO UPDATE SET
                        filename = excluded.filename,
                        size = excluded.size,
                        mtime_ns = excluded.mtime_ns,
                        hash = excluded.hash,
                        hash_algo = excluded.hash_algo,
                        last_seen = excluded.last_seen
                    """,
                    (path_str, filename, size, mtime_ns, digest, DEFAULT_HASH_ALGO, run_started),
                )

            processed_since_commit += 1
            if processed_since_commit >= COMMIT_EVERY:
                conn.commit()
                processed_since_commit = 0

        if processed_since_commit:
            conn.commit()
    finally:
        conn.close()

    run_finished = int(time.time())
    details: Dict[str, object] = {}
    if added is not None:
        details["added"] = added
    if updated is not None:
        details["updated"] = updated
    if errors is not None:
        details["errors"] = errors
    report = build_report(
        root=root,
        db_path=db_path,
        hash_algo=DEFAULT_HASH_ALGO,
        exclude_exts=exclude_exts,
        stats=stats,
        run_started=run_started,
        run_finished=run_finished,
        mode="index",
        details=details,
    )
    return report


def verify_files(
    root: Path,
    db_path: Path,
    exclude_exts: Set[str],
    report_path: Optional[Path],
) -> Dict[str, object]:
    """Verify files by comparing stored hashes against current hashes."""
    stats = {
        "scanned": 0,
        "excluded": 0,
        "verified": 0,
        "mismatched": 0,
        "missing": 0,
        "untracked": 0,
        "errors": 0,
        "db_entries": 0,
    }
    include_details = report_path is not None
    mismatched: Optional[List[Dict[str, object]]] = [] if include_details else None
    missing: Optional[List[Dict[str, object]]] = [] if include_details else None
    untracked: Optional[List[Dict[str, object]]] = [] if include_details else None
    errors: Optional[List[Dict[str, object]]] = [] if include_details else None

    run_started = int(time.time())
    excluded_paths = {str(db_path.resolve())}
    if report_path:
        excluded_paths.add(str(report_path.resolve()))

    conn = open_database_readonly(db_path)
    try:
        stats["db_entries"] = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        
        # Track which hashes have been verified (to avoid marking moved files as missing)
        verified_hashes: Set[str] = set()
        # Track which paths have been verified (for backwards compatibility)
        verified_paths: Set[str] = set()

        for file_path in iter_files(root):
            path_str = str(file_path)
            if path_str in excluded_paths:
                stats["excluded"] += 1
                continue
            if file_path.suffix.lower() in exclude_exts:
                stats["excluded"] += 1
                continue

            stats["scanned"] += 1
            try:
                file_stat = file_path.stat()
            except OSError as exc:
                stats["errors"] += 1
                logging.warning(f"Failed to stat {file_path}: {exc}")
                if errors is not None:
                    errors.append({"path": path_str, "error": str(exc)})
                continue

            # Compute hash first for hash-based matching
            try:
                digest = compute_hash(file_path)
            except OSError as exc:
                stats["errors"] += 1
                logging.warning(f"Failed to hash {file_path}: {exc}")
                if errors is not None:
                    errors.append({"path": path_str, "error": str(exc)})
                continue

            filename = file_path.name
            # Try hash-based lookup first (handles moved/renamed files)
            rows_by_hash = conn.execute(
                "SELECT path, filename, hash_algo FROM files WHERE hash = ?",
                (digest,),
            ).fetchall()

            # Try path-based lookup for backwards compatibility
            row_by_path = conn.execute(
                "SELECT path, filename, hash, hash_algo FROM files WHERE path = ?",
                (path_str,),
            ).fetchone()

            # Determine which row to use
            row = None
            matched_by_hash = False
            if rows_by_hash:
                # Found by hash - check if filename matches (prefer exact match)
                for candidate in rows_by_hash:
                    if candidate["filename"] == filename:
                        row = candidate
                        matched_by_hash = True
                        verified_hashes.add(digest)
                        verified_paths.add(candidate["path"])
                        break
                # If no filename match, use first hash match (file may have been renamed)
                if not row:
                    row = rows_by_hash[0]
                    matched_by_hash = True
                    verified_hashes.add(digest)
                    verified_paths.add(row["path"])
            elif row_by_path:
                # Found by path (backwards compatibility)
                row = row_by_path
                verified_paths.add(path_str)
                # Check if hash matches
                if row_by_path["hash"] != digest:
                    # Path matches but hash doesn't - file was modified
                    stats["mismatched"] += 1
                    if mismatched is not None:
                        mismatched.append(
                            {
                                "path": path_str,
                                "size": file_stat.st_size,
                                "mtime_ns": file_stat.st_mtime_ns,
                                "expected_hash": row_by_path["hash"],
                                "actual_hash": digest,
                            }
                        )
                    continue

            if not row:
                stats["untracked"] += 1
                if untracked is not None:
                    untracked.append(
                        {
                            "path": path_str,
                            "size": file_stat.st_size,
                            "mtime_ns": file_stat.st_mtime_ns,
                        }
                    )
                continue

            if row["hash_algo"] != DEFAULT_HASH_ALGO:
                stats["errors"] += 1
                logging.warning(
                    f"Unsupported hash algorithm for {file_path}: {row['hash_algo']}"
                )
                if errors is not None:
                    errors.append(
                        {
                            "path": path_str,
                            "error": f"Unsupported hash algorithm: {row['hash_algo']}",
                        }
                    )
                continue

            # Hash matches (already computed above)
            stats["verified"] += 1
            if matched_by_hash and row["path"] != path_str:
                # File was moved/renamed - log this for information
                logging.debug(f"File moved: {row['path']} -> {path_str}")

        # Check for missing files: entries in DB that weren't found
        for row in conn.execute("SELECT path, hash FROM files"):
            record_path = Path(row["path"])
            if not is_under_root(record_path, root):
                continue
            if record_path.suffix.lower() in exclude_exts:
                continue
            record_str = str(record_path)
            if record_str in excluded_paths:
                continue
            
            # Skip if this hash was already verified (file was moved, not missing)
            if row["hash"] in verified_hashes:
                continue
            # Skip if this path was already verified
            if record_str in verified_paths:
                continue
            
            if not record_path.exists():
                stats["missing"] += 1
                if missing is not None:
                    missing.append({"path": record_str})
    finally:
        conn.close()

    run_finished = int(time.time())
    details: Dict[str, object] = {}
    if mismatched is not None:
        details["mismatched"] = mismatched
    if missing is not None:
        details["missing"] = missing
    if untracked is not None:
        details["untracked"] = untracked
    if errors is not None:
        details["errors"] = errors

    report = build_report(
        root=root,
        db_path=db_path,
        hash_algo=DEFAULT_HASH_ALGO,
        exclude_exts=exclude_exts,
        stats=stats,
        run_started=run_started,
        run_finished=run_finished,
        mode="verify",
        details=details,
    )
    return report


def write_report(report: Dict[str, object], report_path: Optional[Path]) -> None:
    """Write report to file or stdout."""
    report_json = json.dumps(report, indent=2, sort_keys=True)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_json, encoding='utf-8')
        logging.info(f"Report written to {report_path}")
    else:
        print(report_json)


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Scan files, hash new or changed entries, and store results in SQLite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build or update the hash database
  python verify_integrity.py index --root /path/to/photos --db integrity.db --report report.json

  # Exclude specific file types
  python verify_integrity.py index --root /path/to/photos --exclude-ext .tmp,.db --report report.json

  # Verify files against the stored hashes
  python verify_integrity.py verify --root /path/to/photos --db integrity.db --report verify.json
        """,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    index_parser = subparsers.add_parser(
        'index',
        help='Scan files and store hashes for new or changed entries',
    )
    index_parser.add_argument(
        '--root',
        type=Path,
        required=True,
        help='Root directory to scan recursively',
    )
    index_parser.add_argument(
        '--db',
        type=Path,
        default=Path(DEFAULT_DB_NAME),
        help=f'Path to SQLite database (default: {DEFAULT_DB_NAME})',
    )
    index_parser.add_argument(
        '--exclude-ext',
        action='append',
        default=[],
        help='File extensions to exclude (comma-separated or repeatable)',
    )
    index_parser.add_argument(
        '--report',
        type=Path,
        help='Path to JSON report file (optional)',
    )
    index_parser.add_argument(
        '--log',
        type=Path,
        help='Path to log file (optional)',
    )
    index_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging',
    )

    verify_parser = subparsers.add_parser(
        'verify',
        help='Verify files by comparing stored hashes to current hashes',
    )
    verify_parser.add_argument(
        '--root',
        type=Path,
        required=True,
        help='Root directory to scan recursively',
    )
    verify_parser.add_argument(
        '--db',
        type=Path,
        default=Path(DEFAULT_DB_NAME),
        help=f'Path to SQLite database (default: {DEFAULT_DB_NAME})',
    )
    verify_parser.add_argument(
        '--exclude-ext',
        action='append',
        default=[],
        help='File extensions to exclude (comma-separated or repeatable)',
    )
    verify_parser.add_argument(
        '--report',
        type=Path,
        help='Path to JSON report file (optional)',
    )
    verify_parser.add_argument(
        '--log',
        type=Path,
        help='Path to log file (optional)',
    )
    verify_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging',
    )

    args = parser.parse_args()

    setup_logging(getattr(args, 'log', None), getattr(args, 'verbose', False))

    if args.command == 'index':
        root = args.root.resolve()
        if not root.exists():
            logging.error(f"Root directory does not exist: {root}")
            sys.exit(1)
        if not root.is_dir():
            logging.error(f"Root path is not a directory: {root}")
            sys.exit(1)

        exclude_exts = parse_exclude_extensions(args.exclude_ext)
        report = index_files(
            root=root,
            db_path=args.db,
            exclude_exts=exclude_exts,
            report_path=args.report,
        )
        write_report(report, args.report)
        sys.exit(0)

    if args.command == 'verify':
        root = args.root.resolve()
        if not root.exists():
            logging.error(f"Root directory does not exist: {root}")
            sys.exit(1)
        if not root.is_dir():
            logging.error(f"Root path is not a directory: {root}")
            sys.exit(1)

        exclude_exts = parse_exclude_extensions(args.exclude_ext)
        try:
            report = verify_files(
                root=root,
                db_path=args.db,
                exclude_exts=exclude_exts,
                report_path=args.report,
            )
        except FileNotFoundError as exc:
            logging.error(str(exc))
            sys.exit(1)

        write_report(report, args.report)

        stats = report.get("stats", {})
        if stats.get("mismatched", 0) or stats.get("missing", 0) or stats.get("errors", 0):
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
