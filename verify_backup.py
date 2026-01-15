#!/usr/bin/env python3
"""
Backup verification script.

Scans source and destination folders, matches folders by date (handling different
naming conventions), and verifies all source files exist in destination by checking
filename and size.
"""

import argparse
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Month name mappings (full names and abbreviations)
MONTH_NAMES = {
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12,
}


def parse_source_folder_name(folder_name: str) -> Tuple[Optional[datetime], Optional[str]]:
    """Parse source folder name to extract date and description.
    
    Handles formats like:
    - "Crescent Park - Surrey, BC, September 10, 2022"
    - "September 10, 2022"
    - "Description Text, September 10, 2022"
    
    Args:
        folder_name: Source folder name string
        
    Returns:
        Tuple of (date, description) where:
        - date: datetime object with the extracted date, or None if parsing fails
        - description: string description extracted from folder name, or None if not found
    """
    if not folder_name:
        return None, None
    
    # Pattern to match: Month DD, YYYY
    # Handles full month names and abbreviations
    # Allows for optional leading text (description)
    month_pattern = '|'.join(MONTH_NAMES.keys())
    date_pattern = rf'\b({month_pattern})\s+(\d{{1,2}}),\s*(\d{{4}})\b'
    
    # Case-insensitive search
    match = re.search(date_pattern, folder_name, re.IGNORECASE)
    
    if not match:
        return None, None
    
    month_name = match.group(1).lower()
    day = int(match.group(2))
    year = int(match.group(3))
    
    # Get month number
    month = MONTH_NAMES.get(month_name)
    if not month:
        return None, None
    
    # Validate day (basic check)
    if day < 1 or day > 31:
        return None, None
    
    try:
        date = datetime(year, month, day)
    except ValueError:
        # Invalid date (e.g., February 30)
        return None, None
    
    # Extract description (everything before the date)
    date_start = match.start()
    description = folder_name[:date_start].strip()
    
    # Clean up description: remove trailing commas, dashes, spaces
    description = re.sub(r'[,\s-]+$', '', description)
    
    # Return None for description if it's empty or just whitespace
    if not description:
        description = None
    
    return date, description


def parse_destination_folder_name(folder_name: str) -> Tuple[Optional[datetime], Optional[str]]:
    """Parse destination folder name to extract date and optional description.
    
    Handles formats like:
    - "2022-09-10_CrescentPark-SurreyBC"
    - "2022-09-10"
    - "2022-09-10_Description"
    
    Args:
        folder_name: Destination folder name string
        
    Returns:
        Tuple of (date, description) where:
        - date: datetime object with the extracted date, or None if parsing fails
        - description: string description extracted from folder name, or None if not found
    """
    if not folder_name:
        return None, None
    
    # Pattern to match: YYYY-MM-DD optionally followed by underscore and description
    date_pattern = r'^(\d{4})-(\d{2})-(\d{2})(?:_(.*))?$'
    
    match = re.match(date_pattern, folder_name)
    
    if not match:
        return None, None
    
    year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    description = match.group(4)
    
    # Validate month and day ranges
    if month < 1 or month > 12:
        return None, None
    if day < 1 or day > 31:
        return None, None
    
    try:
        date = datetime(year, month, day)
    except ValueError:
        # Invalid date (e.g., 2022-02-30)
        return None, None
    
    # Clean up description if present
    if description:
        description = description.strip()
        if not description:
            description = None
    else:
        description = None
    
    return date, description


def should_ignore_file(file_path: Path) -> bool:
    """Check if a file should be ignored (matches delete_by_filename criteria).
    
    Files are ignored if they:
    - Start with '._'
    - Are 4KB or smaller (< 4500 bytes)
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file should be ignored, False otherwise
    """
    try:
        file_name = file_path.name
        file_size = file_path.stat().st_size
        return file_name.startswith("._") and file_size < 4500
    except (OSError, AttributeError):
        return False


