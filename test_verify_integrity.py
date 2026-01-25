#!/usr/bin/env python3
"""
Unit tests for verify_integrity.py hashing and indexing logic.
"""

import hashlib
import logging
import os
import sqlite3
import time
from pathlib import Path

import pytest

from verify_integrity import (
    compute_hash,
    index_files,
    parse_exclude_extensions,
    verify_files,
)


logging.basicConfig(level=logging.WARNING)


def _write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _fetch_db_rows(db_path: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            "SELECT path, size, mtime_ns, hash, hash_algo FROM files ORDER BY path"
        ).fetchall()
    finally:
        conn.close()


def test_parse_exclude_extensions_normalizes():
    exclude = parse_exclude_extensions(["tmp,.db", ".log", "  .MOV , mp4  "])
    assert exclude == {".tmp", ".db", ".log", ".mov", ".mp4"}


def test_index_files_records_new_and_excludes(tmp_path: Path):
    root = tmp_path / "root"
    db_path = tmp_path / "integrity.db"
    report_path = tmp_path / "report.json"

    _write_file(root / "a.txt", b"alpha")
    _write_file(root / "b.tmp", b"temp")
    _write_file(root / "nested" / "c.bin", b"binary")

    report = index_files(
        root=root,
        db_path=db_path,
        exclude_exts={".tmp"},
        report_path=report_path,
    )

    assert report["stats"]["scanned"] == 2
    assert report["stats"]["excluded"] == 1
    assert report["stats"]["hashed_new"] == 2
    assert report["stats"]["hashed_updated"] == 0
    assert report["stats"]["unchanged"] == 0
    assert len(report["added"]) == 2

    added_paths = {item["path"] for item in report["added"]}
    assert added_paths == {
        str(root / "a.txt"),
        str(root / "nested" / "c.bin"),
    }

    rows = _fetch_db_rows(db_path)
    assert len(rows) == 2
    row_map = {row["path"]: row for row in rows}
    assert row_map[str(root / "a.txt")]["hash"] == hashlib.sha256(b"alpha").hexdigest()
    assert row_map[str(root / "nested" / "c.bin")]["hash_algo"] == "sha256"


def test_index_files_updates_on_change_and_tracks_unchanged(tmp_path: Path):
    root = tmp_path / "root"
    db_path = tmp_path / "integrity.db"
    report_path = tmp_path / "report.json"
    file_path = root / "photo.jpg"

    initial_content = b"version-one"
    _write_file(file_path, initial_content)
    first = index_files(
        root=root,
        db_path=db_path,
        exclude_exts=set(),
        report_path=report_path,
    )
    assert first["stats"]["hashed_new"] == 1

    previous_hash = hashlib.sha256(initial_content).hexdigest()
    new_content = b"version-two"
    _write_file(file_path, new_content)
    mtime = file_path.stat().st_mtime + 10
    time.sleep(0.01)
    os.utime(file_path, (mtime, mtime))

    second = index_files(
        root=root,
        db_path=db_path,
        exclude_exts=set(),
        report_path=report_path,
    )

    assert second["stats"]["hashed_updated"] == 1
    assert second["stats"]["hashed_new"] == 0
    assert len(second["updated"]) == 1
    assert second["updated"][0]["previous_hash"] == previous_hash

    rows = _fetch_db_rows(db_path)
    assert len(rows) == 1
    assert rows[0]["hash"] == compute_hash(file_path)

    third = index_files(
        root=root,
        db_path=db_path,
        exclude_exts=set(),
        report_path=report_path,
    )
    assert third["stats"]["unchanged"] == 1


def test_verify_files_reports_mismatch_and_untracked(tmp_path: Path):
    root = tmp_path / "root"
    db_path = tmp_path / "integrity.db"
    report_path = tmp_path / "report.json"

    tracked_path = root / "tracked.txt"
    _write_file(tracked_path, b"original")
    _write_file(root / "stable.txt", b"stable")

    index_files(
        root=root,
        db_path=db_path,
        exclude_exts=set(),
        report_path=report_path,
    )

    _write_file(tracked_path, b"changed")
    untracked_path = root / "new.txt"
    _write_file(untracked_path, b"new")

    report = verify_files(
        root=root,
        db_path=db_path,
        exclude_exts=set(),
        report_path=report_path,
    )

    stats = report["stats"]
    assert stats["mismatched"] == 1
    assert stats["verified"] == 1
    assert stats["untracked"] == 1
    assert stats["missing"] == 0

    mismatch_paths = {item["path"] for item in report["mismatched"]}
    assert mismatch_paths == {str(tracked_path)}
    untracked_paths = {item["path"] for item in report["untracked"]}
    assert untracked_paths == {str(untracked_path)}


def test_verify_files_reports_missing(tmp_path: Path):
    root = tmp_path / "root"
    db_path = tmp_path / "integrity.db"
    report_path = tmp_path / "report.json"
    missing_path = root / "gone.txt"

    _write_file(missing_path, b"data")
    index_files(
        root=root,
        db_path=db_path,
        exclude_exts=set(),
        report_path=report_path,
    )

    missing_path.unlink()

    report = verify_files(
        root=root,
        db_path=db_path,
        exclude_exts=set(),
        report_path=report_path,
    )

    stats = report["stats"]
    assert stats["missing"] == 1
    assert report["missing"][0]["path"] == str(missing_path)


def test_verify_files_handles_moved_files_by_hash(tmp_path: Path):
    """Test that verify can find files that have been moved/renamed using hash-based matching."""
    root = tmp_path / "root"
    db_path = tmp_path / "integrity.db"
    report_path = tmp_path / "report.json"
    
    # Create file in original location
    original_path = root / "old_folder" / "photo.jpg"
    _write_file(original_path, b"photo content")
    
    # Index the file
    index_files(
        root=root,
        db_path=db_path,
        exclude_exts=set(),
        report_path=report_path,
    )
    
    # Move file to new location (simulating folder rename)
    new_path = root / "2024-01-15_January_15_2024" / "photo.jpg"
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_bytes(original_path.read_bytes())
    original_path.unlink()
    original_path.parent.rmdir()
    
    # Verify - should find file by hash even though path changed
    report = verify_files(
        root=root,
        db_path=db_path,
        exclude_exts=set(),
        report_path=report_path,
    )
    
    stats = report["stats"]
    # File should be verified (found by hash)
    assert stats["verified"] == 1
    # Original path should NOT be marked as missing (because hash was verified)
    assert stats["missing"] == 0
    # New path should NOT be marked as untracked (because hash matched)
    assert stats["untracked"] == 0
