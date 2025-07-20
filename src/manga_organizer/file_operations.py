"""File operations for manga organizer."""

# インポート順序を修正
import re
import shutil
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import messagebox, scrolledtext

from rapidfuzz import process  # rapidfuzzをインポート

# 定数を定義
SCORE_THRESHOLD = 80

# 処理結果を記録するグローバルリスト
processing_results = []


def add_processing_result(action: str, file_name: str, details: str = "") -> None:
    """処理結果をリストに追加する."""
    processing_results.append(
        {"action": action, "file_name": file_name, "details": details}
    )


def show_processing_results() -> None:
    """処理結果をスクロール可能なダイアログで表示する."""
    if not processing_results:
        messagebox.showinfo("処理結果", "処理されたファイルはありません。")
        return

    # ダイアログウィンドウを作成
    result_window = tk.Toplevel()
    result_window.title("処理結果")
    result_window.geometry("600x400")
    result_window.resizable(width=True, height=True)

    # ウィンドウを最前面に表示
    result_window.lift()
    result_window.attributes("-topmost", True)  # noqa: FBT003
    result_window.focus_force()

    # メインフレーム
    main_frame = tk.Frame(result_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # タイトルラベル
    title_text = f"処理結果 (合計: {len(processing_results)}件)"
    title_label = tk.Label(main_frame, text=title_text, font=("Arial", 12, "bold"))
    title_label.pack(pady=(0, 10))

    # スクロール可能なテキストエリア
    text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, width=70, height=20)
    text_area.pack(fill=tk.BOTH, expand=True)

    # 処理結果をテキストエリアに追加
    for i, result in enumerate(processing_results, 1):
        action_text = ""
        if result["action"] == "moved":
            action_text = "✓ 移動完了"
        elif result["action"] == "skipped_exists":
            action_text = "⚠ スキップ (既存)"
        elif result["action"] == "skipped_no_match":
            action_text = "⚠ スキップ (マッチなし)"
        elif result["action"] == "cancelled":
            action_text = "✗ キャンセル"
        elif result["action"] == "error":
            action_text = "✗ エラー"

        text = f"{i}. {action_text}: {result['file_name']}"
        if result["details"]:
            text += f"\n   詳細: {result['details']}"
        text += "\n\n"

        text_area.insert(tk.END, text)

    # テキストエリアを読み取り専用にする
    text_area.config(state=tk.DISABLED)

    # 閉じるボタン
    close_button = tk.Button(
        main_frame, text="閉じる", command=result_window.destroy, font=("Arial", 10)
    )
    close_button.pack(pady=(10, 0))

    # Escapeキーで閉じる
    result_window.bind("<Escape>", lambda _: result_window.destroy())


def clear_processing_results() -> None:
    """処理結果をクリアする."""
    processing_results.clear()


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


def _parse_filename(file_name: str) -> tuple[str, str]:
    """Parse filename into book title and suffix."""
    match = re.match(r"^(.+?)(第\d+巻.*)?$", file_name)
    if match:
        return match.group(1).strip(), match.group(2) or ""
    return file_name, ""


def _handle_exact_match(zip_file: Path, dist_path: Path) -> bool:
    """Handle exact match case."""
    dst = dist_path / zip_file.name
    if dst.exists():
        print(f"File {dst.name} already exists. Skipping.")
        add_processing_result(
            "skipped_exists", zip_file.name, f"移動先に同名ファイルが存在: {dst}"
        )
        return False

    shutil.move(str(zip_file), str(dst))
    print(f"Moved {zip_file.name} into {dist_path.name}")
    add_processing_result("moved", zip_file.name, f"完全一致で移動: {dist_path.name}")
    return True


def _show_confirmation_dialog(
    book_title: str, best_match: str, score: float, zip_file: Path
) -> bool:
    """Show confirmation dialog for fuzzy match."""
    root = tk.Tk()
    root.withdraw()
    root.lift()
    root.attributes("-topmost", True)  # noqa: FBT003
    root.focus_force()

    message = f"'{book_title}' は以下のシリーズタイトルに最も近いです:\n\n"
    message += f"{best_match} (スコア: {score})\n"
    message += f"\n'{zip_file.name}' をこのフォルダに移動しますか?"

    user_confirmed = messagebox.askyesno(title="移動確認", message=message)
    root.destroy()
    return user_confirmed


def _handle_fuzzy_match(
    zip_file: Path,
    best_match: str,
    book_suffix: str,
    series_title_dict: dict[str, Path],
) -> bool:
    """Handle fuzzy match case with file renaming and moving."""
    new_filename = best_match + book_suffix + ".zip"
    new_zip_path = zip_file.parent / new_filename

    zip_file.rename(new_zip_path)

    if not rename_folder_in_zip(new_zip_path, f"{best_match} {book_suffix}"):
        print(f"Warning: Failed to rename folder inside {new_filename}")

    dist_path = series_title_dict[best_match]
    dst = dist_path / new_filename

    if dst.exists():
        print(f"File {dst.name} already exists. Skipping.")
        new_zip_path.rename(zip_file)
        add_processing_result(
            "skipped_exists",
            zip_file.name,
            f"リネーム後の移動先に同名ファイルが存在: {new_filename}",
        )
        return False

    shutil.move(str(new_zip_path), str(dst))
    print(f"Moved and renamed {zip_file.name} to {new_filename} into {dist_path.name}")
    add_processing_result(
        "moved",
        zip_file.name,
        f"曖昧マッチで移動・リネーム: {new_filename} → {dist_path.name}",
    )
    return True


def move_zip_file(zip_file: Path, series_title_dict: dict[str, Path]) -> bool:
    """Move zip files to their respective directories based on series title."""
    book_title, book_suffix = _parse_filename(zip_file.stem)

    # 完全一致チェック
    dist_path = series_title_dict.get(book_title)
    if dist_path:
        return _handle_exact_match(zip_file, dist_path)

    # 曖昧検索
    result = process.extractOne(book_title, series_title_dict.keys())
    if result is None:
        add_processing_result(
            "skipped_no_match",
            zip_file.name,
            "マッチするシリーズが見つかりませんでした",
        )
        return False

    best_match, score = result[0], result[1]
    if score < SCORE_THRESHOLD:
        add_processing_result(
            "skipped_no_match",
            zip_file.name,
            f"スコアが閾値未満 (最高スコア: {score}, 閾値: {SCORE_THRESHOLD})",
        )
        return False

    if not _show_confirmation_dialog(book_title, best_match, score, zip_file):
        add_processing_result(
            "cancelled",
            zip_file.name,
            f"ユーザーがキャンセル (候補: {best_match}, スコア: {score})",
        )
        return False

    return _handle_fuzzy_match(zip_file, best_match, book_suffix, series_title_dict)
