#!/usr/bin/env python3
"""
Organize files by date into YYYY-MM-DD folder structure.

This script recursively scans a source directory and copies files into
dated folders based on the earliest available date (EXIF metadata for images,
video metadata for videos, file timestamps for all other files).
"""

import argparse
import hashlib
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow not installed. EXIF extraction will be unavailable.")

try:
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


# Supported file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', 
                    '.heic', '.heif', '.raw', '.cr2', '.nef', '.orf', '.sr2'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', 
                    '.m4v', '.mpg', '.mpeg', '.3gp', '.mts', '.m2ts'}


def setup_logging(log_file: Optional[Path] = None, verbose: bool = False) -> None:
    """Configure logging to file and console."""
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file, mode='w', encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def get_exif_date(image_path: Path) -> Optional[datetime]:
    """Extract date from EXIF data of an image file.
    
    Returns the earliest available date from EXIF tags:
    - DateTimeOriginal
    - DateTimeDigitized
    - DateTime
    """
    if not PIL_AVAILABLE:
        return None
    
    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            if not exif:
                return None
            
            dates = []
            
            # Map of EXIF tag names to their IDs
            tag_map = {TAGS.get(k, k): k for k in exif.keys()}
            
            # Try DateTimeOriginal (tag 36867)
            if 'DateTimeOriginal' in tag_map:
                date_str = exif.get(tag_map['DateTimeOriginal'])
                if date_str:
                    dates.append(parse_exif_datetime(date_str))
            
            # Try DateTimeDigitized (tag 36868)
            if 'DateTimeDigitized' in tag_map:
                date_str = exif.get(tag_map['DateTimeDigitized'])
                if date_str:
                    dates.append(parse_exif_datetime(date_str))
            
            # Try DateTime (tag 306)
            if 'DateTime' in tag_map:
                date_str = exif.get(tag_map['DateTime'])
                if date_str:
                    dates.append(parse_exif_datetime(date_str))
            
            # Return the earliest date found
            valid_dates = [d for d in dates if d is not None]
            return min(valid_dates) if valid_dates else None
            
    except Exception as e:
        logging.debug(f"Failed to extract EXIF from {image_path}: {e}")
        return None


def parse_exif_datetime(date_str: str) -> Optional[datetime]:
    """Parse EXIF datetime string to datetime object.
    
    EXIF datetime format: 'YYYY:MM:DD HH:MM:SS'
    """
    try:
        return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
    except (ValueError, AttributeError):
        return None


def get_video_metadata_date(video_path: Path) -> Optional[datetime]:
    """Extract creation date from video file metadata using mutagen.
    
    Returns the earliest available date from metadata.
    """
    if not MUTAGEN_AVAILABLE:
        return None
    
    try:
        metadata = MutagenFile(str(video_path))
        if not metadata:
            return None
        
        dates = []
        
        # Try common date tags
        date_tags = ['date', 'creation_date', 'creationdate', 'creation time']
        for tag in date_tags:
            if tag in metadata:
                value = metadata[tag][0] if isinstance(metadata[tag], list) else metadata[tag]
                parsed = parse_video_datetime(str(value))
                if parsed:
                    dates.append(parsed)
        
        # Return the earliest date found
        return min(dates) if dates else None
        
    except Exception as e:
        logging.debug(f"Failed to extract metadata from {video_path}: {e}")
        return None


def parse_video_datetime(date_str: str) -> Optional[datetime]:
    """Parse various video datetime formats to datetime object."""
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y:%m:%d %H:%M:%S',
        '%Y-%m-%d',
        '%Y%m%d',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:len(fmt.replace('%', ''))], fmt)
        except (ValueError, IndexError):
            continue
    
    return None


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file.
    
    Args:
        file_path: Path to the file to hash
        
    Returns:
        Hexadecimal string representation of the hash
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logging.debug(f"Failed to hash {file_path}: {e}")
        return ""


def find_unique_filename(dest_folder: Path, base_name: str) -> Path:
    """Find a unique filename by appending numbers if needed.
    
    Args:
        dest_folder: Destination folder path
        base_name: Base filename (e.g., "photo.jpg")
        
    Returns:
        Path to a unique filename (e.g., "photo.jpg", "photo_1.jpg", "photo_2.jpg")
    """
    dest_file = dest_folder / base_name
    
    # If the file doesn't exist, return it as-is
    if not dest_file.exists():
        return dest_file
    
    # Split filename and extension
    stem = dest_file.stem
    suffix = dest_file.suffix
    
    # Try appending numbers until we find a unique name
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        dest_file = dest_folder / new_name
        if not dest_file.exists():
            return dest_file
        counter += 1
        
        # Safety limit to prevent infinite loops
        if counter > 10000:
            raise ValueError(f"Could not find unique filename for {base_name} after 10000 attempts")


def get_file_timestamps(file_path: Path) -> Tuple[datetime, datetime]:
    """Get file creation and modification timestamps.
    
    Returns (creation_time, modification_time) tuple.
    On Windows, creation_time is more reliable.
    """
    stat = file_path.stat()
    creation_time = datetime.fromtimestamp(stat.st_ctime)
    modification_time = datetime.fromtimestamp(stat.st_mtime)
    return creation_time, modification_time


