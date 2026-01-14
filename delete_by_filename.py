#!/usr/bin/env python3
"""
Delete files that start with ._ and are 4KB or under.

This script recursively scans a source directory and deletes files matching
the criteria (starting with ._ and size <= 4KB).
"""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional


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


def remove_bad_characters_from_filename(dir1: str, file: str, file_name_index: int, 
                                       file_path: Path, root: Path) -> Path:
    """Rename files with problematic characters in their names."""
    if "chat-media-video" in file:
        sanitized_file_path = root / dir1 / f"chat-media-video{file_name_index}"
        shutil.move(str(file_path), str(sanitized_file_path))
        file_path = sanitized_file_path
    return file_path


def delete_by_filename(source_path: Path, output_file: Optional[Path] = None, 
                      dry_run: bool = False) -> dict:
    """Delete files that start with ._ and are 4KB or under.
    
    Args:
        source_path: Root directory to scan recursively
        output_file: Optional file to write deleted files information
        dry_run: If True, don't actually delete files
        
    Returns:
        Dictionary with statistics
    """
    deleted_files: List[str] = []
    file_name_index = 1
    
    logging.info(f"Starting scan of {source_path}")
    logging.info(f"Dry run: {dry_run}")
    
    # Recursively walk through directories
    for root, dirs, files in os.walk(source_path):
        root_path = Path(root)
        
        for dir1 in dirs:
            dir_path = root_path / dir1
            for subroot, subdirs, subfiles in os.walk(dir_path):
                subroot_path = Path(subroot)
                
                for file in subfiles:
                    file_path = subroot_path / file
                    
                    # Handle bad characters in filename
                    file_path = remove_bad_characters_from_filename(
                        dir1, file, file_name_index, file_path, root_path
                    )
                    file_name_index += 1
                    
                    # Check if file matches deletion criteria
                    if file.startswith("._") and file_path.stat().st_size < 4500:
                        deleted_files.append(str(file_path))
                        
                        if not dry_run:
                            try:
                                file_path.unlink()
                                logging.info(f"Deleted: {file_path}")
                            except Exception as e:
                                logging.error(f"Failed to delete {file_path}: {e}")
                        else:
                            logging.info(f"[DRY RUN] Would delete: {file_path}")
    
    # Write output file if specified
    if output_file and deleted_files:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for name in deleted_files:
                    # Clean up special characters
                    cleaned_name = name.replace('\u2a31', '').replace('\u02bb', '')
                    f.write(f"{cleaned_name}\n")
            logging.info(f"Deleted files information written to {output_file}")
        except Exception as e:
            logging.error(f"Failed to write output file {output_file}: {e}")
    
    stats = {
        'processed': file_name_index - 1,
        'deleted': len(deleted_files),
    }
    
    return stats


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Delete files that start with ._ and are 4KB or under',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to preview changes
  python delete_by_filename.py --source /path/to/files --dry-run
  
  # Actually delete files
  python delete_by_filename.py --source /path/to/files
  
  # Delete files and write log to file
  python delete_by_filename.py --source /path/to/files --output deleted_files.txt
        """
    )
    
    parser.add_argument(
        '--source',
        type=Path,
        required=True,
        help='Source directory to scan recursively'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file for deleted files information (optional)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without deleting files'
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
    
    # Delete files
    stats = delete_by_filename(args.source, args.output, args.dry_run)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Files processed: {stats['processed']}")
    print(f"Files deleted: {stats['deleted']}")
    
    if args.dry_run:
        print("\nThis was a DRY RUN. No files were actually deleted.")
    
    print("="*60)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
