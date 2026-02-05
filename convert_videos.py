#!/usr/bin/env python3
"""
Convert a folder of video files to a new format using HandBrakeCLI.

This script filters files by extension, converts matching videos using a
HandBrake preset file, and preserves timestamps based on metadata (when
available) or filesystem creation time.
"""

import argparse
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

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
    print("Warning: mutagen not installed. Video metadata extraction will be unavailable.")

IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
    '.heic', '.heif', '.raw', '.cr2', '.nef', '.orf', '.sr2'
}


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


def normalize_extensions(values: Sequence[str]) -> List[str]:
    """Normalize and deduplicate extensions (e.g. ['mp4', '.MOV'] -> ['.mp4', '.mov'])."""
    extensions = []
    for value in values:
        if not value:
            continue
        parts = [p.strip() for p in value.split(',')]
        for part in parts:
            if not part:
                continue
            ext = part.lower()
            if not ext.startswith('.'):
                ext = f".{ext}"
            if ext not in extensions:
                extensions.append(ext)
    return extensions


def normalize_extension(value: str) -> str:
    """Normalize a single extension (e.g. 'mp4' -> '.mp4')."""
    ext = value.strip().lower()
    if not ext.startswith('.'):
        ext = f".{ext}"
    return ext


def iter_source_files(source_dir: Path, recursive: bool) -> Iterable[Path]:
    """Yield files from the source directory."""
    if recursive:
        iterator = source_dir.rglob('*')
    else:
        iterator = source_dir.glob('*')

    for path in iterator:
        if path.is_file():
            yield path


def parse_exif_datetime(date_str: str) -> Optional[datetime]:
    """Parse EXIF datetime string to datetime object."""
    try:
        return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
    except (ValueError, AttributeError):
        return None


def get_exif_date(image_path: Path) -> Optional[datetime]:
    """Extract date from EXIF data of an image file."""
    if not PIL_AVAILABLE:
        return None

    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            if not exif:
                return None

            dates = []
            tag_map = {TAGS.get(k, k): k for k in exif.keys()}

            for tag_name in ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime'):
                if tag_name in tag_map:
                    date_str = exif.get(tag_map[tag_name])
                    if date_str:
                        parsed = parse_exif_datetime(date_str)
                        if parsed:
                            dates.append(parsed)

            return min(dates) if dates else None
    except Exception as exc:
        logging.debug(f"Failed to extract EXIF from {image_path}: {exc}")
        return None


def parse_video_datetime(date_str: str) -> Optional[datetime]:
    """Parse various video datetime formats to datetime object."""
    sample_date = datetime(2000, 1, 2, 3, 4, 5)
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y:%m:%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d',
        '%Y%m%d',
    ]

    for fmt in formats:
        try:
            expected_len = len(sample_date.strftime(fmt))
            return datetime.strptime(date_str[:expected_len], fmt)
        except (ValueError, IndexError):
            continue

    return None


def get_video_metadata_date(video_path: Path) -> Optional[datetime]:
    """Extract creation date from video file metadata using mutagen."""
    if not MUTAGEN_AVAILABLE:
        return None

    try:
        metadata = MutagenFile(str(video_path))
        if not metadata:
            return None

        dates = []
        date_tags = ['date', 'creation_date', 'creationdate', 'creation time']
        for tag in date_tags:
            if tag in metadata:
                value = metadata[tag][0] if isinstance(metadata[tag], list) else metadata[tag]
                parsed = parse_video_datetime(str(value))
                if parsed:
                    dates.append(parsed)

        return min(dates) if dates else None
    except Exception as exc:
        logging.debug(f"Failed to extract metadata from {video_path}: {exc}")
        return None


def get_filesystem_creation_time(file_path: Path) -> datetime:
    """Get best-effort filesystem creation time for a file."""
    stat = file_path.stat()
    if hasattr(stat, 'st_birthtime'):
        return datetime.fromtimestamp(stat.st_birthtime)

    if os.name == 'nt':
        return datetime.fromtimestamp(stat.st_ctime)

    # On Unix, st_ctime is metadata change time; fall back to mtime.
    return datetime.fromtimestamp(stat.st_mtime)


def get_preferred_timestamp(file_path: Path) -> Tuple[datetime, str]:
    """Return the best available timestamp and its source."""
    metadata_date = get_video_metadata_date(file_path)
    if metadata_date:
        return metadata_date, 'metadata'

    if file_path.suffix.lower() in IMAGE_EXTENSIONS:
        exif_date = get_exif_date(file_path)
        if exif_date:
            return exif_date, 'exif'

    return get_filesystem_creation_time(file_path), 'filesystem'