def _scan_folders_by_date(
    root_path: Path, 
    parse_func, 
    folder_type: str = "folder"
) -> Dict[datetime, List[Path]]:
    """Scan directory and group folders by date using the provided parser function.
    
    Args:
        root_path: Root directory containing folders to scan
        parse_func: Function to parse folder names (parse_source_folder_name or parse_destination_folder_name)
        folder_type: Type description for logging messages (e.g., "source", "destination")
        
    Returns:
        Dictionary mapping dates to lists of folder paths
    """
    folders_by_date: Dict[datetime, List[Path]] = defaultdict(list)
    
    if not root_path.exists() or not root_path.is_dir():
        logging.warning(f"{folder_type.capitalize()} path does not exist or is not a directory: {root_path}")
        return folders_by_date
    
    for item in root_path.iterdir():
        if item.is_dir():
            date, _ = parse_func(item.name)
            if date:
                # Normalize date to midnight for matching
                date_key = date.replace(hour=0, minute=0, second=0, microsecond=0)
                folders_by_date[date_key].append(item)
            else:
                logging.debug(f"Skipping {folder_type} folder (could not parse date): {item.name}")
    
    return folders_by_date


def scan_source_folders(source_path: Path) -> Dict[datetime, List[Path]]:
    """Scan source directory and group folders by date.
    
    Args:
        source_path: Root directory containing source folders
        
    Returns:
        Dictionary mapping dates to lists of folder paths
    """
    return _scan_folders_by_date(source_path, parse_source_folder_name, "source")


def scan_destination_folders(dest_path: Path) -> Dict[datetime, List[Path]]:
    """Scan destination directory and group folders by date.
    
    Args:
        dest_path: Root directory containing destination folders
        
    Returns:
        Dictionary mapping dates to lists of folder paths
    """
    return _scan_folders_by_date(dest_path, parse_destination_folder_name, "destination")


def get_files_in_folder(folder_path: Path, ignore_deleted_files: bool = False) -> Dict[str, int]:
    """Get all files in a folder with their sizes.
    
    Args:
        folder_path: Path to folder to scan
        ignore_deleted_files: If True, ignore files matching delete_by_filename criteria
        
    Returns:
        Dictionary mapping filenames to file sizes
    """
    files: Dict[str, int] = {}
    
    if not folder_path.exists() or not folder_path.is_dir():
        return files
    
    for item in folder_path.rglob('*'):
        if item.is_file():
            if ignore_deleted_files and should_ignore_file(item):
                logging.debug(f"Ignoring file (matches delete_by_filename criteria): {item}")
                continue
            
            # Use relative path from folder_path as key to handle subdirectories
            rel_path = item.relative_to(folder_path)
            files[str(rel_path)] = item.stat().st_size
    
    return files


