# Photo & Movie Organization Utilities

Built with AI using Cursor.

## Overview

This collection of utilities helps organize and manage photo and movie files.

It was created in response to me having a hard drive with 4 TB of photos and videos on a 2012 iMac in the Photos app.  I wanted to move the collection to a modern non-Apple machine and have full control over the data.  Exporting from Photos resulted in folder names that were poorly named and included proprietaru mac metadata that needed cleaning.  

The scripts were used to move the data from Photos to a windows drive.

- **rename_folders.py**: Rename folders exported from Apple's Photos Mac app to standardized YYYY-MM-DD format.   This script can be used after files were exported from the Photos app.  

- **organize_by_date.py**: Organize files into dated folders based on EXIF/metadata.  This script is useful after copying photos and movies out of an iPhone.   The resulting files are not sorted into sub-folders.  This script puts them in dated sub-folders.

- **delete_by_filename.py**: Clean up mac metadata files (e.g., macOS `._` files).  I don't want these.  Someone might if they intend to rehydrate the files into a Mac OS.  

- **verify_backup.py**: Confirm that data in a photo collection with date centric folders produced by "rename_folders" and "organize_by_date" contain the complete collection of files found in source folders named in the Apple Photos format.   This script is used as a sanity check to make sure the above scripts didn't miss any data or delete any real files.   Also useful after I've been working in my photo library and realize I may have accidentally deleted data.

## Installation

```bash
pip install -r requirements.txt
```

### Requirements

- Python 3.7+
- Pillow (for EXIF extraction)
- mutagen (for video metadata)
- pytest (for running tests)

---

## organize_by_date.py

Recursively scans a source directory and copies files into dated folders organized by `YYYY-MM-DD` format. The script uses the earliest available date from:
- EXIF metadata (for images)
- Video metadata (for videos)
- File system timestamps (creation/modification time)

### Features

- **Pure Python**: No external binaries required (uses Pillow for EXIF, mutagen for video metadata)
- **Copy, don't move**: Original files remain untouched
- **Smart date detection**: Prioritizes EXIF/video metadata over file timestamps
- **Duplicate handling**: Skips files that already exist in destination (safe to re-run)
- **Comprehensive logging**: Logs all operations and errors
- **Dry-run mode**: Preview changes before actually copying files

### Usage

```bash
# Dry run to preview changes
python organize_by_date.py --source /path/to/photos --destination /path/to/organized --dry-run

# Actually copy files
python organize_by_date.py --source /path/to/photos --destination /path/to/organized

# Save log to file
python organize_by_date.py --source /path/to/photos --destination /path/to/organized --log organization.log

# Verbose logging
python organize_by_date.py --source /path/to/photos --destination /path/to/organized --verbose
```

### Command Line Options

- `--source`: Source directory to scan recursively (required)
- `--destination`: Destination directory where dated folders will be created (required)
- `--dry-run`: Preview changes without copying files
- `--log`: Path to log file (optional)
- `--verbose`: Enable verbose/debug logging

**Note:** The script processes all file types, not just images and videos. It uses file timestamps for files without EXIF or video metadata.

### Supported File Formats

**Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.heic`, `.heif`, `.raw`, `.cr2`, `.nef`, `.orf`, `.sr2`

**Videos**: `.mp4`, `.mov`, `.avi`, `.mkv`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.mpg`, `.mpeg`, `.3gp`, `.mts`, `.m2ts`

### Date Detection Priority

1. **Images**: EXIF `DateTimeOriginal` → `DateTimeDigitized` → `DateTime` → file timestamps
2. **Videos**: Metadata creation date → file timestamps
3. **Other files**: File creation time → modification time

### Output Structure

Files are organized into folders like:

```
destination/
├── 2020-01-15/
│   ├── IMG_001.jpg
│   └── vacation_video.mp4
├── 2020-03-22/
│   └── birthday.jpg
└── 2021-06-10/
    └── summer_trip.mov
```

### Notes

