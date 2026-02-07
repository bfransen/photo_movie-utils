#!/usr/bin/env python3
"""
Tests for copy_mtime_to_ctime.py

Tests collection and dry-run behavior; actual creation-time setting is platform-specific.
"""

import os
import tempfile
from pathlib import Path

import pytest

from copy_mtime_to_ctime import collect_files, copy_mtime_to_ctime, set_creation_time_from_mtime


@pytest.fixture
def temp_dir():
    """Create temporary directory with a file."""
    d = Path(tempfile.mkdtemp(prefix="test_copy_mtime_"))
    (d / "a.txt").write_text("a")
    (d / "b.txt").write_text("b")
    sub = d / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("c")
    yield d
    import shutil
    shutil.rmtree(d, ignore_errors=True)


def test_collect_files_single_file(temp_dir):
    """Single file path returns that file only."""
    f = temp_dir / "a.txt"
    assert collect_files(f, recursive=False) == [f]
    assert collect_files(f, recursive=True) == [f]


def test_collect_files_dir_non_recursive(temp_dir):
    """Directory without recursive returns only direct children files."""
    files = collect_files(temp_dir, recursive=False)
    assert len(files) == 2
    assert set(files) == {temp_dir / "a.txt", temp_dir / "b.txt"}


def test_collect_files_dir_recursive(temp_dir):
    """Directory with recursive returns all files under it."""
    files = collect_files(temp_dir, recursive=True)
    assert len(files) == 3
    assert set(files) == {
        temp_dir / "a.txt",
        temp_dir / "b.txt",
        temp_dir / "sub" / "c.txt",
    }


def test_copy_mtime_to_ctime_dry_run(temp_dir):
    """Dry run reports correct counts without changing files."""
    processed, updated, skipped = copy_mtime_to_ctime(temp_dir, recursive=True, dry_run=True)
    assert processed == 3
    assert updated == 3
    assert skipped == 0


def test_set_creation_time_from_mtime_nonexistent():
    """Non-existent path returns False."""
    assert set_creation_time_from_mtime(Path("/nonexistent/file.txt")) is False


def test_set_creation_time_from_mtime_directory(temp_dir):
    """Directory path returns False (only files are supported)."""
    assert set_creation_time_from_mtime(temp_dir) is False
