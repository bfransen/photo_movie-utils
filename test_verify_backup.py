#!/usr/bin/env python3
"""
Unit tests for verify_backup.py date parsing functions.

Tests the date parsing functions for source and destination folder names.
"""

import logging
import tempfile
from pathlib import Path

import pytest
from datetime import datetime

from verify_backup import (
    generate_report,
    get_files_in_folder,
    parse_destination_folder_name,
    parse_source_folder_name,
    scan_destination_folders,
    scan_source_folders,
    should_ignore_file,
    verify_backup,
)

# Configure logging for tests to avoid noise
logging.basicConfig(level=logging.WARNING)


# Test data for parametrized tests
MONTH_NAMES = [
    ("January", 1), ("February", 2), ("March", 3), ("April", 4),
    ("May", 5), ("June", 6), ("July", 7), ("August", 8),
    ("September", 9), ("October", 10), ("November", 11), ("December", 12)
]

MONTH_ABBREVIATIONS = [
    ("Jan", 1), ("Feb", 2), ("Mar", 3), ("Apr", 4),
    ("Jun", 6), ("Jul", 7), ("Aug", 8),
    ("Sep", 9), ("Sept", 9), ("Oct", 10), ("Nov", 11), ("Dec", 12)
]


# Tests for parse_source_folder_name

def test_parse_source_folder_with_description_and_comma():
    """Test parsing source folder with description and comma separator."""
    folder_name = "Crescent Park - Surrey, BC, September 10, 2022"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2022, 9, 10)
    assert description == "Crescent Park - Surrey, BC"


def test_parse_source_folder_without_description():
    """Test parsing source folder without description."""
    folder_name = "September 10, 2022"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2022, 9, 10)
    assert description is None


def test_parse_source_folder_with_simple_description():
    """Test parsing source folder with simple description."""
    folder_name = "Description Text, September 10, 2022"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2022, 9, 10)
    assert description == "Description Text"


@pytest.mark.parametrize("month_name,month_num", MONTH_NAMES)
def test_parse_source_folder_all_month_names(month_name, month_num):
    """Test parsing with all full month names."""
    folder_name = f"{month_name} 15, 2023"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2023, month_num, 15)
    assert description is None


@pytest.mark.parametrize("abbrev,month_num", MONTH_ABBREVIATIONS)
def test_parse_source_folder_month_abbreviations(abbrev, month_num):
    """Test parsing with month abbreviations."""
    folder_name = f"{abbrev} 20, 2023"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2023, month_num, 20)
    assert description is None


@pytest.mark.parametrize("folder_name", [
    "september 10, 2022",
    "SEPTEMBER 10, 2022",
    "September 10, 2022",
    "SePtEmBeR 10, 2022",
])
def test_parse_source_folder_case_insensitive(folder_name):
    """Test that month names are case-insensitive."""
    date, description = parse_source_folder_name(folder_name)
    assert date == datetime(2022, 9, 10)


def test_parse_source_folder_single_digit_day():
    """Test parsing with single digit day."""
    folder_name = "September 5, 2022"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2022, 9, 5)


def test_parse_source_folder_double_digit_day():
    """Test parsing with double digit day."""
    folder_name = "September 25, 2022"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2022, 9, 25)


def test_parse_source_folder_description_with_dash():
    """Test parsing description that includes dashes."""
    folder_name = "Beach Trip - California, July 4, 2023"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2023, 7, 4)
    assert description == "Beach Trip - California"


def test_parse_source_folder_description_with_multiple_commas():
    """Test parsing description with multiple commas."""
    folder_name = "Family, Vacation, Photos, August 15, 2023"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2023, 8, 15)
    assert description == "Family, Vacation, Photos"


def test_parse_source_folder_invalid_folder_name():
    """Test parsing invalid folder name."""
    folder_name = "Invalid folder name"
    date, description = parse_source_folder_name(folder_name)
    
    assert date is None
    assert description is None


def test_parse_source_folder_empty_string():
    """Test parsing empty string."""
    date, description = parse_source_folder_name("")
    
    assert date is None
    assert description is None


def test_parse_source_folder_none_input():
    """Test parsing None input."""
    date, description = parse_source_folder_name(None)
    
    assert date is None
    assert description is None


