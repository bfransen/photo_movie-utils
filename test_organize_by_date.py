#!/usr/bin/env python3
"""
Functional tests for organize_by_date.py

Tests the script with sample data to verify it works correctly.
Works on both Linux and Windows.
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# Import the module functions
from organize_by_date import organize_files, get_file_date


def create_test_file(file_path: Path, content: str = "test content", 
                     timestamp: datetime = None) -> None:
    """Create a test file with optional timestamp.
    
    Args:
        file_path: Path where to create the file
        content: Content to write to the file
        timestamp: Optional datetime to set as file modification time
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')
    
    if timestamp:
        # Set both modification and access time
        # Note: On Windows, we can only set mtime and atime, not ctime
        timestamp_float = timestamp.timestamp()
        os.utime(file_path, (timestamp_float, timestamp_float))


def create_test_image(file_path: Path, timestamp: datetime = None) -> None:
    """Create a simple test image file (PNG).
    
    Args:
        file_path: Path where to create the image
        timestamp: Optional datetime to set as file modification time
    """
    try:
        from PIL import Image
        
        # Create a simple 10x10 red image
        img = Image.new('RGB', (10, 10), color='red')
        file_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(file_path, 'PNG')
        
        if timestamp:
            timestamp_float = timestamp.timestamp()
            os.utime(file_path, (timestamp_float, timestamp_float))
    except ImportError:
        # If PIL is not available, create a dummy file
        create_test_file(file_path, "fake image data", timestamp)


def create_test_video(file_path: Path, timestamp: datetime = None) -> None:
    """Create a dummy test video file.
    
    Args:
        file_path: Path where to create the video
        timestamp: Optional datetime to set as file modification time
    """
    # Create a dummy file with video extension
    # Real video metadata would require actual video encoding
    create_test_file(file_path, "fake video data", timestamp)


@pytest.fixture
def temp_dirs():
    """Create temporary source and destination directories for testing."""
    source_dir = Path(tempfile.mkdtemp(prefix='test_source_'))
    dest_dir = Path(tempfile.mkdtemp(prefix='test_dest_'))
    
    yield source_dir, dest_dir
    
    # Cleanup
    shutil.rmtree(source_dir, ignore_errors=True)
    shutil.rmtree(dest_dir, ignore_errors=True)


def test_organize_files_by_timestamp(temp_dirs):
    """Test that files are organized by their file timestamps."""
    source_dir, dest_dir = temp_dirs
    
    # Create test files with different dates
    dates = [
        datetime(2023, 1, 15, 10, 30, 0),
        datetime(2023, 2, 20, 14, 45, 0),
        datetime(2023, 3, 10, 9, 15, 0),
    ]
    
    files = []
    for i, date in enumerate(dates):
        file_path = source_dir / f"test_file_{i}.txt"
        create_test_file(file_path, f"content {i}", date)
        files.append(file_path)
    
    # Run the organization
    stats = organize_files(source_dir, dest_dir, dry_run=False)
    
    # Verify statistics
    assert stats['processed'] == 3
    assert stats['copied'] == 3
    assert stats['failed'] == 0
    
    # Verify files are in correct date folders
    assert (dest_dir / "2023-01-15" / "test_file_0.txt").exists()
    assert (dest_dir / "2023-02-20" / "test_file_1.txt").exists()
    assert (dest_dir / "2023-03-10" / "test_file_2.txt").exists()
    
    # Verify source files still exist (script copies, not moves)
    for file_path in files:
        assert file_path.exists()


def test_organize_dry_run(temp_dirs):
    """Test that dry-run mode doesn't actually copy files."""
    source_dir, dest_dir = temp_dirs
    
    # Create a test file
    test_date = datetime(2023, 5, 1, 12, 0, 0)
    file_path = source_dir / "test.txt"
    create_test_file(file_path, "test content", test_date)
    
    # Run in dry-run mode
    stats = organize_files(source_dir, dest_dir, dry_run=True)
    
    # Verify statistics
    assert stats['processed'] == 1
    assert stats['copied'] == 1  # Counted as "would copy"
    
    # Verify file was NOT actually copied
    assert not (dest_dir / "2023-05-01" / "test.txt").exists()
    
    # Verify source file still exists
    assert file_path.exists()


