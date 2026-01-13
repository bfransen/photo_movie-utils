# Photo & Movie Organization Utilities

Python scripts for managing and organizing photo and movie files.

Built with an AI first approach using Cursor.

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

### Installation

```bash
pip install -r requirements.txt
```

### Usage

#### Basic Usage

```bash
# Dry run to preview changes
python organize_by_date.py --source /path/to/photos --destination /path/to/organized --dry-run

# Actually copy files
python organize_by_date.py --source /path/to/photos --destination /path/to/organized
```

#### Advanced Usage

```bash
# Process only specific file types
python organize_by_date.py \
    --source /path/to/photos \
    --destination /path/to/organized \
    --extensions .jpg .png .mp4 .mov

# Save log to file
python organize_by_date.py \
    --source /path/to/photos \
    --destination /path/to/organized \
    --log organization.log

# Verbose logging
python organize_by_date.py \
    --source /path/to/photos \
    --destination /path/to/organized \
    --verbose
```

### Command Line Options

- `--source`: Source directory to scan recursively (required)
- `--destination`: Destination directory where dated folders will be created (required)
- `--dry-run`: Preview changes without copying files
- `--extensions`: File extensions to process (default: all image and video formats)
- `--log`: Path to log file (optional)
- `--verbose`: Enable verbose/debug logging

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

### Requirements

- Python 3.7+
- Pillow (for EXIF extraction)
- mutagen (for video metadata)