@pytest.mark.parametrize("folder_name", [
    "February 30, 2023",
    "April 31, 2023",
])
def test_parse_source_folder_invalid_dates(folder_name):
    """Test that invalid dates return None."""
    date, description = parse_source_folder_name(folder_name)
    assert date is None


def test_parse_source_folder_year_in_past():
    """Test parsing dates in the past."""
    folder_name = "January 1, 2000"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2000, 1, 1)


def test_parse_source_folder_year_in_future():
    """Test parsing dates in the future."""
    folder_name = "December 31, 2099"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2099, 12, 31)


def test_parse_source_folder_description_with_trailing_spaces():
    """Test that trailing spaces in description are cleaned."""
    folder_name = "My Photos   , September 10, 2022"
    date, description = parse_source_folder_name(folder_name)
    
    assert date == datetime(2022, 9, 10)
    assert description == "My Photos"


# Tests for parse_destination_folder_name

def test_parse_destination_folder_with_description():
    """Test parsing destination folder with description."""
    folder_name = "2022-09-10_CrescentPark-SurreyBC"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2022, 9, 10)
    assert description == "CrescentPark-SurreyBC"


def test_parse_destination_folder_without_description():
    """Test parsing destination folder without description."""
    folder_name = "2022-09-10"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2022, 9, 10)
    assert description is None


def test_parse_destination_folder_with_simple_description():
    """Test parsing destination folder with simple description."""
    folder_name = "2022-09-10_Description"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2022, 9, 10)
    assert description == "Description"


@pytest.mark.parametrize("month", range(1, 13))
def test_parse_destination_folder_all_months(month):
    """Test parsing with all months."""
    folder_name = f"2023-{month:02d}-15"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2023, month, 15)
    assert description is None


def test_parse_destination_folder_single_digit_month_and_day_padded():
    """Test parsing with single digit month and day (padded to 2 digits)."""
    folder_name = "2023-01-05"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2023, 1, 5)


def test_parse_destination_folder_double_digit_month_and_day():
    """Test parsing with double digit month and day."""
    folder_name = "2023-12-31"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2023, 12, 31)


def test_parse_destination_folder_description_with_dashes():
    """Test parsing description that includes dashes."""
    folder_name = "2023-07-04_Beach-Trip-California"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2023, 7, 4)
    assert description == "Beach-Trip-California"


def test_parse_destination_folder_description_with_underscores():
    """Test parsing description that includes underscores."""
    folder_name = "2023-08-15_Family_Vacation_Photos"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2023, 8, 15)
    assert description == "Family_Vacation_Photos"


def test_parse_destination_folder_description_with_spaces():
    """Test parsing description that includes spaces."""
    folder_name = "2023-09-10_My Photo Collection"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2023, 9, 10)
    assert description == "My Photo Collection"


def test_parse_destination_folder_invalid_format():
    """Test parsing invalid format."""
    folder_name = "invalid-format"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date is None
    assert description is None


def test_parse_destination_folder_wrong_separator():
    """Test parsing with wrong separator (slash instead of dash)."""
    folder_name = "2022/09/10"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date is None
    assert description is None


def test_parse_destination_folder_empty_string():
    """Test parsing empty string."""
    date, description = parse_destination_folder_name("")
    
    assert date is None
    assert description is None


def test_parse_destination_folder_none_input():
    """Test parsing None input."""
    date, description = parse_destination_folder_name(None)
    
    assert date is None
    assert description is None


@pytest.mark.parametrize("folder_name", [
    "2023-02-30",
    "2023-04-31",
    "2023-00-15",
    "2023-13-15",
    "2023-09-00",
    "2023-09-32",
])
def test_parse_destination_folder_invalid_dates(folder_name):
    """Test that invalid dates return None."""
    date, description = parse_destination_folder_name(folder_name)
    assert date is None


def test_parse_destination_folder_year_in_past():
    """Test parsing dates in the past."""
    folder_name = "2000-01-01"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2000, 1, 1)


def test_parse_destination_folder_year_in_future():
    """Test parsing dates in the future."""
    folder_name = "2099-12-31"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2099, 12, 31)


def test_parse_destination_folder_description_with_trailing_spaces():
    """Test that trailing spaces in description are cleaned."""
    folder_name = "2023-09-10_My Photos   "
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2023, 9, 10)
    assert description == "My Photos"


def test_parse_destination_folder_description_empty_after_underscore():
    """Test that empty description after underscore returns None."""
    folder_name = "2023-09-10_"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2023, 9, 10)
    assert description is None


