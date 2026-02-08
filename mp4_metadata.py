"""
Set creation_time in MP4 container metadata.

Used by copy_mtime_to_ctime and convert_videos to ensure MP4 files have
correct creation date in their container metadata (read by ffprobe, organize_by_date, etc.).
"""

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Union


def set_mp4_creation_time(path: Path, timestamp: Union[datetime, float]) -> bool:
    """
    Set creation_time in MP4 container metadata using ffmpeg (in-place).

    Args:
        path: Path to the MP4 file.
        timestamp: Creation time as datetime or Unix timestamp (float).

    Returns:
        True if creation_time was set, False otherwise (e.g. ffmpeg not found).
    """
    if shutil.which("ffmpeg") is None:
        return False
    path = path.resolve()
    if path.suffix.lower() not in (".mp4", ".m4v"):
        return False
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(float(timestamp))
    else:
        dt = timestamp
    creation_time_str = dt.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        fd, temp_path = tempfile.mkstemp(
            suffix=path.suffix, dir=path.parent, prefix=".mp4_meta_"
        )
        os.close(fd)
        temp_path = Path(temp_path)
        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(path),
                    "-c",
                    "copy",
                    "-map",
                    "0",
                    "-metadata",
                    f"creation_time={creation_time_str}",
                    str(temp_path),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                return False
            temp_path.replace(path)
            return True
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
    except Exception:
        return False
