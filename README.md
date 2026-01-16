# Photo & Movie Organization Utilities

Python scripts for managing and organizing photo and movie files.

Built with an AI first approach using Cursor.

## Overview

This collection of utilities helps organize and manage photo and movie files:

- **organize_by_date.py**: Organize files into dated folders based on EXIF/metadata
- **rename_folders.py**: Rename folders exported from Apple's Photos Mac app to standardized YYYY-MM-DD format
- **delete_by_filename.py**: Clean up system files (e.g., macOS `._` files)
- **verify_backup.py**: Confirm that data in a photo collection with date centric folders produced by "rename_folders" and "organize_by_date" contain the complete collection of files found in source folders named in the Apple Photos format.
- **verify_integrity.py**: Scan files, hash new or changed entries, store results in SQLite, and output JSON reports.

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

Utility module providing functions to parse and match folder names containing dates in different formats. Useful for comparing source and destination folder structures when verifying backups.

### Features

- **Flexible date parsing**: Handles multiple date formats
- **Source folder parsing**: Parses "Month Day, Year" format (e.g., "September 10, 2022")
- **Destination folder parsing**: Parses "YYYY-MM-DD" format (e.g., "2022-09-10")
- **Description extraction**: Extracts optional descriptions from folder names
- **Case-insensitive**: Handles various month name formats and abbreviations

### Functions

#### `parse_source_folder_name(folder_name: str)`

Parses source folder names with dates in "Month Day, Year" format.

**Supported formats:**
- `"September 10, 2022"`
- `"Crescent Park - Surrey, BC, September 10, 2022"`
- `"Description Text, September 10, 2022"`

**Returns:** Tuple of `(date, description)` where date is a datetime object and description is an optional string.

#### `parse_destination_folder_name(folder_name: str)`

Parses destination folder names with dates in "YYYY-MM-DD" format.

**Supported formats:**
- `"2022-09-10"`
- `"2022-09-10_CrescentPark-SurreyBC"`
- `"2022-09-10_Description"`

**Returns:** Tuple of `(date, description)` where date is a datetime object and description is an optional string.

### Usage

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

### Notes

- Month names are case-insensitive
- Supports both full month names and abbreviations (e.g., "Jan", "January")
- Returns `(None, None)` for invalid or unparseable folder names
- Validates dates (e.g., rejects February 30)

---

## verify_integrity.py

Scans a directory tree, computes SHA-256 hashes for new or changed files, and stores
them in a local SQLite database. Outputs a JSON report.

### Features

- **Incremental hashing**: Only new or changed files are hashed
- **SQLite storage**: Stores path, size, mtime, hash, and last_seen
- **Exclude file types**: Skip file extensions you do not want to track
- **JSON report**: Summary output to stdout or a report file

### Usage

```bash
# Index files and write a JSON report
python verify_integrity.py index --root /path/to/photos --db integrity.db --report report.json

# Exclude file types by extension
python verify_integrity.py index --root /path/to/photos --exclude-ext .tmp,.db --report report.json
```

### Notes

- The script does not follow symlinks.
- Use `--report` if you want a detailed JSON file with added/updated entries.

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