def test_parse_destination_folder_leap_year_february_29():
    """Test that valid leap year date (Feb 29) is accepted."""
    folder_name = "2024-02-29"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date == datetime(2024, 2, 29)


def test_parse_destination_folder_non_leap_year_february_29():
    """Test that invalid leap year date (Feb 29 in non-leap year) returns None."""
    folder_name = "2023-02-29"
    date, description = parse_destination_folder_name(folder_name)
    
    assert date is None


# Tests for should_ignore_file


def test_should_ignore_file_matches_criteria(tmp_path):
    """Test that files starting with ._ and < 4KB are ignored."""
    # Create a small file starting with ._
    test_file = tmp_path / "._test_file"
    test_file.write_bytes(b"x" * 1000)  # 1KB file
    
    assert should_ignore_file(test_file) is True


def test_should_ignore_file_too_large(tmp_path):
    """Test that files starting with ._ but >= 4KB are not ignored."""
    # Create a large file starting with ._
    test_file = tmp_path / "._large_file"
    test_file.write_bytes(b"x" * 5000)  # 5KB file
    
    assert should_ignore_file(test_file) is False


def test_should_ignore_file_normal_file(tmp_path):
    """Test that normal files are not ignored."""
    test_file = tmp_path / "normal_file.txt"
    test_file.write_bytes(b"x" * 1000)
    
    assert should_ignore_file(test_file) is False


def test_should_ignore_file_nonexistent():
    """Test that nonexistent files return False."""
    fake_path = Path("/nonexistent/path/file")
    assert should_ignore_file(fake_path) is False


# Tests for scan_source_folders


def test_scan_source_folders_valid_folders(tmp_path):
    """Test scanning source folders with valid date formats."""
    # Create folders with valid source date formats
    (tmp_path / "September 10, 2022").mkdir()
    (tmp_path / "January 5, 2023").mkdir()
    (tmp_path / "Invalid Folder").mkdir()
    
    folders = scan_source_folders(tmp_path)
    
    assert len(folders) == 2
    # Dates are normalized to midnight
    date_key_1 = datetime(2022, 9, 10).replace(hour=0, minute=0, second=0, microsecond=0)
    date_key_2 = datetime(2023, 1, 5).replace(hour=0, minute=0, second=0, microsecond=0)
    assert date_key_1 in folders
    assert date_key_2 in folders


def test_scan_source_folders_nonexistent_path():
    """Test scanning nonexistent path returns empty dict."""
    fake_path = Path("/nonexistent/path")
    folders = scan_source_folders(fake_path)
    
    assert len(folders) == 0


def test_scan_source_folders_empty_directory(tmp_path):
    """Test scanning empty directory returns empty dict."""
    folders = scan_source_folders(tmp_path)
    
    assert len(folders) == 0


def test_scan_source_folders_ignores_files(tmp_path):
    """Test that files are ignored, only directories are scanned."""
    (tmp_path / "September 10, 2022").mkdir()
    (tmp_path / "some_file.txt").write_text("test")
    
    folders = scan_source_folders(tmp_path)
    
    assert len(folders) == 1


# Tests for scan_destination_folders


def test_scan_destination_folders_valid_folders(tmp_path):
    """Test scanning destination folders with valid date formats."""
    # Create folders with valid destination date formats
    (tmp_path / "2022-09-10").mkdir()
    (tmp_path / "2023-01-05").mkdir()
    (tmp_path / "2022-09-10_Description").mkdir()
    (tmp_path / "Invalid Folder").mkdir()
    
    folders = scan_destination_folders(tmp_path)
    
    assert len(folders) == 2  # Two unique dates
    assert datetime(2022, 9, 10).replace(hour=0, minute=0, second=0, microsecond=0) in folders
    assert datetime(2023, 1, 5).replace(hour=0, minute=0, second=0, microsecond=0) in folders
    # Check that both 2022-09-10 folders are grouped together
    date_key = datetime(2022, 9, 10).replace(hour=0, minute=0, second=0, microsecond=0)
    assert len(folders[date_key]) == 2


def test_scan_destination_folders_nonexistent_path():
    """Test scanning nonexistent path returns empty dict."""
    fake_path = Path("/nonexistent/path")
    folders = scan_destination_folders(fake_path)
    
    assert len(folders) == 0


