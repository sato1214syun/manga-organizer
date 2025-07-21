"""Main script for organizing manga zip files into folders based on configuration.

This script selects a source directory, finds zip files, and moves them to destination
subdirectories according to rules defined in a config.toml file.
"""

import re
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from file_picker import pick_dir

from src.manga_organizer.file_operations import (
    clear_processing_results,
    get_fuzzy_matches,
    move_zip_file_with_confirmation,
    show_batch_confirmation_dialog,
    show_processing_results,
)


def load_config() -> tuple[Path | None, str]:
    """Load configuration from config.toml file.

    Returns
    -------
        tuple: (dest_dir, source_dir_str) or (None, "") if error
    """
    config_path = Path("config.toml")
    try:
        with config_path.open("rb") as f:
            config = tomllib.load(f)
        dest_dir_str = config.get("destination_directory")
        source_dir_str = config.get("source_directory", "")
        if not dest_dir_str:
            print("'destination_directory' not found in config.toml")
            return None, ""
        dest_dir = Path(dest_dir_str)
        if not dest_dir.exists():
            print(f"Destination directory does not exist: {dest_dir}")
            return None, ""
        return dest_dir, str(source_dir_str)
    except FileNotFoundError:
        print("config.toml not found.")
        return None, ""
    except tomllib.TOMLDecodeError as e:
        print(f"Error reading config.toml: {e}")
        return None, ""


def build_series_dict(dest_dir: Path) -> dict[str, Path]:
    """Build dictionary mapping series titles to their directory paths.

    Args:
        dest_dir: Destination directory to scan for series subdirectories

    Returns
    -------
        Dictionary mapping series titles to directory paths
    """
    title_regex = re.compile(r"^.*\)\s\[.*?\]\s*")
    series_title_dict = {}

    for root, dirs, _ in dest_dir.walk():
        for dir_name in dirs:
            dir_path = root / dir_name
            title = title_regex.sub("", dir_name).strip()
            if title:
                series_title_dict[title] = dir_path

    return series_title_dict


def run() -> None:
    """Organize manga zip files."""
    # 3. Specify the destination directory in the config file (config.toml)
    dest_dir, source_dir_str = load_config()
    if not dest_dir:
        return

    # 1. Select a folder using file-picker
    source_path = pick_dir(init_dir=source_dir_str)
    if not source_path:
        input("No folder selected. Exiting. please hit the Enter.")
        return
    source_dir = Path(source_path)

    # 処理結果をクリア
    clear_processing_results()

    # 2. Get all zip file paths in the selected folder
    zip_files = list(source_dir.glob("*.zip"))

    if not zip_files:
        print("No zip files found in the selected directory.")
        return

    print(f"Found {len(zip_files)} zip file(s) to process.")

    # 4. Recursively get the paths of subdirectories in the destination directory
    # 5. extract titles of the paths and mapping to subdirectory paths {title: path}
    series_title_dict = build_series_dict(dest_dir)

    # 6. Move zip files according to the rules
    # 事前に曖昧マッチの確認をメインスレッドで実行
    print("事前確認を実行中...")
    all_matches = get_fuzzy_matches(zip_files, series_title_dict)
    fuzzy_matches = {k: v for k, v in all_matches.items() if v is not None}
    confirmations = show_batch_confirmation_dialog(fuzzy_matches)

    print("ファイル移動を並列実行中...")
    # 並列実行する
    moved_count = 0
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                move_zip_file_with_confirmation,
                zip_file,
                series_title_dict,
                confirmation=confirmations.get(zip_file),
            ): zip_file
            for zip_file in zip_files
        }
        for future in futures:
            is_moved = future.result()
            if is_moved:
                moved_count += 1

    print(f"\nFinished. Moved {moved_count} files.")

    # 処理結果をダイアログで表示
    show_processing_results()