def get_file_date(file_path: Path) -> datetime:
    """Get the earliest available date for a file.
    
    Priority order:
    1. EXIF data (for images)
    2. Video metadata (for videos)
    3. File creation time
    4. File modification time
    """
    # Try EXIF for images
    if file_path.suffix.lower() in IMAGE_EXTENSIONS:
        exif_date = get_exif_date(file_path)
        if exif_date:
            return exif_date
    
    # Try metadata for videos
    if file_path.suffix.lower() in VIDEO_EXTENSIONS:
        video_date = get_video_metadata_date(file_path)
        if video_date:
            return video_date
    
    # Fall back to file timestamps
    creation_time, modification_time = get_file_timestamps(file_path)
    return min(creation_time, modification_time)


def copy_file_to_dated_folder(source_file: Path, destination_root: Path, 
                               dry_run: bool = False) -> Tuple[bool, str]:
    """Copy a file to the appropriate dated folder.
    
    If a file with the same name exists, compares hashes to determine if it's
    the same file. If different, appends a number to create a unique filename.
    
    Returns (success, message) tuple.
    """
    try:
        # Get the date for the file
        file_date = get_file_date(source_file)
        date_folder = file_date.strftime('%Y-%m-%d')
        
        # Create destination path
        dest_folder = destination_root / date_folder
        dest_file = dest_folder / source_file.name
        
        # Check if file already exists
        if dest_file.exists():
            # Calculate hashes to see if files are identical
            source_hash = calculate_file_hash(source_file)
            dest_hash = calculate_file_hash(dest_file)
            
            # Only skip if both hashes were calculated successfully and they match
            if source_hash and dest_hash and source_hash == dest_hash:
                # Files are identical, skip
                return True, f"Skipped (already exists, identical): {dest_file}"
            else:
                # Files are different or hash calculation failed, find a unique filename
                dest_file = find_unique_filename(dest_folder, source_file.name)
        
        # Create destination folder if needed
        if not dry_run:
            dest_folder.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        if not dry_run:
            import shutil
            shutil.copy2(source_file, dest_file)
            if dest_file.name != source_file.name:
                return True, f"Copied to {dest_file} (renamed due to duplicate name)"
            else:
                return True, f"Copied to {dest_file}"
        else:
            if dest_file.name != source_file.name:
                return True, f"[DRY RUN] Would copy to {dest_file} (renamed due to duplicate name)"
            else:
                return True, f"[DRY RUN] Would copy to {dest_file}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def organize_files(source_dir: Path, destination_dir: Path, 
                  dry_run: bool = False) -> dict:
    """Recursively scan source directory and organize files by date.
    
    Returns statistics dictionary.
    """
    stats = {
        'processed': 0,
        'copied': 0,
        'skipped': 0,
        'failed': 0,
        'errors': []
    }
    
    logging.info(f"Starting scan of {source_dir}")
    logging.info(f"Destination: {destination_dir}")
    logging.info(f"Dry run: {dry_run}")
    logging.info("Processing all file types")
    
    # Recursively find all files
    for file_path in source_dir.rglob('*'):
        if not file_path.is_file():
            continue
        
        stats['processed'] += 1
        
        # Copy file to dated folder
        success, message = copy_file_to_dated_folder(
            file_path, destination_dir, dry_run
        )
        
        if success:
            if 'already exists' in message.lower() and 'identical' in message.lower():
                stats['skipped'] += 1
            else:
                stats['copied'] += 1
            logging.info(f"{file_path.name}: {message}")
        else:
            stats['failed'] += 1
            error_msg = f"{file_path}: {message}"
            stats['errors'].append(error_msg)
            logging.error(error_msg)
        
        # Progress indicator
        if stats['processed'] % 100 == 0:
            logging.info(f"Processed {stats['processed']} files...")
    
    return stats


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Organize files into dated folders (YYYY-MM-DD)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to preview changes
  python organize_by_date.py --source /path/to/files --destination /path/to/organized --dry-run
  
  # Actually copy files
  python organize_by_date.py --source /path/to/files --destination /path/to/organized
        """
    )
    
    parser.add_argument(
        '--source',
        type=Path,
        required=True,
        help='Source directory to scan recursively'
    )
    
    parser.add_argument(
        '--destination',
        type=Path,
        required=True,
        help='Destination directory where dated folders will be created'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without copying files'
    )
    
    parser.add_argument(
        '--log',
        type=Path,
        help='Path to log file (optional)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log, args.verbose)
    
    # Validate source directory
    if not args.source.exists():
        logging.error(f"Source directory does not exist: {args.source}")
        sys.exit(1)
    
    if not args.source.is_dir():
        logging.error(f"Source path is not a directory: {args.source}")
        sys.exit(1)
    
    # Create destination directory if needed
    if not args.dry_run:
        args.destination.mkdir(parents=True, exist_ok=True)
    
    # Organize files
    stats = organize_files(args.source, args.destination, args.dry_run)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Files processed: {stats['processed']}")
    print(f"Files copied: {stats['copied']}")
    print(f"Files skipped (already exist): {stats['skipped']}")
    print(f"Files failed: {stats['failed']}")
    
    if stats['errors']:
        print(f"\nErrors encountered ({len(stats['errors'])}):")
        for error in stats['errors']:
            print(f"  - {error}")
    
    if args.dry_run:
        print("\nThis was a DRY RUN. No files were actually copied.")
    
    print("="*60)
    
    # Exit with error code if there were failures
    sys.exit(1 if stats['failed'] > 0 else 0)


if __name__ == '__main__':
    main()