- The script **copies** files, it does not move them. Original files remain in place.
- Files that already exist in the destination are skipped (safe to re-run).
- All operations are logged, including errors.
- The script continues processing even if individual files fail.

---

## rename_folders.py

This script was designed to deal with the awful folder naming of photos exported from Apple's Photos Mac app.   The folders exported by Photos are named with the date at the end of the folder which makes them difficult to organize and sort by name.

This script renames the folders in-place.

Recursively scans a source directory and renames folders that contain dates in the format "Month Day, Year" (e.g., "January 15, 2023") to a standardized "YYYY-MM-DD" format with the original folder name preserved and added as a suffix.

### Features

- **Date format standardization**: Converts human-readable dates to ISO format
- **Preserves folder content**: Original folder name is preserved after the date prefix
- **Recursive scanning**: Processes nested folder structures
- **Dry-run mode**: Preview changes before renaming
- **Comprehensive logging**: Logs all rename operations

### Usage

```bash
# Dry run to preview changes
python rename_folders.py --source /path/to/folders --dry-run

# Actually rename folders
python rename_folders.py --source /path/to/folders

# Rename folders and write log to file
python rename_folders.py --source /path/to/folders --output renamed_folders.txt

# Verbose logging
python rename_folders.py --source /path/to/folders --verbose --log rename.log
```

### Command Line Options

- `--source`: Source directory to scan recursively (required)
- `--output`: Output file for renamed folders information (optional)
- `--dry-run`: Preview changes without renaming folders
- `--log`: Path to log file (optional)
- `--verbose`: Enable verbose logging

### Example

Before:
```
photos/
├── January 15, 2023 photos/
│   └── image1.jpg
└── February 20, 2023 videos/
    └── video1.mp4
```

After:
```
photos/
├── 2023-01-15_January_15_2023_photos/
│   └── image1.jpg
└── 2023-02-20_February_20_2023_videos/
    └── video1.mp4
```

### Notes

- Only folders matching the "Month Day, Year" format are renamed
- Folders already in YYYY-MM-DD format are skipped
- The script processes folders in reverse order to handle nested structures safely

---

## delete_by_filename.py

Recursively scans a source directory and deletes files that match specific criteria. Primarily designed to clean up system files like macOS `._` resource fork files that are 4KB or smaller.

### Features

- **Targeted cleanup**: Removes specific file patterns (e.g., `._*` files)
- **Size-based filtering**: Only deletes files under a specified size threshold
- **Recursive scanning**: Processes nested directory structures
- **Dry-run mode**: Preview changes before deleting
- **Safety logging**: Logs all deleted files for review

### Usage

```bash
# Dry run to preview changes
python delete_by_filename.py --source /path/to/files --dry-run

# Actually delete files
python delete_by_filename.py --source /path/to/files

# Delete files and write log to file
python delete_by_filename.py --source /path/to/files --output deleted_files.txt

# Verbose logging
python delete_by_filename.py --source /path/to/files --verbose --log delete.log
```

### Command Line Options

- `--source`: Source directory to scan recursively (required)
- `--output`: Output file for deleted files information (optional)
- `--dry-run`: Preview changes without deleting files
- `--log`: Path to log file (optional)
- `--verbose`: Enable verbose logging

### Notes

- **Use with caution**: This script permanently deletes files
- Always use `--dry-run` first to preview what will be deleted
- The script targets files starting with `._` and 4KB or smaller (typical macOS resource fork files)
- All deletions are logged for audit purposes

---

## verify_backup.py

Verifies that backup folders contain all files from source folders by matching folders by date and comparing file contents. Designed to verify that photo collections with date-centric folders (produced by `rename_folders.py` and `organize_by_date.py`) contain the complete collection of files found in source folders named in the Apple Photos format.

### Features

