"""Utilities for file storage and naming conventions.

This module provides helper functions for managing file names and storage
operations, ensuring consistent naming patterns across the application.
It handles slugification of names, generation of timestamped filenames,
and retrieval of the latest file versions from a directory.
"""

import datetime as dt
import re
import unicodedata
from pathlib import Path
from typing import Dict, List


def slugify(value: str) -> str:
    """Normalize a string to a URL-friendly slug.

    Converts the string to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    Args:
        value: The string to slugify.

    Returns:
        str: The slugified string.
    """
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


def generate_filename(name: str, last_modified: str | None = None) -> str:
    """Generate a standardized filename for a resource.

    The filename format is: `<slugified-name>@<timestamp>.csv`
    The timestamp format is Compact ISO 8601: `YYYYMMDDTHHMMSS`

    Args:
        name: The base name of the resource (e.g., "Tesouro Selic").
        last_modified: An optional ISO 8601 timestamp string representing
            the last modification time. If not provided or invalid, the
            current time is used.

    Returns:
        str: The generated filename.
    """
    name_slug = slugify(name)

    if last_modified:
        try:
            # CKAN returns ISO format: 2025-12-04T12:59:45.172801
            timestamp = dt.datetime.fromisoformat(last_modified)
            timestamp_str = timestamp.strftime("%Y%m%dT%H%M%S")
        except ValueError:
            # Fallback to current time
            timestamp_str = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    else:
        timestamp_str = dt.datetime.now().strftime("%Y%m%dT%H%M%S")

    return f"{name_slug}@{timestamp_str}.csv"


def get_latest_files(directory: Path) -> List[Path]:
    """Scan a directory and return only the latest version of each file group.

    Files are grouped by their slug (the part of the filename before the '@').
    For each group, only the file with the lexicographically largest timestamp
    is returned. This is useful for handling versioned files where multiple
    downloads of the same dataset might exist.

    Args:
        directory: The directory to scan for CSV files.

    Returns:
        List[Path]: A sorted list of paths to the latest version of each file.
    """
    if not directory.exists():
        return []

    files_map: Dict[str, Path] = {}

    for file_path in directory.glob("*.csv"):
        name = file_path.name
        if "@" not in name:
            continue

        # Split into slug and timestamp
        parts = name.split("@")
        slug = "@".join(parts[:-1])
        timestamp_part = parts[-1].replace(".csv", "")

        # If we haven't seen this slug or if this file is newer
        if slug not in files_map:
            files_map[slug] = file_path
        else:
            # Compare timestamps
            current_best = files_map[slug]
            current_ts = current_best.name.split("@")[-1].replace(".csv", "")

            if timestamp_part > current_ts:
                files_map[slug] = file_path

    return sorted(list(files_map.values()))


def get_latest_file(data_dir: Path, pattern: str) -> Path | None:
    """Find the latest file matching a specific pattern in a directory.

    This function searches for files matching the given glob pattern and
    returns the one with the latest timestamp suffix.

    Args:
        data_dir: The directory to search in.
        pattern: The glob pattern to match files (e.g., "investors*.csv").

    Returns:
        Path | None: The path to the latest file matching the pattern, or
            None if no matching files are found.
    """
    files = list(data_dir.glob(pattern))
    if not files:
        return None

    latest_file = None
    latest_ts = ""

    for f in files:
        if "@" not in f.name:
            continue

        parts = f.name.split("@")
        ts = parts[-1].replace(".csv", "")

        if ts > latest_ts:
            latest_ts = ts
            latest_file = f

    return latest_file