def test_scan_destination_folders_empty_directory(tmp_path):
    """Test scanning empty directory returns empty dict."""
    folders = scan_destination_folders(tmp_path)
    
    assert len(folders) == 0


# Tests for get_files_in_folder


def test_get_files_in_folder_basic(tmp_path):
    """Test getting files from a folder."""
    folder = tmp_path / "test_folder"
    folder.mkdir()
    
    (folder / "file1.txt").write_text("content1")
    (folder / "file2.txt").write_text("content2")
    
    files = get_files_in_folder(folder)
    
    assert len(files) == 2
    assert "file1.txt" in files
    assert "file2.txt" in files
    assert files["file1.txt"] > 0
    assert files["file2.txt"] > 0


def test_get_files_in_folder_with_subdirectories(tmp_path):
    """Test getting files including subdirectories."""
    folder = tmp_path / "test_folder"
    folder.mkdir()
    subfolder = folder / "subfolder"
    subfolder.mkdir()
    
    (folder / "file1.txt").write_text("content1")
    (subfolder / "file2.txt").write_text("content2")
    
    files = get_files_in_folder(folder)
    
    assert len(files) == 2
    assert "file1.txt" in files
    assert "subfolder/file2.txt" in files


def test_get_files_in_folder_ignores_deleted_files(tmp_path):
    """Test that deleted files are ignored when flag is set."""
    folder = tmp_path / "test_folder"
    folder.mkdir()
    
    # Create a file that should be ignored
    ignored_file = folder / "._ignored"
    ignored_file.write_bytes(b"x" * 1000)  # Small ._ file
    
    # Create a normal file
    normal_file = folder / "normal.txt"
    normal_file.write_text("content")
    
    files_without_ignore = get_files_in_folder(folder, ignore_deleted_files=False)
    files_with_ignore = get_files_in_folder(folder, ignore_deleted_files=True)
    
    assert len(files_without_ignore) == 2
    assert len(files_with_ignore) == 1
    assert "normal.txt" in files_with_ignore
    assert "._ignored" not in files_with_ignore


def test_get_files_in_folder_nonexistent_path():
    """Test getting files from nonexistent path returns empty dict."""
    fake_path = Path("/nonexistent/path")
    files = get_files_in_folder(fake_path)
    
    assert len(files) == 0


# Tests for verify_backup


def test_verify_backup_perfect_match(tmp_path):
    """Test verification when all files match."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    
    # Create matching folders
    source_folder = source / "September 10, 2022"
    dest_folder = dest / "2022-09-10"
    source_folder.mkdir()
    dest_folder.mkdir()
    
    # Create matching files
    (source_folder / "file1.txt").write_text("content1")
    (source_folder / "file2.txt").write_text("content2")
    (dest_folder / "file1.txt").write_text("content1")
    (dest_folder / "file2.txt").write_text("content2")
    
    results = verify_backup(source, dest)
    
    assert results['folders_checked'] == 1
    assert results['folders_matched'] == 1
    assert len(results['missing_files']) == 0
    assert len(results['folders_unmatched']) == 0
    assert results['total_source_files'] == 2
    assert results['total_dest_files'] == 2


def test_verify_backup_missing_files(tmp_path):
    """Test verification when files are missing."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    
    source_folder = source / "September 10, 2022"
    dest_folder = dest / "2022-09-10"
    source_folder.mkdir()
    dest_folder.mkdir()
    
    (source_folder / "file1.txt").write_text("content1")
    (source_folder / "file2.txt").write_text("content2")
    (dest_folder / "file1.txt").write_text("content1")
    # file2.txt is missing in destination
    
    results = verify_backup(source, dest)
    
    assert results['folders_checked'] == 1
    assert results['folders_matched'] == 0
    assert len(results['missing_files']) == 1
    assert results['missing_files'][0]['filename'] == "file2.txt"