def verify_backup(source_path: Path, dest_path: Path, 
                  ignore_deleted_files: bool = False) -> Dict:
    """Verify that all source files exist in destination folders.
    
    Args:
        source_path: Root directory containing source folders
        dest_path: Root directory containing destination folders
        ignore_deleted_files: If True, ignore files matching delete_by_filename criteria
        
    Returns:
        Dictionary containing verification results and statistics
    """
    logging.info(f"Starting backup verification")
    logging.info(f"Source: {source_path}")
    logging.info(f"Ignore deleted files: {ignore_deleted_files}")
    
    # Scan folders
    logging.info("Scanning source folders...")
    source_folders = scan_source_folders(source_path)
    logging.info(f"Found {len(source_folders)} unique dates in source folders")
    
    logging.info("Scanning destination folders...")
    dest_folders = scan_destination_folders(dest_path)
    logging.info(f"Found {len(dest_folders)} unique dates in destination folders")
    
    # Results tracking
    results = {
        'folders_checked': 0,
        'folders_matched': 0,
        'folders_unmatched': [],
        'folder_details': [],
        'missing_files': [],
        'total_source_files': 0,
        'total_dest_files': 0,
    }
    
    # Match folders by date and verify files
    for date, source_folder_list in source_folders.items():
        date_str = date.strftime("%Y-%m-%d")
        logging.info(f"\nProcessing date: {date_str}")
        
        if date not in dest_folders:
            logging.warning(f"No destination folder found for date {date_str}")
            for src_folder in source_folder_list:
                results['folders_unmatched'].append({
                    'date': date_str,
                    'source_folder': str(src_folder),
                    'reason': 'No matching destination folder'
                })
            continue
        
        # Process each source folder for this date
        for src_folder in source_folder_list:
            results['folders_checked'] += 1
            logging.info(f"  Checking source folder: {src_folder.name}")
            
            # Get all files in source folder
            source_files = get_files_in_folder(src_folder, ignore_deleted_files)
            source_file_count = len(source_files)
            results['total_source_files'] += source_file_count
            logging.info(f"    Found {source_file_count} files in source folder")
            
            # Check each destination folder for this date
            dest_folder_list = dest_folders[date]
            folder_matched = False
            
            for dest_folder in dest_folder_list:
                logging.info(f"    Checking destination folder: {dest_folder.name}")
                
                # Get all files in destination folder
                dest_files = get_files_in_folder(dest_folder, ignore_deleted_files)
                dest_file_count = len(dest_files)
                results['total_dest_files'] += dest_file_count
                logging.info(f"      Found {dest_file_count} files in destination folder")
                
                # Find missing files
                missing = []
                for filename, size in source_files.items():
                    if filename not in dest_files:
                        missing.append({
                            'filename': filename,
                            'size': size,
                            'source_folder': str(src_folder),
                            'dest_folder': str(dest_folder)
                        })
                    elif dest_files[filename] != size:
                        # File exists but size mismatch
                        missing.append({
                            'filename': filename,
                            'size': size,
                            'dest_size': dest_files[filename],
                            'source_folder': str(src_folder),
                            'dest_folder': str(dest_folder),
                            'reason': 'Size mismatch'
                        })
                
                if not missing:
                    folder_matched = True
                    results['folders_matched'] += 1
                    logging.info(f"      ✓ All files verified in {dest_folder.name}")
                else:
                    logging.warning(f"      ✗ {len(missing)} files missing or mismatched in {dest_folder.name}")
                    results['missing_files'].extend(missing)
                
                # Store folder details
                results['folder_details'].append({
                    'date': date_str,
                    'source_folder': str(src_folder),
                    'dest_folder': str(dest_folder),
                    'source_file_count': source_file_count,
                    'dest_file_count': dest_file_count,
                    'missing_count': len(missing),
                    'matched': len(missing) == 0
                })
            
            if not folder_matched and dest_folder_list:
                logging.warning(f"  Source folder {src_folder.name} did not fully match any destination folder")
    
    return results


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


