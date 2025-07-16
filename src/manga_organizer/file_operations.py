"""File operations for manga organizer."""

import re
import shutil
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import messagebox


def rename_folder_in_zip(zip_path: Path, new_name: str) -> bool:
    """Rename the main folder inside a zip file."""
    try:
        # 一時ファイルを作成
        temp_zip_path = zip_path.with_suffix(".tmp")

        with (
            zipfile.ZipFile(zip_path, "r") as source_zip,
            zipfile.ZipFile(temp_zip_path, "w", zipfile.ZIP_DEFLATED) as target_zip,
        ):
            for file_info in source_zip.infolist():
                file_data = source_zip.read(file_info.filename)

                # フォルダ名を変更
                new_filename = file_info.filename
                if "/" in file_info.filename:
                    parts = file_info.filename.split("/")
                    if len(parts) > 1:
                        parts[0] = new_name
                        new_filename = "/".join(parts)
                elif file_info.is_dir() and file_info.filename.rstrip("/"):
                    new_filename = new_name + "/"

                # 新しいファイル情報を作成
                new_file_info = zipfile.ZipInfo(new_filename)
                new_file_info.date_time = file_info.date_time
                new_file_info.compress_type = file_info.compress_type

                if file_info.is_dir():
                    new_file_info.external_attr = file_info.external_attr
                    target_zip.writestr(new_file_info, b"")
                else:
                    target_zip.writestr(new_file_info, file_data)

        # 元のファイルを削除し、一時ファイルをリネーム
        zip_path.unlink()
        temp_zip_path.rename(zip_path)

    except (zipfile.BadZipFile, FileNotFoundError, PermissionError) as e:
        msg = f"Error renaming folder in zip {zip_path}: {e}"
        print(msg)
        if temp_zip_path.exists():
            temp_zip_path.unlink()
        return False
    else:
        return True


def move_zip_file(zip_file: Path, series_title_dict: dict[str, Path]) -> bool:
    """Move zip files to their respective directories based on series title."""
    file_name = zip_file.stem  # File name without extension

    # book_titleとbook_suffixに分割
    match = re.match(r"^(.+?)(第\d+巻.*)?$", file_name)
    if match:
        book_title = match.group(1).strip()
        book_suffix = match.group(2) or ""
    else:
        book_title = file_name
        book_suffix = ""

    # 完全一致チェック
    dist_path = series_title_dict.get(book_title)
    if dist_path:
        dst = dist_path / zip_file.name
        if dst.exists():
            print(f"File {dst.name} already exists. Skipping.")
            return False
        shutil.move(str(zip_file), str(dst))
        print(f"Moved {zip_file.name} into {dist_path.name}")
        return True

    # 部分配列チェック(book_titleが各キーに含まれるかチェック).
    matching_keys = [key for key in series_title_dict if book_title in key]

    if matching_keys:
        # ダイアログを表示
        root = tk.Tk()
        root.withdraw()  # メインウィンドウを非表示

        message = f"'{book_title}' は以下のシリーズタイトルに含まれています:\n\n"
        for i, key in enumerate(matching_keys, 1):
            message += f"{i}. {key}\n"
        message += f"\n'{zip_file.name}' をこのフォルダに移動しますか?"

        # 複数の候補がある場合は選択ダイアログを表示
        if len(matching_keys) == 1:
            result = messagebox.askyesno("移動確認", message)
            selected_key = matching_keys[0] if result else None
        else:
            # 複数候補の場合は最初の候補を使用
            # より良い実装のためには選択ダイアログが必要
            result = messagebox.askyesno(
                "移動確認", message + "\n最初の候補を使用します。"
            )
            selected_key = matching_keys[0] if result else None

        root.destroy()

        if selected_key:
            # ファイル名を変更
            new_filename = selected_key + book_suffix + ".zip"
            new_zip_path = zip_file.parent / new_filename

            # zipファイルをリネーム
            zip_file.rename(new_zip_path)

            # zip内のフォルダ名も変更
            if not rename_folder_in_zip(new_zip_path, selected_key + book_suffix):
                print(f"Warning: Failed to rename folder inside {new_filename}")

            # 移動先パスを取得
            dist_path = series_title_dict[selected_key]
            dst = dist_path / new_filename

            if dst.exists():
                print(f"File {dst.name} already exists. Skipping.")
                # 元の名前に戻す
                new_zip_path.rename(zip_file)
                return False

            shutil.move(str(new_zip_path), str(dst))
            print(
                f"Moved and renamed {zip_file.name} to {new_filename} "
                f"into {dist_path.name}"
            )
            return True

    return False
