#!/usr/bin/env python3
"""
Tests for convert_videos.py.
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from convert_videos import (
    build_output_path,
    convert_videos,
    get_preferred_timestamp,
    load_preset_names,
    normalize_extensions,
)


@pytest.fixture
def temp_dirs():
    """Create temporary source and destination directories for testing."""
    source_dir = Path(tempfile.mkdtemp(prefix='test_source_'))
    dest_dir = Path(tempfile.mkdtemp(prefix='test_dest_'))

    yield source_dir, dest_dir

    shutil.rmtree(source_dir, ignore_errors=True)
    shutil.rmtree(dest_dir, ignore_errors=True)


def create_test_file(file_path: Path, content: str = "test data",
                     timestamp: datetime = None) -> None:
    """Create a test file with an optional timestamp."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')

    if timestamp:
        ts = timestamp.timestamp()
        os.utime(file_path, (ts, ts))


def create_preset_file(file_path: Path) -> None:
    """Create a minimal HandBrake preset file."""
    data = {
        "PresetList": [
            {"PresetName": "Preset A"},
            {"Folder": True, "ChildrenArray": [{"PresetName": "Preset B"}]},
        ]
    }
    file_path.write_text(json.dumps(data), encoding='utf-8')


def test_normalize_extensions():
    extensions = normalize_extensions(["mp4", ".MOV", "mkv, avi"])
    assert set(extensions) == {".mp4", ".mov", ".mkv", ".avi"}


def test_build_output_path_preserves_structure(temp_dirs):
    source_dir, dest_dir = temp_dirs
    file_path = source_dir / "nested" / "clip.mov"

    output_path = build_output_path(file_path, source_dir, dest_dir, ".mp4")
    assert output_path == dest_dir / "nested" / "clip.mp4"


def test_get_preferred_timestamp_filesystem(temp_dirs):
    source_dir, _ = temp_dirs
    test_date = datetime(2024, 1, 15, 12, 0, 0)
    file_path = source_dir / "video.mp4"
    create_test_file(file_path, "fake video data", test_date)

    timestamp, source = get_preferred_timestamp(file_path)
    assert source == "filesystem"
    assert abs((timestamp - test_date).total_seconds()) < 5


def test_load_preset_names(temp_dirs):
    source_dir, _ = temp_dirs
    preset_path = source_dir / "presets.json"
    create_preset_file(preset_path)

    names = load_preset_names(preset_path)
    assert names == ["Preset A", "Preset B"]


def test_convert_videos_dry_run(temp_dirs):
    source_dir, dest_dir = temp_dirs
    # Preset lives outside source_dir so it isn't counted in "scanned" (we only
    # scan source content: clip1.mov, clip2.mp4, notes.txt = 3 files).
    preset_path = dest_dir / "presets.json"
    create_preset_file(preset_path)

    create_test_file(source_dir / "clip1.mov")
    create_test_file(source_dir / "clip2.mp4")
    create_test_file(source_dir / "notes.txt")

    stats = convert_videos(
        source_dir=source_dir,
        destination_dir=dest_dir,
        extensions=[".mov", ".mp4"],
        output_extension=".mkv",
        preset_file=preset_path,
        preset_name="Preset A",
        handbrake_cli="HandBrakeCLI",
        handbrake_format=None,
        extra_args=[],
        recursive=False,
        overwrite=False,
        dry_run=True,
    )

    assert stats["scanned"] == 3
    assert stats["matched"] == 2
    assert stats["converted"] == 2
    assert stats["skipped"] == 0
    assert stats["failed"] == 0

    assert not (dest_dir / "clip1.mkv").exists()
    assert not (dest_dir / "clip2.mkv").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
