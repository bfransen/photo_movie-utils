#!/usr/bin/env python3
"""
Rename folders based on date in the format "Month Day, Year".

This script recursively scans a source directory and renames folders that
contain dates in the format "Month Day, Year" to "YYYY-MM-DD" format.
"""

import argparse
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


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


def convert_date_format(original_date: str) -> str:
    """Convert date string from "Month Day, Year" to "YYYY-MM-DD".
    
    Args:
        original_date: Date string in format "Month Day, Year"
        
    Returns:
        Date string in format "YYYY-MM-DD"
    """
    try:
        date_object = datetime.strptime(original_date, "%B %d, %Y")
        return date_object.strftime("%Y-%m-%d")
    except ValueError as e:
        logging.debug(f"Failed to parse date '{original_date}': {e}")
        return ""


def rename_folders(source_path: Path, output_file: Optional[Path] = None,
                  dry_run: bool = False) -> dict:
    """Rename folders based on date in the format "Month Day, Year".
    
    Args:
        source_path: Root directory to scan recursively
        output_file: Optional file to write renamed folders information
        dry_run: If True, don't actually rename folders
        
    Returns:
        Dictionary with statistics
    """
    renamed_folders: List[Tuple[str, str]] = []
    no_match_folders: List[str] = []
    
    logging.info(f"Starting scan of {source_path}")
    logging.info(f"Dry run: {dry_run}")
    
    # Walk through directories (need to collect all first to avoid modifying while iterating)
    folders_to_rename: List[Tuple[Path, str]] = []
    
    for root, dirs, files in os.walk(source_path):
        root_path = Path(root)
        
        for folder in dirs:
            folder_path = root_path / folder
            
            # Extract date from the folder name using a regular expression
            match = re.search(r'(\b\w+ \d+, \d+\b)', folder)
            if match:
                original_date = match.group(0)
                new_date = convert_date_format(original_date)
                
                if new_date:
                    # Create new folder name
                    new_folder_name = f"{new_date}_{folder.replace(' ', '_')}"
                    new_folder_name = new_folder_name.replace(',', '')
                    new_folder_name = new_folder_name.replace('_-_', '_')
                    
                    folders_to_rename.append((folder_path, new_folder_name))
                    renamed_folders.append((str(folder_path), new_folder_name))
                else:
                    no_match_folders.append(str(folder_path))
            else:
                no_match_folders.append(str(folder_path))
    
    # Perform renaming (in reverse order to handle nested folders)
    folders_to_rename.reverse()
    
    for folder_path, new_folder_name in folders_to_rename:
        new_folder_path = folder_path.parent / new_folder_name
        
        if not dry_run:
            try:
                shutil.move(str(folder_path), str(new_folder_path))
                logging.info(f"Renamed: {folder_path} -> {new_folder_path}")
            except Exception as e:
                logging.error(f"Failed to rename {folder_path}: {e}")
        else:
            logging.info(f"[DRY RUN] Would rename: {folder_path} -> {new_folder_path}")
    
    # Write output file if specified
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for original, renamed in renamed_folders:
                    f.write(f"{original} -> {renamed}\n")
                if no_match_folders:
                    f.write("\n# Folders with no date match:\n")
                    for folder in no_match_folders:
                        f.write(f"No match - {folder}\n")
            logging.info(f"Renamed folders information written to {output_file}")
        except Exception as e:
            logging.error(f"Failed to write output file {output_file}: {e}")
    
    stats = {
        'processed': len(renamed_folders) + len(no_match_folders),
        'renamed': len(renamed_folders),
        'no_match': len(no_match_folders),
    }
    
    return stats


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Rename folders based on date in the format "Month Day, Year"',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to preview changes
  python rename_folders.py --source /path/to/folders --dry-run
  
  # Actually rename folders
  python rename_folders.py --source /path/to/folders
  
  # Rename folders and write log to file
  python rename_folders.py --source /path/to/folders --output renamed_folders.txt
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
        help='Output file for renamed folders information (optional)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without renaming folders'
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
    
    # Rename folders
    stats = rename_folders(args.source, args.output, args.dry_run)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Folders processed: {stats['processed']}")
    print(f"Folders renamed: {stats['renamed']}")
    print(f"Folders with no match: {stats['no_match']}")
    
    if args.dry_run:
        print("\nThis was a DRY RUN. No folders were actually renamed.")
    
    print("="*60)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