- **Date-based folder matching**: Automatically matches source and destination folders by date, handling different naming conventions
- **File verification**: Verifies files exist in destination by filename and size
- **Comprehensive logging**: Logs all scanning and verification operations
- **Detailed reporting**: Generates reports showing folder statistics and missing files
- **Flexible file filtering**: Option to ignore files that would be cleaned up by `delete_by_filename.py`
- **Subdirectory support**: Handles files in nested subdirectories within folders
- **Size mismatch detection**: Identifies files that exist but have different sizes

### Usage

```bash
# Basic verification
python verify_backup.py --source /path/to/source --destination /path/to/dest

# Ignore files that would be deleted by delete_by_filename script
python verify_backup.py --source /path/to/source --destination /path/to/dest --ignore-deleted

# Save log and report to files
python verify_backup.py --source /path/to/source --destination /path/to/dest --log verify.log --report report.txt

# Verbose logging
python verify_backup.py --source /path/to/source --destination /path/to/dest --verbose
```

### Command Line Options

- `--source`: Source directory containing folders to verify (required)
- `--destination`: Destination directory containing backup folders (required)
- `--ignore-deleted`: Ignore files that would be cleaned up by `delete_by_filename.py` script (files starting with `._` and < 4KB)
- `--log`: Path to log file (optional)
- `--report`: Path to report file (optional)
- `--verbose`: Enable verbose/debug logging

### How It Works

1. **Scans source folders**: Parses folder names in "Month Day, Year" format (e.g., "September 10, 2022")
2. **Scans destination folders**: Parses folder names in "YYYY-MM-DD" format (e.g., "2022-09-10")
3. **Matches by date**: Groups folders by their date and matches source to destination folders
4. **Verifies files**: Checks that all source files exist in destination folders with matching sizes
5. **Generates report**: Produces a detailed report of verification results

### Report Contents

The verification report includes:

- **Summary statistics**: Number of folders checked, matched, total files scanned
- **Folder details**: File counts per folder and match status
- **Missing files**: List of files not found in destination or with size mismatches
- **Unmatched folders**: Source folders with no matching destination folder

### Example Output

```
================================================================================
BACKUP VERIFICATION REPORT
================================================================================

SUMMARY
--------------------------------------------------------------------------------
Folders checked: 5
Folders fully matched: 4
Total source files scanned: 127
Total destination files scanned: 125
Missing or mismatched files: 2

FOLDER DETAILS
--------------------------------------------------------------------------------
Date: 2022-09-10
  Source: September 10, 2022
  Destination: 2022-09-10
  Source files: 25
  Destination files: 25
  Missing files: 0
  Status: ✓ MATCHED
...
```

### Notes

- The script matches folders by date, so source folders like "September 10, 2022" will match destination folders like "2022-09-10"
- Files are verified by both filename and size to detect corruption or incomplete copies
- The script exits with code 0 if all files are verified, or code 1 if issues are found (useful for automation)
- Month names in source folders are case-insensitive and support abbreviations
- The `--ignore-deleted` option is useful when source folders contain system files that were intentionally cleaned up in the destination

### Programmatic Usage

The script can also be used as a module for programmatic access to parsing functions:

```python
from verify_backup import parse_source_folder_name, parse_destination_folder_name

# Parse source folder
date, desc = parse_source_folder_name("September 10, 2022")
# Returns: (datetime(2022, 9, 10), None)

date, desc = parse_source_folder_name("Crescent Park - Surrey, BC, September 10, 2022")
# Returns: (datetime(2022, 9, 10), "Crescent Park - Surrey, BC")

# Parse destination folder
date, desc = parse_destination_folder_name("2022-09-10")
# Returns: (datetime(2022, 9, 10), None)

date, desc = parse_destination_folder_name("2022-09-10_CrescentPark-SurreyBC")
# Returns: (datetime(2022, 9, 10), "CrescentPark-SurreyBC")
```

---

## Testing

All scripts include comprehensive test suites. Run tests with:

```bash
pytest test_*.py -v
```

Or run tests for a specific script:

```bash
pytest test_organize_by_date.py -v
pytest test_rename_folders.py -v
pytest test_delete_by_filename.py -v
pytest test_verify_backup.py -v
```