def generate_report(results: Dict, report_file: Optional[Path] = None) -> str:
    """Generate a text report from verification results.
    
    Args:
        results: Dictionary containing verification results
        report_file: Optional file path to write report to
        
    Returns:
        Report as a string
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("BACKUP VERIFICATION REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # Summary statistics
    report_lines.append("SUMMARY")
    report_lines.append("-" * 80)
    report_lines.append(f"Folders checked: {results['folders_checked']}")
    report_lines.append(f"Folders fully matched: {results['folders_matched']}")
    report_lines.append(f"Total source files scanned: {results['total_source_files']}")
    report_lines.append(f"Total destination files scanned: {results['total_dest_files']}")
    report_lines.append(f"Missing or mismatched files: {len(results['missing_files'])}")
    report_lines.append("")
    
    # Folder details
    if results['folder_details']:
        report_lines.append("FOLDER DETAILS")
        report_lines.append("-" * 80)
        for detail in results['folder_details']:
            status = "✓ MATCHED" if detail['matched'] else "✗ MISMATCHED"
            report_lines.append(f"Date: {detail['date']}")
            report_lines.append(f"  Source: {Path(detail['source_folder']).name}")
            report_lines.append(f"  Destination: {Path(detail['dest_folder']).name}")
            report_lines.append(f"  Source files: {detail['source_file_count']}")
            report_lines.append(f"  Destination files: {detail['dest_file_count']}")
            report_lines.append(f"  Missing files: {detail['missing_count']}")
            report_lines.append(f"  Status: {status}")
            report_lines.append("")
    
    # Missing files
    if results['missing_files']:
        report_lines.append("MISSING OR MISMATCHED FILES")
        report_lines.append("-" * 80)
        for missing in results['missing_files']:
            report_lines.append(f"File: {missing['filename']}")
            report_lines.append(f"  Source folder: {Path(missing['source_folder']).name}")
            report_lines.append(f"  Destination folder: {Path(missing['dest_folder']).name}")
            report_lines.append(f"  Source size: {missing['size']:,} bytes")
            if 'dest_size' in missing:
                report_lines.append(f"  Destination size: {missing['dest_size']:,} bytes")
                report_lines.append(f"  Reason: {missing.get('reason', 'Size mismatch')}")
            else:
                report_lines.append(f"  Reason: File not found")
            report_lines.append("")
    
    # Unmatched folders
    if results['folders_unmatched']:
        report_lines.append("UNMATCHED FOLDERS")
        report_lines.append("-" * 80)
        for unmatched in results['folders_unmatched']:
            report_lines.append(f"Date: {unmatched['date']}")
            report_lines.append(f"  Source folder: {Path(unmatched['source_folder']).name}")
            report_lines.append(f"  Reason: {unmatched['reason']}")
            report_lines.append("")
    
    report_lines.append("=" * 80)
    
    report_text = "\n".join(report_lines)
    
    if report_file:
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logging.info(f"Report written to {report_file}")
        except Exception as e:
            logging.error(f"Failed to write report file {report_file}: {e}")
    
    return report_text


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Verify backup by comparing source and destination folders',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic verification
  python verify_backup.py --source /path/to/source --destination /path/to/dest
  
  # Ignore files that would be deleted by delete_by_filename script
  python verify_backup.py --source /path/to/source --destination /path/to/dest --ignore-deleted
  
  # Save log and report to files
  python verify_backup.py --source /path/to/source --destination /path/to/dest --log verify.log --report report.txt
        """
    )
    
    parser.add_argument(
        '--source',
        type=Path,
        required=True,
        help='Source directory containing folders to verify'
    )
    
    parser.add_argument(
        '--destination',
        type=Path,
        required=True,
        help='Destination directory containing backup folders'
    )
    
    parser.add_argument(
        '--ignore-deleted',
        action='store_true',
        help='Ignore files that would be cleaned up by delete_by_filename script (._* files < 4KB)'
    )
    
    parser.add_argument(
        '--log',
        type=Path,
        help='Path to log file (optional)'
    )
    
    parser.add_argument(
        '--report',
        type=Path,
        help='Path to report file (optional)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log, args.verbose)
    
    # Validate directories
    if not args.source.exists():
        logging.error(f"Source directory does not exist: {args.source}")
        sys.exit(1)
    
    if not args.source.is_dir():
        logging.error(f"Source path is not a directory: {args.source}")
        sys.exit(1)
    
    if not args.destination.exists():
        logging.error(f"Destination directory does not exist: {args.destination}")
        sys.exit(1)
    
    if not args.destination.is_dir():
        logging.error(f"Destination path is not a directory: {args.destination}")
        sys.exit(1)
    
    # Run verification
    try:
        results = verify_backup(args.source, args.destination, args.ignore_deleted)
        
        # Generate and display report
        report_text = generate_report(results, args.report)
        
        # Print report to console
        print("\n" + report_text)
        
        # Exit with appropriate code
        if results['missing_files'] or results['folders_unmatched']:
            logging.warning("Verification completed with issues found")
            sys.exit(1)
        else:
            logging.info("Verification completed successfully - all files verified")
            sys.exit(0)
            
    except Exception as e:
        logging.error(f"Error during verification: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

