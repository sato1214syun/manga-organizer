"""Main module for manga organizer."""

import re
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from file_picker import pick_dir
from src.manga_organizer.file_operations import move_zip_file


def main() -> None:
    """Execute main script.

    zipファイルを、特定のルールに従ってフォルダ分けする機能。

    1. フォルダをfile-pickerを用いて選択
    2. そのフォルダ内のzipファイルのパスをすべて取得する
    3. zipファイルの仕分け先ディレクトリは設定ファイル(config.toml)で指定しておく
    4. 仕分け先ディレクトリ内のサブディレクトリのパスを再帰的に取得する
    5. サブディレクトリ名から、"あ) [作者名]"を除き、trimした名前(作品名)を取得し、
        4.で取得したサブディレクトリのパスとdict型で関連付けておく
    4. 仕分け先ディレクトリ内でのzipファイルのフォルダ分けルールは以下とする
        - zipファイル名から"01巻"を除外して作品名を抽出する。
        - 同じ作品名のサブディレクトリに移動する
        - サブディレクトリにすでに同名のzipファイルが存在する場合はスキップする
    """
    # 3. Specify the destination directory in the config file (config.toml)
    config_path = Path("config.toml")
    try:
        with config_path.open("rb") as f:
            config = tomllib.load(f)
        dest_dir_str = Path(config.get("destination_directory"))
        source_dir_str = Path(config.get("source_directory"))
        if not dest_dir_str.exists():
            print("'destination_directory' not found in config.toml")
            return
        dest_dir = Path(dest_dir_str)
    except FileNotFoundError:
        print("config.toml not found.")
        return
    except Exception as e:  # noqa: BLE001
        print(f"Error reading config.toml: {e}")
        return

    # 1. Select a folder using file-picker
    source_path = pick_dir(init_dir=source_dir_str)
    if not source_path:
        input("No folder selected. Exiting. please hit the Enter.")
        return
    source_dir = Path(source_path)

    # 2. Get all zip file paths in the selected folder
    zip_files = source_dir.glob("*.zip")

    # 4. Recursively get the paths of subdirectories in the destination directory
    # 5. extract titles of the paths and mapping to subdirectory paths {title: path}
    # Remove "あ) [作者名]" from the subdirectory name and trim spaces to get the title
    title_regex = r"^.*\)\s\[.*\]"
    series_title_dict = {
        re.sub(title_regex, "", d.name).strip(): d
        for d in dest_dir.rglob("*")
        if d.is_dir()
    }

    # 6. Move zip files according to the rules
    # 並列実行する
    moved_count = 0
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(move_zip_file, zip_file, series_title_dict): zip_file
            for zip_file in zip_files
        }
        for future in futures:
            is_moved = future.result()
            if is_moved:
                moved_count += 1
    print(f"\nFinished. Moved {moved_count} files.")


if __name__ == "__main__":
    main()