def test_verify_backup_size_mismatch(tmp_path):
    """Test verification detects size mismatches."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    
    source_folder = source / "September 10, 2022"
    dest_folder = dest / "2022-09-10"
    source_folder.mkdir()
    dest_folder.mkdir()
    
    (source_folder / "file1.txt").write_text("content1")
    (dest_folder / "file1.txt").write_text("different content")  # Different size
    
    results = verify_backup(source, dest)
    
    assert len(results['missing_files']) == 1
    assert results['missing_files'][0]['reason'] == 'Size mismatch'
    assert 'dest_size' in results['missing_files'][0]


def test_verify_backup_unmatched_folder(tmp_path):
    """Test verification when source folder has no destination match."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    
    source_folder = source / "September 10, 2022"
    source_folder.mkdir()
    (source_folder / "file1.txt").write_text("content1")
    
    # No matching destination folder
    
    results = verify_backup(source, dest)
    
    assert results['folders_checked'] == 0  # Not checked because no match
    assert len(results['folders_unmatched']) == 1
    assert results['folders_unmatched'][0]['reason'] == 'No matching destination folder'


def test_verify_backup_ignores_deleted_files(tmp_path):
    """Test verification ignores deleted files when flag is set."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    
    source_folder = source / "September 10, 2022"
    dest_folder = dest / "2022-09-10"
    source_folder.mkdir()
    dest_folder.mkdir()
    
    # Create files including one that should be ignored
    (source_folder / "._ignored").write_bytes(b"x" * 1000)
    (source_folder / "normal.txt").write_text("content")
    (dest_folder / "normal.txt").write_text("content")
    # ._ignored is missing in dest, but should be ignored
    
    results = verify_backup(source, dest, ignore_deleted_files=True)
    
    assert results['folders_matched'] == 1
    assert len(results['missing_files']) == 0


def test_verify_backup_multiple_folders(tmp_path):
    """Test verification with multiple folders."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    
    # Create multiple date folders
    (source / "September 10, 2022").mkdir()
    (source / "January 5, 2023").mkdir()
    (dest / "2022-09-10").mkdir()
    (dest / "2023-01-05").mkdir()
    
    (source / "September 10, 2022" / "file1.txt").write_text("content")
    (source / "January 5, 2023" / "file2.txt").write_text("content")
    (dest / "2022-09-10" / "file1.txt").write_text("content")
    (dest / "2023-01-05" / "file2.txt").write_text("content")
    
    results = verify_backup(source, dest)
    
    assert results['folders_checked'] == 2
    assert results['folders_matched'] == 2
    assert len(results['missing_files']) == 0


def test_verify_backup_multiple_dest_folders_same_date(tmp_path):
    """Test verification where source folder matches multiple destination folders.
    
    Files should be considered found if they exist in at least one destination folder,
    not all of them.
    """
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    
    # Create one source folder and multiple destination folders for the same date
    (source / "September 10, 2022").mkdir()
    (dest / "2022-09-10_backup1").mkdir()
    (dest / "2022-09-10_backup2").mkdir()
    
    # Source folder has 3 files
    (source / "September 10, 2022" / "file1.txt").write_text("content1")
    (source / "September 10, 2022" / "file2.txt").write_text("content2")
    (source / "September 10, 2022" / "file3.txt").write_text("content3")
    
    # First destination folder has file1 and file2
    (dest / "2022-09-10_backup1" / "file1.txt").write_text("content1")
    (dest / "2022-09-10_backup1" / "file2.txt").write_text("content2")
    
    # Second destination folder has file2 and file3
    (dest / "2022-09-10_backup2" / "file2.txt").write_text("content2")
    (dest / "2022-09-10_backup2" / "file3.txt").write_text("content3")
    
    results = verify_backup(source, dest)
    
    # All files should be found (file1 in backup1, file2 in both, file3 in backup2)
    assert results['folders_checked'] == 1
    assert results['folders_matched'] == 1
    assert len(results['missing_files']) == 0


