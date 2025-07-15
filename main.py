"""Main script for organizing manga zip files."""

import re
import shutil
import tomllib
from pathlib import Path

from file_picker import pick_dir


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
        - サブディレクトリの作品名と同じ名前のzipファイルは、そのサブディレクトリに移動する
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
    moved_count = 0
    for zip_file in zip_files:
        file_name = zip_file.stem  # File name without extension
        book_title = re.sub(r"\d+巻$", "", file_name).strip()
        dist_path = series_title_dict.get(book_title)
        if dist_path:
            dst = dist_path / zip_file.name
            if dst.exists():
                print(f"File {dst.name} already exists. Skipping.")
                continue
            shutil.move(str(zip_file), str(dst))
            moved_count += 1
            print(f"Moved {zip_file.name} into {dist_path.name}")

    print(f"\nFinished. Moved {moved_count} files.")


if __name__ == "__main__":
    main()
