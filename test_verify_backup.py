#!/usr/bin/env python3
"""
Unit tests for verify_backup.py date parsing functions.

Tests the date parsing functions for source and destination folder names.
"""

import pytest
from datetime import datetime

from verify_backup import parse_source_folder_name, parse_destination_folder_name


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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
