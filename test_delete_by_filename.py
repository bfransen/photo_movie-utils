#!/usr/bin/env python3
"""
Functional tests for delete_by_filename.py

Tests the script with sample data to verify it works correctly.
Works on both Linux and Windows.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Import the module functions
from delete_by_filename import delete_by_filename


def create_test_file(file_path: Path, content: str = "test content", 
                     size: int = None) -> None:
    """Create a test file with optional size.
    
    Args:
        file_path: Path where to create the file
        content: Content to write to the file
        size: Optional target size in bytes (will pad or truncate)
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    if size is not None:
        # Pad or truncate content to match size
        if len(content) < size:
            content = content + 'x' * (size - len(content))
        else:
            content = content[:size]
    
    file_path.write_bytes(content.encode('utf-8'))


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    test_dir = Path(tempfile.mkdtemp(prefix='test_delete_'))
    
    yield test_dir
    
    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)


def test_delete_files_matching_criteria(temp_dir):
    """Test that files starting with ._ and < 4KB are deleted."""
    # Create directory structure
    subdir = temp_dir / "subdir1"
    subdir.mkdir()
    
    # Create files that should be deleted (._ prefix and < 4KB)
    small_file = subdir / "._small_file.txt"
    create_test_file(small_file, "small content", size=1000)
    
    # Create files that should NOT be deleted
    # File with ._ prefix but too large
    large_file = subdir / "._large_file.txt"
    create_test_file(large_file, "x" * 5000, size=5000)
    
    # File without ._ prefix
    normal_file = subdir / "normal_file.txt"
    create_test_file(normal_file, "normal content", size=1000)
    
    # Run the deletion
    stats = delete_by_filename(temp_dir, dry_run=False)
    
    # Verify statistics
    assert stats['deleted'] == 1
    
    # Verify files
    assert not small_file.exists(), "Small ._ file should be deleted"
    assert large_file.exists(), "Large ._ file should NOT be deleted"
    assert normal_file.exists(), "Normal file should NOT be deleted"


def test_delete_dry_run(temp_dir):
    """Test that dry-run mode doesn't actually delete files."""
    subdir = temp_dir / "subdir1"
    subdir.mkdir()
    
    # Create file that should be deleted
    test_file = subdir / "._test_file.txt"
    create_test_file(test_file, "content", size=1000)
    
    # Run in dry-run mode
    stats = delete_by_filename(temp_dir, dry_run=True)
    
    # Verify statistics
    assert stats['deleted'] == 1
    
    # Verify file was NOT actually deleted
    assert test_file.exists(), "File should NOT be deleted in dry-run mode"


def test_delete_nested_directories(temp_dir):
    """Test that files in nested directories are found and deleted."""
    # Create nested directory structure
    subdir1 = temp_dir / "subdir1"
    subdir2 = subdir1 / "subdir2"
    subdir2.mkdir(parents=True)
    
    # Create files in nested directories
    file1 = subdir1 / "._file1.txt"
    create_test_file(file1, "content1", size=1000)
    
    file2 = subdir2 / "._file2.txt"
    create_test_file(file2, "content2", size=2000)
    
    # Run the deletion
    stats = delete_by_filename(temp_dir, dry_run=False)
    
    # Verify both files were deleted
    assert stats['deleted'] == 2
    assert not file1.exists()
    assert not file2.exists()


def test_delete_output_file(temp_dir):
    """Test that deleted files are written to output file."""
    subdir = temp_dir / "subdir1"
    subdir.mkdir()
    
    # Create files to delete
    file1 = subdir / "._file1.txt"
    file2 = subdir / "._file2.txt"
    create_test_file(file1, "content1", size=1000)
    create_test_file(file2, "content2", size=2000)
    
    # Create output file path
    output_file = temp_dir / "deleted_files.txt"
    
    # Run the deletion
    stats = delete_by_filename(temp_dir, output_file=output_file, dry_run=False)
    
    # Verify output file was created
    assert output_file.exists()
    
    # Verify content
    content = output_file.read_text(encoding='utf-8')
    assert str(file1) in content or file1.name in content
    assert str(file2) in content or file2.name in content


def test_delete_skip_large_files(temp_dir):
    """Test that files >= 4KB are not deleted even with ._ prefix."""
    subdir = temp_dir / "subdir1"
    subdir.mkdir()
    
    # Create file exactly at 4KB boundary (should NOT be deleted, threshold is < 4500)
    file_exact = subdir / "._exact_4k.txt"
    create_test_file(file_exact, "x" * 4500, size=4500)
    
    # Create file over 4KB
    file_large = subdir / "._large.txt"
    create_test_file(file_large, "x" * 5000, size=5000)
    
    # Run the deletion
    stats = delete_by_filename(temp_dir, dry_run=False)
    
    # Verify no files were deleted
    assert stats['deleted'] == 0
    assert file_exact.exists()
    assert file_large.exists()


def test_delete_skip_normal_files(temp_dir):
    """Test that files without ._ prefix are not deleted."""
    subdir = temp_dir / "subdir1"
    subdir.mkdir()
    
    # Create normal files (small size but no ._ prefix)
    file1 = subdir / "normal1.txt"
    file2 = subdir / "normal2.txt"
    create_test_file(file1, "content1", size=1000)
    create_test_file(file2, "content2", size=2000)
    
    # Run the deletion
    stats = delete_by_filename(temp_dir, dry_run=False)
    
    # Verify no files were deleted
    assert stats['deleted'] == 0
    assert file1.exists()
    assert file2.exists()


def test_delete_empty_directory(temp_dir):
    """Test handling of empty directory."""
    # Create empty subdirectory
    subdir = temp_dir / "subdir1"
    subdir.mkdir()
    
    # Run the deletion
    stats = delete_by_filename(temp_dir, dry_run=False)
    
    # Verify no files were deleted
    assert stats['deleted'] == 0


def test_delete_multiple_subdirectories(temp_dir):
    """Test that files in multiple subdirectories are all processed."""
    # Create multiple subdirectories
    subdir1 = temp_dir / "subdir1"
    subdir2 = temp_dir / "subdir2"
    subdir1.mkdir()
    subdir2.mkdir()
    
    # Create files in each
    file1 = subdir1 / "._file1.txt"
    file2 = subdir2 / "._file2.txt"
    create_test_file(file1, "content1", size=1000)
    create_test_file(file2, "content2", size=2000)
    
    # Run the deletion
    stats = delete_by_filename(temp_dir, dry_run=False)
    
    # Verify both files were deleted
    assert stats['deleted'] == 2
    assert not file1.exists()
    assert not file2.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

