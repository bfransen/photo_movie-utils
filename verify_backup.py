#!/usr/bin/env python3
"""
Backup verification script.

Scans source and destination folders, matches folders by date (handling different
naming conventions), and verifies all source files exist in destination by checking
filename and size.
"""

import re
from datetime import datetime
from typing import Optional, Tuple


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