def test_organize_all_file_types(temp_dirs):
    """Test that all file types are processed, not just images/videos."""
    source_dir, dest_dir = temp_dirs
    
    test_date = datetime(2023, 6, 15, 10, 0, 0)
    
    # Create files of different types
    files = {
        'document.pdf': source_dir / "document.pdf",
        'spreadsheet.xlsx': source_dir / "spreadsheet.xlsx",
        'archive.zip': source_dir / "archive.zip",
        'script.py': source_dir / "script.py",
        'data.json': source_dir / "data.json",
    }
    
    for file_path in files.values():
        create_test_file(file_path, "test content", test_date)
    
    # Run the organization
    stats = organize_files(source_dir, dest_dir, dry_run=False)
    
    # Verify all files were processed
    assert stats['processed'] == len(files)
    assert stats['copied'] == len(files)
    
    # Verify all files are in the same date folder
    date_folder = dest_dir / "2023-06-15"
    assert date_folder.exists()
    
    for filename, original_path in files.items():
        assert (date_folder / filename).exists()


def test_organize_nested_directories(temp_dirs):
    """Test that files in nested directories are found and organized."""
    source_dir, dest_dir = temp_dirs
    
    # Create nested directory structure
    nested_dir = source_dir / "subdir" / "nested"
    nested_dir.mkdir(parents=True, exist_ok=True)
    
    test_date = datetime(2023, 7, 1, 8, 0, 0)
    file_path = nested_dir / "nested_file.txt"
    create_test_file(file_path, "nested content", test_date)
    
    # Run the organization
    stats = organize_files(source_dir, dest_dir, dry_run=False)
    
    # Verify file was found and organized
    assert stats['processed'] == 1
    assert stats['copied'] == 1
    
    # Verify file is in correct date folder (not preserving nested structure)
    assert (dest_dir / "2023-07-01" / "nested_file.txt").exists()


def test_skip_duplicate_files(temp_dirs):
    """Test that duplicate files (same name) are skipped."""
    source_dir, dest_dir = temp_dirs
    
    test_date = datetime(2023, 8, 1, 12, 0, 0)
    
    # Create a file and organize it
    file_path = source_dir / "duplicate.txt"
    create_test_file(file_path, "content", test_date)
    
    stats1 = organize_files(source_dir, dest_dir, dry_run=False)
    assert stats1['copied'] == 1
    
    # Try to organize again (should skip)
    stats2 = organize_files(source_dir, dest_dir, dry_run=False)
    assert stats2['processed'] == 1
    assert stats2['skipped'] == 1
    assert stats2['copied'] == 0


def test_get_file_date_fallback(temp_dirs):
    """Test that get_file_date falls back to file timestamps."""
    source_dir, _ = temp_dirs
    
    # Create a non-image, non-video file
    test_date = datetime(2023, 9, 15, 15, 30, 0)
    file_path = source_dir / "test.txt"
    create_test_file(file_path, "test", test_date)
    
    # Get the file date
    file_date = get_file_date(file_path)
    
    # Should be close to our test date (within a few seconds for filesystem precision)
    time_diff = abs((file_date - test_date).total_seconds())
    assert time_diff < 5, f"Date mismatch: {file_date} vs {test_date}"


def test_organize_image_files(temp_dirs):
    """Test that image files are processed (even without EXIF)."""
    source_dir, dest_dir = temp_dirs
    
    test_date = datetime(2023, 10, 1, 10, 0, 0)
    
    # Create a test image
    image_path = source_dir / "test_image.png"
    create_test_image(image_path, test_date)
    
    # Run the organization
    stats = organize_files(source_dir, dest_dir, dry_run=False)
    
    # Verify image was processed
    assert stats['processed'] == 1
    assert stats['copied'] == 1
    
    # Verify image is in correct date folder
    assert (dest_dir / "2023-10-01" / "test_image.png").exists()


def test_organize_video_files(temp_dirs):
    """Test that video files are processed."""
    source_dir, dest_dir = temp_dirs
    
    test_date = datetime(2023, 11, 1, 12, 0, 0)
    
    # Create a test video file
    video_path = source_dir / "test_video.mp4"
    create_test_video(video_path, test_date)
    
    # Run the organization
    stats = organize_files(source_dir, dest_dir, dry_run=False)
    
    # Verify video was processed
    assert stats['processed'] == 1
    assert stats['copied'] == 1
    
    # Verify video is in correct date folder
    assert (dest_dir / "2023-11-01" / "test_video.mp4").exists()


def test_empty_source_directory(temp_dirs):
    """Test handling of empty source directory."""
    source_dir, dest_dir = temp_dirs
    
    # Run on empty directory
    stats = organize_files(source_dir, dest_dir, dry_run=False)
    
    # Verify no files processed
    assert stats['processed'] == 0
    assert stats['copied'] == 0
    assert stats['failed'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

