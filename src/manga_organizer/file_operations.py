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


def _show_no_results_dialog() -> None:
    """処理結果がない場合のダイアログを表示する."""
    root = tk.Tk()
    root.withdraw()
    center_x = int(root.winfo_screenwidth() / 2)
    center_y = int(root.winfo_screenheight() / 2)
    root.geometry(f"1x1+{center_x}+{center_y}")
    root.deiconify()
    root.withdraw()
    messagebox.showinfo("処理結果", "処理されたファイルはありません。")
    root.destroy()


def _create_centered_window(title: str, width: int, height: int) -> tk.Tk:
    """中央に配置されたウィンドウを作成する."""
    root = tk.Tk()
    root.title(title)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width / 2 - width / 2)
    center_y = int(screen_height / 2 - height / 2)
    root.geometry(f"{width}x{height}+{center_x}+{center_y}")
    root.resizable(width=True, height=True)
    root.lift()
    root.attributes("-topmost", True)  # noqa: FBT003
    root.focus_force()
    return root


def _get_action_text(action: str) -> str:
    """アクションに対応するテキストを取得する."""
    action_map = {
        "moved": "✓ 移動完了",
        "skipped_exists": "⚠ スキップ (既存)",
        "skipped_no_match": "⚠ スキップ (マッチなし)",
        "cancelled": "✗ キャンセル",
        "error": "✗ エラー",
    }
    return action_map.get(action, "")


def _populate_text_area(text_area: scrolledtext.ScrolledText) -> None:
    """テキストエリアに処理結果を追加する."""
    for i, result in enumerate(processing_results, 1):
        action_text = _get_action_text(result["action"])
        text = f"{i}. {action_text}: {result['file_name']}"
        if result["details"]:
            text += f"\n   詳細: {result['details']}"
        text += "\n\n"
        text_area.insert(tk.END, text)


def show_processing_results() -> None:
    """処理結果をスクロール可能なダイアログで表示する."""
    if not processing_results:
        _show_no_results_dialog()
        return

    root = _create_centered_window("処理結果", 600, 400)
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    title_text = f"処理結果 (合計: {len(processing_results)}件)"
    title_label = tk.Label(main_frame, text=title_text, font=("Arial", 12, "bold"))
    title_label.pack(pady=(0, 10))

    text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, width=70, height=20)
    text_area.pack(fill=tk.BOTH, expand=True)

    _populate_text_area(text_area)
    text_area.config(state=tk.DISABLED)

    close_button = tk.Button(
        main_frame, text="閉じる", command=root.destroy, font=("Arial", 10)
    )
    close_button.pack(pady=(10, 0))

    root.bind("<Escape>", lambda _: root.destroy())
    root.mainloop()


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
    # タイトルと巻数の間にスペースを追加
    if book_suffix:
        new_filename = f"{best_match} {book_suffix}.zip"
        folder_name = f"{best_match} {book_suffix}"
    else:
        new_filename = f"{best_match}.zip"
        folder_name = best_match

    new_zip_path = zip_file.parent / new_filename

    zip_file.rename(new_zip_path)

    if not rename_folder_in_zip(new_zip_path, folder_name):
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


def get_fuzzy_matches(
    zip_files: list[Path], series_title_dict: dict[str, Path]
) -> dict[Path, tuple[str, float] | None]:
    """事前に曖昧マッチの候補を取得する."""
    matches = {}
    for zip_file in zip_files:
        book_title, _ = _parse_filename(zip_file.stem)

        # 完全一致チェック
        if book_title in series_title_dict:
            matches[zip_file] = None  # 完全一致の場合はNone
            continue

        # 曖昧検索
        result = process.extractOne(book_title, series_title_dict.keys())
        if result is None or result[1] < SCORE_THRESHOLD:
            matches[zip_file] = None  # マッチしない場合はNone
        else:
            matches[zip_file] = (result[0], result[1])  # (best_match, score)

    return matches


def show_batch_confirmation_dialog(
    fuzzy_matches: dict[Path, tuple[str, float]],
) -> dict[Path, bool]:
    """バッチで確認ダイアログを表示する."""
    confirmations = {}

    if not fuzzy_matches:
        return confirmations

    for zip_file, (best_match, score) in fuzzy_matches.items():
        book_title, _ = _parse_filename(zip_file.stem)

        root = tk.Tk()
        root.withdraw()
        root.lift()
        root.attributes("-topmost", True)  # noqa: FBT003
        root.focus_force()

        message = f"'{book_title}' は以下のシリーズタイトルに最も近いです:\n\n"
        message += f"{best_match} (スコア: {score})\n"
        message += f"\n'{zip_file.name}' をこのフォルダに移動しますか?"

        user_confirmed = messagebox.askyesno(title="移動確認", message=message)
        confirmations[zip_file] = user_confirmed
        root.destroy()

    return confirmations


def move_zip_file_with_confirmation(
    zip_file: Path,
    series_title_dict: dict[str, Path],
    *,
    confirmation: bool | None = None,
) -> bool:
    """確認結果を使ってファイルを移動する."""
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

    # 事前確認結果を使用
    if confirmation is False:
        add_processing_result(
            "cancelled",
            zip_file.name,
            f"ユーザーがキャンセル (候補: {best_match}, スコア: {score})",
        )
        return False

    return _handle_fuzzy_match(zip_file, best_match, book_suffix, series_title_dict)


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