def test_verify_backup_multiple_dest_folders_missing_file(tmp_path):
    """Test verification where a file is missing from all destination folders."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    
    # Create one source folder and multiple destination folders for the same date
    (source / "September 10, 2022").mkdir()
    (dest / "2022-09-10_backup1").mkdir()
    (dest / "2022-09-10_backup2").mkdir()
    
    # Source folder has 3 files
    (source / "September 10, 2022" / "file1.txt").write_text("content1")
    (source / "September 10, 2022" / "file2.txt").write_text("content2")
    (source / "September 10, 2022" / "file3.txt").write_text("content3")
    
    # First destination folder has file1
    (dest / "2022-09-10_backup1" / "file1.txt").write_text("content1")
    
    # Second destination folder has file2
    (dest / "2022-09-10_backup2" / "file2.txt").write_text("content2")
    
    # file3 is missing from both destination folders
    
    results = verify_backup(source, dest)
    
    # file3 should be reported as missing
    assert results['folders_checked'] == 1
    assert results['folders_matched'] == 0
    assert len(results['missing_files']) == 1
    assert results['missing_files'][0]['filename'] == 'file3.txt'


# Tests for generate_report


def test_generate_report_success(tmp_path):
    """Test report generation for successful verification."""
    results = {
        'folders_checked': 2,
        'folders_matched': 2,
        'folders_unmatched': [],
        'folder_details': [
            {
                'date': '2022-09-10',
                'source_folder': '/source/September 10, 2022',
                'dest_folder': '/dest/2022-09-10',
                'source_file_count': 3,
                'dest_file_count': 3,
                'missing_count': 0,
                'matched': True
            }
        ],
        'missing_files': [],
        'total_source_files': 3,
        'total_dest_files': 3,
    }
    
    report = generate_report(results)
    
    assert "BACKUP VERIFICATION REPORT" in report
    assert "Folders checked: 2" in report
    assert "Folders fully matched: 2" in report
    assert "Total source files scanned: 3" in report
    assert "Missing or mismatched files: 0" in report
    assert "FOLDER DETAILS" in report
    assert "2022-09-10" in report
    assert "✓ MATCHED" in report


def test_generate_report_with_missing_files(tmp_path):
    """Test report generation with missing files."""
    results = {
        'folders_checked': 1,
        'folders_matched': 0,
        'folders_unmatched': [],
        'folder_details': [
            {
                'date': '2022-09-10',
                'source_folder': '/source/September 10, 2022',
                'dest_folder': '/dest/2022-09-10',
                'source_file_count': 2,
                'dest_file_count': 1,
                'missing_count': 1,
                'matched': False
            }
        ],
        'missing_files': [
            {
                'filename': 'missing.txt',
                'size': 1000,
                'source_folder': '/source/September 10, 2022',
                'dest_folder': '/dest/2022-09-10'
            }
        ],
        'total_source_files': 2,
        'total_dest_files': 1,
    }
    
    report = generate_report(results)
    
    assert "Missing or mismatched files: 1" in report
    assert "MISSING OR MISMATCHED FILES" in report
    assert "missing.txt" in report
    assert "✗ MISMATCHED" in report
    assert "File not found" in report


def test_generate_report_with_size_mismatch(tmp_path):
    """Test report generation with size mismatches."""
    results = {
        'folders_checked': 1,
        'folders_matched': 0,
        'folders_unmatched': [],
        'folder_details': [],
        'missing_files': [
            {
                'filename': 'mismatch.txt',
                'size': 1000,
                'dest_size': 2000,
                'source_folder': '/source/September 10, 2022',
                'dest_folder': '/dest/2022-09-10',
                'reason': 'Size mismatch'
            }
        ],
        'total_source_files': 1,
        'total_dest_files': 1,
    }
    
    report = generate_report(results)
    
    assert "mismatch.txt" in report
    assert "Size mismatch" in report
    assert "1,000 bytes" in report or "1,000" in report
    assert "2,000 bytes" in report or "2,000" in report


def test_generate_report_with_unmatched_folders(tmp_path):
    """Test report generation with unmatched folders."""
    results = {
        'folders_checked': 0,
        'folders_matched': 0,
        'folders_unmatched': [
            {
                'date': '2022-09-10',
                'source_folder': '/source/September 10, 2022',
                'reason': 'No matching destination folder'
            }
        ],
        'folder_details': [],
        'missing_files': [],
        'total_source_files': 0,
        'total_dest_files': 0,
    }
    
    report = generate_report(results)
    
    assert "UNMATCHED FOLDERS" in report
    assert "2022-09-10" in report
    assert "No matching destination folder" in report


def test_generate_report_writes_to_file(tmp_path):
    """Test that report can be written to a file."""
    results = {
        'folders_checked': 1,
        'folders_matched': 1,
        'folders_unmatched': [],
        'folder_details': [],
        'missing_files': [],
        'total_source_files': 1,
        'total_dest_files': 1,
    }
    
    report_file = tmp_path / "report.txt"
    report = generate_report(results, report_file)
    
    assert report_file.exists()
    assert report_file.read_text() == report
    assert "BACKUP VERIFICATION REPORT" in report_file.read_text()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