def apply_timestamps(target_path: Path, timestamp: datetime) -> None:
    """Apply the timestamp to the output file (mtime/atime)."""
    epoch = timestamp.timestamp()
    os.utime(target_path, (epoch, epoch))


def find_preset_names(data) -> List[str]:
    """Recursively find preset names in a HandBrake preset JSON structure."""
    names: List[str] = []
    if isinstance(data, dict):
        preset_name = data.get('PresetName')
        if isinstance(preset_name, str):
            names.append(preset_name)
        for value in data.values():
            if isinstance(value, (dict, list)):
                names.extend(find_preset_names(value))
    elif isinstance(data, list):
        for item in data:
            names.extend(find_preset_names(item))
    return names


def load_preset_names(config_path: Path) -> List[str]:
    """Load preset names from a HandBrake preset file."""
    try:
        data = json.loads(config_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Preset file is not valid JSON: {exc}") from exc

    names = find_preset_names(data)
    seen = set()
    unique_names = []
    for name in names:
        if name not in seen:
            unique_names.append(name)
            seen.add(name)

    if not unique_names:
        raise ValueError("No presets found in the provided config file.")

    return unique_names


def ensure_handbrake_cli(handbrake_cli: str) -> None:
    """Verify that HandBrakeCLI is available."""
    resolved = shutil.which(handbrake_cli)
    if not resolved:
        raise FileNotFoundError(
            f"HandBrakeCLI not found: {handbrake_cli}. Install HandBrakeCLI or "
            "provide --handbrake-cli with the correct path."
        )


def build_output_path(source_file: Path, source_root: Path,
                      destination_root: Path, output_extension: str) -> Path:
    """Build the output file path while preserving relative structure."""
    relative = source_file.relative_to(source_root)
    output_relative = relative.with_suffix(output_extension)
    return destination_root / output_relative


def build_handbrake_command(
    handbrake_cli: str,
    input_path: Path,
    output_path: Path,
    preset_name: str,
    preset_file: Optional[Path],
    handbrake_format: Optional[str],
    extra_args: Sequence[str],
) -> List[str]:
    """Build the HandBrakeCLI command."""
    command = [handbrake_cli, '-i', str(input_path), '-o', str(output_path)]
    if preset_file:
        command.extend(['--preset-import-file', str(preset_file)])
    if preset_name:
        command.extend(['--preset', preset_name])
    if handbrake_format:
        command.extend(['--format', handbrake_format])
    if extra_args:
        command.extend(extra_args)
    return command


def is_subpath(path: Path, parent: Path) -> bool:
    """Return True if path is within parent."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def convert_videos(
    source_dir: Path,
    destination_dir: Path,
    extensions: Sequence[str],
    output_extension: str,
    preset_file: Path,
    preset_name: str,
    handbrake_cli: str,
    handbrake_format: Optional[str],
    extra_args: Sequence[str],
    recursive: bool,
    overwrite: bool,
    dry_run: bool,
) -> dict:
    """Convert videos in the source folder to a new format."""
    stats = {
        'scanned': 0,
        'matched': 0,
        'converted': 0,
        'skipped': 0,
        'failed': 0,
        'errors': [],
    }

    extensions_set = set(extensions)
    destination_in_source = is_subpath(destination_dir, source_dir)

    for file_path in iter_source_files(source_dir, recursive):
        stats['scanned'] += 1

        if destination_in_source and is_subpath(file_path, destination_dir):
            continue

        if file_path.suffix.lower() not in extensions_set:
            continue

        stats['matched'] += 1
        output_path = build_output_path(
            file_path, source_dir, destination_dir, output_extension
        )

        if output_path.exists() and not overwrite:
            stats['skipped'] += 1
            logging.info(f"Skipped (exists): {output_path}")
            continue

        timestamp, timestamp_source = get_preferred_timestamp(file_path)

        if dry_run:
            stats['converted'] += 1
            logging.info(
                f"[DRY RUN] Would convert {file_path} -> {output_path} "
                f"(timestamp: {timestamp_source})"
            )
            continue

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            command = build_handbrake_command(
                handbrake_cli=handbrake_cli,
                input_path=file_path,
                output_path=output_path,
                preset_name=preset_name,
                preset_file=preset_file,
                handbrake_format=handbrake_format,
                extra_args=extra_args,
            )

            logging.debug(f"Running HandBrakeCLI: {' '.join(command)}")
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                error_message = (
                    f"HandBrake failed for {file_path} (exit {result.returncode})."
                )
                if result.stderr:
                    error_message += f" stderr: {result.stderr.strip()}"
                raise RuntimeError(error_message)

            if result.stdout:
                logging.debug(result.stdout.strip())

            apply_timestamps(output_path, timestamp)
            stats['converted'] += 1
            logging.info(
                f"Converted {file_path} -> {output_path} "
                f"(timestamp: {timestamp_source})"
            )
        except Exception as exc:
            stats['failed'] += 1
            error_msg = f"{file_path}: {exc}"
            stats['errors'].append(error_msg)
            logging.error(error_msg)

    return stats


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert video files using HandBrakeCLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert_videos.py --source /path/to/videos --destination /path/to/output \\
    --extensions mp4 mov --output-extension mp4 \\
    --handbrake-config /path/to/presets.json --preset-name "My Preset"

  python convert_videos.py --source /path/to/videos --destination /path/to/output \\
    --extensions mp4,mov --output-extension mkv \\
    --handbrake-config /path/to/presets.json --preset-name "My Preset" --recursive
        """
    )

    parser.add_argument(
        '--source',
        type=Path,
        required=True,
        help='Source directory containing video files'
    )
    parser.add_argument(
        '--destination',
        type=Path,
        required=True,
        help='Destination directory for converted videos'
    )
    parser.add_argument(
        '--extensions',
        nargs='+',
        required=True,
        help='File extensions to convert (e.g. mp4 mov or "mp4,mov")'
    )
    parser.add_argument(
        '--output-extension',
        required=True,
        help='Output file extension (e.g. mp4, mkv)'
    )
    parser.add_argument(
        '--handbrake-config',
        type=Path,
        required=True,
        help='Path to HandBrake preset JSON file'
    )
    parser.add_argument(
        '--preset-name',
        help='Preset name to use. If omitted, the first preset in the config file is used.'
    )
    parser.add_argument(
        '--handbrake-cli',
        default='HandBrakeCLI',
        help='Path to HandBrakeCLI binary (default: HandBrakeCLI)'
    )
    parser.add_argument(
        '--format',
        dest='handbrake_format',
        help='Optional HandBrake output format (e.g. av_mp4, av_mkv)'
    )
    parser.add_argument(
        '--handbrake-args',
        default='',
        help='Additional HandBrakeCLI arguments (quoted string)'
    )
    parser.add_argument(
        '--recursive',
        action='store_true',
        help='Recursively scan subdirectories'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing output files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview conversions without running HandBrakeCLI'
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

    setup_logging(args.log, args.verbose)

    if not args.source.exists():
        logging.error(f"Source directory does not exist: {args.source}")
        sys.exit(1)
    if not args.source.is_dir():
        logging.error(f"Source path is not a directory: {args.source}")
        sys.exit(1)

    if not args.handbrake_config.exists():
        logging.error(f"HandBrake config file does not exist: {args.handbrake_config}")
        sys.exit(1)
    if not args.handbrake_config.is_file():
        logging.error(f"HandBrake config path is not a file: {args.handbrake_config}")
        sys.exit(1)

    extensions = normalize_extensions(args.extensions)
    if not extensions:
        logging.error("No valid extensions provided.")
        sys.exit(1)

    output_extension = normalize_extension(args.output_extension)

    try:
        preset_names = load_preset_names(args.handbrake_config)
    except ValueError as exc:
        logging.error(str(exc))
        sys.exit(1)

    preset_name = args.preset_name or preset_names[0]
    if args.preset_name and args.preset_name not in preset_names:
        logging.error(
            f"Preset '{args.preset_name}' not found in config file. "
            f"Available presets: {', '.join(preset_names)}"
        )
        sys.exit(1)

    extra_args = shlex.split(args.handbrake_args) if args.handbrake_args else []

    if not args.dry_run:
        try:
            ensure_handbrake_cli(args.handbrake_cli)
        except FileNotFoundError as exc:
            logging.error(str(exc))
            sys.exit(1)

    if not args.dry_run:
        args.destination.mkdir(parents=True, exist_ok=True)

    stats = convert_videos(
        source_dir=args.source,
        destination_dir=args.destination,
        extensions=extensions,
        output_extension=output_extension,
        preset_file=args.handbrake_config,
        preset_name=preset_name,
        handbrake_cli=args.handbrake_cli,
        handbrake_format=args.handbrake_format,
        extra_args=extra_args,
        recursive=args.recursive,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files scanned: {stats['scanned']}")
    print(f"Files matched: {stats['matched']}")
    print(f"Files converted: {stats['converted']}")
    print(f"Files skipped: {stats['skipped']}")
    print(f"Files failed: {stats['failed']}")

    if stats['errors']:
        print(f"\nErrors encountered ({len(stats['errors'])}):")
        for error in stats['errors']:
            print(f"  - {error}")

    if args.dry_run:
        print("\nThis was a DRY RUN. No files were actually converted.")

    print("=" * 60)

    sys.exit(1 if stats['failed'] > 0 else 0)


if __name__ == '__main__':
    main()
