#!/usr/bin/env python3
"""
Functional tests for rename_folders.py

Tests the script with sample data to verify it works correctly.
Works on both Linux and Windows.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Import the module functions
from rename_folders import rename_folders, convert_date_format


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    test_dir = Path(tempfile.mkdtemp(prefix='test_rename_'))
    
    yield test_dir
    
    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)


def test_rename_folder_with_date(temp_dir):
    """Test that folders with dates are renamed correctly."""
    # Create folder with date in name
    old_folder = temp_dir / "January 15, 2023 photos"
    old_folder.mkdir()
    
    # Create a file inside to verify folder is moved
    test_file = old_folder / "test.txt"
    test_file.write_text("test content")
    
    # Run the renaming
    stats = rename_folders(temp_dir, dry_run=False)
    
    # Verify statistics
    assert stats['renamed'] == 1
    assert stats['no_match'] == 0
    
    # Verify folder was renamed
    new_folder = temp_dir / "2023-01-15_January_15_2023_photos"
    assert new_folder.exists(), "Folder should be renamed"
    assert not old_folder.exists(), "Old folder should not exist"
    
    # Verify file is still in renamed folder
    assert (new_folder / "test.txt").exists()


def test_rename_folder_dry_run(temp_dir):
    """Test that dry-run mode doesn't actually rename folders."""
    # Create folder with date
    old_folder = temp_dir / "February 20, 2023 videos"
    old_folder.mkdir()
    
    # Run in dry-run mode
    stats = rename_folders(temp_dir, dry_run=True)
    
    # Verify statistics
    assert stats['renamed'] == 1
    
    # Verify folder was NOT actually renamed
    assert old_folder.exists(), "Folder should NOT be renamed in dry-run mode"
    new_folder = temp_dir / "2023-02-20_February_20_2023_videos"
    assert not new_folder.exists()


def test_rename_multiple_folders(temp_dir):
    """Test that multiple folders with dates are renamed."""
    # Create multiple folders with dates
    folder1 = temp_dir / "March 10, 2023 photos"
    folder2 = temp_dir / "April 5, 2023 videos"
    folder3 = temp_dir / "May 1, 2023 documents"
    
    for folder in [folder1, folder2, folder3]:
        folder.mkdir()
    
    # Run the renaming
    stats = rename_folders(temp_dir, dry_run=False)
    
    # Verify statistics
    assert stats['renamed'] == 3
    
    # Verify all folders were renamed
    assert (temp_dir / "2023-03-10_March_10_2023_photos").exists()
    assert (temp_dir / "2023-04-05_April_5_2023_videos").exists()
    assert (temp_dir / "2023-05-01_May_1_2023_documents").exists()


def test_rename_skip_folders_without_date(temp_dir):
    """Test that folders without dates are not renamed."""
    # Create folders with and without dates
    folder_with_date = temp_dir / "June 15, 2023 photos"
    folder_without_date = temp_dir / "regular_folder"
    folder_other_format = temp_dir / "2023-06-15_already_formatted"
    
    for folder in [folder_with_date, folder_without_date, folder_other_format]:
        folder.mkdir()
    
    # Run the renaming
    stats = rename_folders(temp_dir, dry_run=False)
    
    # Verify statistics
    assert stats['renamed'] == 1
    assert stats['no_match'] == 2
    
    # Verify only folder with date was renamed
    assert (temp_dir / "2023-06-15_June_15_2023_photos").exists()
    assert folder_without_date.exists(), "Folder without date should not be renamed"
    assert folder_other_format.exists(), "Folder with different date format should not be renamed"


def test_rename_nested_folders(temp_dir):
    """Test that nested folders with dates are renamed."""
    # Create nested structure
    parent = temp_dir / "parent_folder"
    nested = parent / "July 1, 2023 nested"
    nested.mkdir(parents=True)
    
    # Create file in nested folder
    test_file = nested / "test.txt"
    test_file.write_text("test")
    
    # Run the renaming
    stats = rename_folders(temp_dir, dry_run=False)
    
    # Verify nested folder was renamed
    assert stats['renamed'] == 1
    new_nested = parent / "2023-07-01_July_1_2023_nested"
    assert new_nested.exists()
    assert (new_nested / "test.txt").exists()


def test_rename_output_file(temp_dir):
    """Test that renamed folders are written to output file."""
    # Create folders with dates
    folder1 = temp_dir / "August 10, 2023 photos"
    folder2 = temp_dir / "September 5, 2023 videos"
    
    for folder in [folder1, folder2]:
        folder.mkdir()
    
    # Create output file path
    output_file = temp_dir / "renamed_folders.txt"
    
    # Run the renaming
    stats = rename_folders(temp_dir, output_file=output_file, dry_run=False)
    
    # Verify output file was created
    assert output_file.exists()
    
    # Verify content
    content = output_file.read_text(encoding='utf-8')
    assert "August 10, 2023 photos" in content or "2023-08-10" in content
    assert "September 5, 2023 videos" in content or "2023-09-05" in content


def test_convert_date_format():
    """Test the date format conversion function."""
    # Test various date formats
    assert convert_date_format("January 1, 2023") == "2023-01-01"
    assert convert_date_format("February 28, 2023") == "2023-02-28"
    assert convert_date_format("December 31, 2022") == "2022-12-31"
    assert convert_date_format("March 15, 2024") == "2024-03-15"
    
    # Test invalid date format
    assert convert_date_format("invalid date") == ""
    assert convert_date_format("2023-01-01") == ""


def test_rename_folder_name_cleaning(temp_dir):
    """Test that folder names are cleaned properly (spaces, commas, etc.)."""
    # Create folder with various characters
    old_folder = temp_dir / "October 20, 2023 - photos"
    old_folder.mkdir()
    
    # Run the renaming
    stats = rename_folders(temp_dir, dry_run=False)
    
    # Verify folder was renamed with cleaned name
    assert stats['renamed'] == 1
    # Should have date prefix and cleaned name
    new_folder_name = list(temp_dir.glob("2023-10-20_*"))[0]
    assert new_folder_name.exists()
    assert "2023-10-20" in new_folder_name.name
    assert "," not in new_folder_name.name


def test_rename_empty_directory(temp_dir):
    """Test handling of empty directory."""
    # Create empty directory (no subdirectories)
    # Run the renaming
    stats = rename_folders(temp_dir, dry_run=False)
    
    # Verify no folders were processed
    assert stats['renamed'] == 0
    assert stats['no_match'] == 0


def test_rename_mixed_folders(temp_dir):
    """Test renaming when some folders have dates and some don't."""
    # Create mix of folders
    folder1 = temp_dir / "November 1, 2023 photos"
    folder2 = temp_dir / "regular_folder"
    folder3 = temp_dir / "December 25, 2023 holiday"
    folder4 = temp_dir / "another_regular"
    
    for folder in [folder1, folder2, folder3, folder4]:
        folder.mkdir()
    
    # Run the renaming
    stats = rename_folders(temp_dir, dry_run=False)
    
    # Verify statistics
    assert stats['renamed'] == 2
    assert stats['no_match'] == 2
    
    # Verify correct folders were renamed
    assert (temp_dir / "2023-11-01_November_1_2023_photos").exists()
    assert (temp_dir / "2023-12-25_December_25_2023_holiday").exists()
    assert folder2.exists()
    assert folder4.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

