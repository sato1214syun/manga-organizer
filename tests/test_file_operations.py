"""Test script for the enhanced move_zip_file function."""

import shutil
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.manga_organizer.file_operations import move_zip_file


@pytest.fixture
def temp_test_dir(tmp_path: Path) -> Path:
    """Create temporary test directory structure."""
    test_dir = tmp_path / "test_temp"
    test_dir.mkdir()
    return test_dir


@pytest.fixture
def mock_series_dict(tmp_path: Path) -> dict[str, Path]:
    """Create mock series title dictionary with real directories."""
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    folder1 = dest_dir / "あ) [作者x作者2] てすとフォルダ1"
    folder2 = dest_dir / "あ) [作者x作者2] てすとフォルダ2"
    folder1.mkdir()
    folder2.mkdir()

    return {
        "てすとフォルダ1": folder1,
        "てすとフォルダ2": folder2,
    }


@pytest.fixture
def test_zip_file(temp_test_dir: Path) -> Path:
    """Create a test zip file with a folder inside."""
    zip_path = temp_test_dir / "てすと第1巻.zip"

    # Create a simple zip file with a folder inside
    with zipfile.ZipFile(zip_path, "w") as zf:
        # Add a directory entry
        zf.writestr("てすと第1巻/", "")
        # Add a file inside the directory
        zf.writestr("てすと第1巻/test.txt", "test content")

    return zip_path


class TestMoveZipFile:
    """Test cases for move_zip_file function."""

    def test_exact_match_success(
        self, test_zip_file: Path, mock_series_dict: dict[str, Path]
    ) -> None:
        """Test exact match case - should move without dialog."""
        # Rename the zip file to match exactly
        exact_match_zip = test_zip_file.parent / "てすとフォルダ2第1巻.zip"
        test_zip_file.rename(exact_match_zip)

        result = move_zip_file(exact_match_zip, mock_series_dict)

        assert result is True
        # Check that file was moved to the correct location
        expected_path = mock_series_dict["てすとフォルダ2"] / "てすとフォルダ2第1巻.zip"
        assert expected_path.exists()

    def test_exact_match_file_exists(
        self, test_zip_file: Path, mock_series_dict: dict[str, Path]
    ) -> None:
        """Test exact match case where destination file already exists."""
        # Rename the zip file to match exactly
        exact_match_zip = test_zip_file.parent / "てすとフォルダ2第1巻.zip"
        test_zip_file.rename(exact_match_zip)

        # Create a file that already exists at destination
        dest_file = mock_series_dict["てすとフォルダ2"] / "てすとフォルダ2第1巻.zip"
        dest_file.write_text("existing file")

        result = move_zip_file(exact_match_zip, mock_series_dict)

        assert result is False
        # Original file should still exist
        assert exact_match_zip.exists()

    @patch("src.manga_organizer.file_operations.messagebox.askyesno")
    @patch("src.manga_organizer.file_operations.tk.Tk")
    def test_partial_match_user_accepts(
        self,
        mock_tk: MagicMock,
        mock_messagebox: MagicMock,
        test_zip_file: Path,
        mock_series_dict: dict[str, Path],
    ) -> None:
        """Test partial match case where user accepts the move."""
        mock_messagebox.return_value = True  # User clicks "Yes"
        mock_root = mock_tk.return_value

        result = move_zip_file(test_zip_file, mock_series_dict)

        assert result is True
        # Check that dialog was shown
        mock_messagebox.assert_called_once()
        mock_root.withdraw.assert_called_once()
        mock_root.destroy.assert_called_once()

        # Check that file was renamed and moved
        # Note: The first matching key will be used ("てすとフォルダ1")
        expected_path = mock_series_dict["てすとフォルダ1"] / "てすとフォルダ1第1巻.zip"
        assert expected_path.exists()

    @patch("src.manga_organizer.file_operations.messagebox.askyesno")
    @patch("src.manga_organizer.file_operations.tk.Tk")
    def test_partial_match_user_declines(
        self,
        mock_tk: MagicMock,
        mock_messagebox: MagicMock,
        test_zip_file: Path,
        mock_series_dict: dict[str, Path],
    ) -> None:
        """Test partial match case where user declines the move."""
        mock_messagebox.return_value = False  # User clicks "No"
        mock_root = mock_tk.return_value

        result = move_zip_file(test_zip_file, mock_series_dict)

        assert result is False
        # Check that dialog was shown
        mock_messagebox.assert_called_once()
        mock_root.withdraw.assert_called_once()
        mock_root.destroy.assert_called_once()

        # Original file should still exist
        assert test_zip_file.exists()

    @patch("src.manga_organizer.file_operations.messagebox.askyesno")
    @patch("src.manga_organizer.file_operations.tk.Tk")
    def test_partial_match_destination_exists(
        self,
        mock_tk: MagicMock,
        mock_messagebox: MagicMock,
        test_zip_file: Path,
        mock_series_dict: dict[str, Path],
    ) -> None:
        """Test partial match case where destination file already exists."""
        mock_messagebox.return_value = True  # User clicks "Yes"

        # Create a file that already exists at destination for the first matching key
        dest_file = mock_series_dict["てすとフォルダ1"] / "てすとフォルダ1第1巻.zip"
        dest_file.write_text("existing file")

        result = move_zip_file(test_zip_file, mock_series_dict)

        assert result is False
        # Original file should be restored to original name
        assert test_zip_file.exists()

    def test_no_match(
        self, temp_test_dir: Path, mock_series_dict: dict[str, Path]
    ) -> None:
        """Test case where there's no match at all."""
        # Create a zip file with no matching title
        no_match_zip = temp_test_dir / "完全に違う名前.zip"
        with zipfile.ZipFile(no_match_zip, "w") as zf:
            zf.writestr("test.txt", "test content")

        result = move_zip_file(no_match_zip, mock_series_dict)

        assert result is False
        # Original file should still exist
        assert no_match_zip.exists()

    def test_multiple_partial_matches(
        self, temp_test_dir: Path, mock_series_dict: dict[str, Path]
    ) -> None:
        """Test case with multiple partial matches."""
        # Add another series that would also match
        folder3 = mock_series_dict["てすとフォルダ1"].parent / "あ) [作者] てすと作品"
        folder3.mkdir()
        mock_series_dict["てすと作品"] = folder3

        test_zip = temp_test_dir / "てすと第1巻.zip"
        with zipfile.ZipFile(test_zip, "w") as zf:
            zf.writestr("てすと第1巻/test.txt", "test content")

        with (
            patch(
                "src.manga_organizer.file_operations.messagebox.askyesno"
            ) as mock_messagebox,
            patch("src.manga_organizer.file_operations.tk.Tk"),
        ):
            mock_messagebox.return_value = True

            result = move_zip_file(test_zip, mock_series_dict)

            assert result is True
            # Should use the first matching key
            expected_path = (
                mock_series_dict["てすとフォルダ1"] / "てすとフォルダ1第1巻.zip"
            )
            assert expected_path.exists()


class TestFuzzySearch:
    """Test cases for rapidfuzz-based fuzzy matching."""

    @pytest.fixture
    def fuzzy_series_dict(self, tmp_path: Path) -> dict[str, Path]:
        """Create mock series title dictionary for fuzzy matching tests."""
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        # Create directories with similar but different names
        folders = {
            "進撃の巨人": dest_dir / "進撃の巨人",
            "進撃の巨人 完結編": dest_dir / "進撃の巨人 完結編",
            "鬼滅の刃": dest_dir / "鬼滅の刃",
            "鬼滅の刃 無限列車編": dest_dir / "鬼滅の刃 無限列車編",
            "ワンピース": dest_dir / "ワンピース",
            "ワンピース RED": dest_dir / "ワンピース RED",
        }

        for folder in folders.values():
            folder.mkdir()

        return folders

    @pytest.fixture
    def fuzzy_zip_file(self, tmp_path: Path) -> Path:
        """Create a test zip file for fuzzy matching."""
        zip_path = tmp_path / "進撃第1巻.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("進撃第1巻/", "")
            zf.writestr("進撃第1巻/test.txt", "test content")
        return zip_path

    @patch("src.manga_organizer.file_operations.messagebox.askyesno", return_value=True)
    @patch("src.manga_organizer.file_operations.tk.Tk")
    def test_fuzzy_match_high_score(
        self,
        mock_tk: MagicMock,
        mock_messagebox: MagicMock,
        fuzzy_zip_file: Path,
        fuzzy_series_dict: dict[str, Path],
    ) -> None:
        """Test fuzzy match with high score (should trigger dialog and move)."""
        # Create a zip file that closely matches "進撃の巨人"
        zip_path = fuzzy_zip_file.parent / "進撃第1巻.zip"
        fuzzy_zip_file.rename(zip_path)

        result = move_zip_file(zip_path, fuzzy_series_dict)

        assert result is True
        # Check that dialog was shown
        mock_messagebox.assert_called_once()
        mock_tk.assert_called_once()
        mock_tk.return_value.withdraw.assert_called_once()
        mock_tk.return_value.destroy.assert_called_once()

        # Check dialog message contains fuzzy match info
        call_args = mock_messagebox.call_args
        message = call_args[1]["message"]
        assert "進撃" in message
        assert "スコア:" in message
        assert "進撃の巨人" in message

        # Check that file was moved to the best match directory
        expected_path = fuzzy_series_dict["進撃の巨人"] / "進撃の巨人第1巻.zip"
        assert expected_path.exists()

    @patch(
        "src.manga_organizer.file_operations.messagebox.askyesno", return_value=False
    )
    @patch("src.manga_organizer.file_operations.tk.Tk")
    def test_fuzzy_match_user_declines(
        self,
        mock_tk: MagicMock,
        mock_messagebox: MagicMock,
        fuzzy_zip_file: Path,
        fuzzy_series_dict: dict[str, Path],
    ) -> None:
        """Test fuzzy match when user declines the move."""
        # Create a zip file that closely matches "鬼滅の刃"
        zip_path = fuzzy_zip_file.parent / "鬼滅第1巻.zip"
        fuzzy_zip_file.rename(zip_path)

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("鬼滅第1巻/", "")
            zf.writestr("鬼滅第1巻/test.txt", "test content")

        result = move_zip_file(zip_path, fuzzy_series_dict)

        assert result is False
        # Check that dialog was shown
        mock_messagebox.assert_called_once()
        mock_tk.assert_called_once()
        mock_tk.return_value.withdraw.assert_called_once()
        mock_tk.return_value.destroy.assert_called_once()

        # Original file should still exist
        assert zip_path.exists()

    def test_fuzzy_match_low_score_no_dialog(
        self,
        tmp_path: Path,
        fuzzy_series_dict: dict[str, Path],
    ) -> None:
        """Test fuzzy match with low score (should not trigger dialog)."""
        # Create a zip file with very different name (low fuzzy score)
        zip_path = tmp_path / "完全に違う作品第1巻.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("完全に違う作品第1巻/", "")
            zf.writestr("完全に違う作品第1巻/test.txt", "test content")

        with patch(
            "src.manga_organizer.file_operations.messagebox.askyesno"
        ) as mock_msg:
            result = move_zip_file(zip_path, fuzzy_series_dict)

            assert result is False
            # Dialog should not be shown for low score matches
            mock_msg.assert_not_called()
            # Original file should still exist
            assert zip_path.exists()

    @patch("src.manga_organizer.file_operations.messagebox.askyesno", return_value=True)
    @patch("src.manga_organizer.file_operations.tk.Tk")
    def test_fuzzy_match_with_volume_suffix(
        self,
        mock_tk: MagicMock,
        mock_messagebox: MagicMock,
        tmp_path: Path,
        fuzzy_series_dict: dict[str, Path],
    ) -> None:
        """Test fuzzy match preserves volume suffix in renamed file."""
        # Create a zip file with volume suffix
        zip_path = tmp_path / "ワンピ第25巻.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("ワンピ第25巻/", "")
            zf.writestr("ワンピ第25巻/test.txt", "test content")

        result = move_zip_file(zip_path, fuzzy_series_dict)

        assert result is True
        # Check that volume suffix is preserved in the moved file
        expected_path = fuzzy_series_dict["ワンピース"] / "ワンピース第25巻.zip"
        assert expected_path.exists()

    @patch("src.manga_organizer.file_operations.messagebox.askyesno", return_value=True)
    @patch("src.manga_organizer.file_operations.tk.Tk")
    def test_fuzzy_match_destination_file_exists(
        self,
        mock_tk: MagicMock,
        mock_messagebox: MagicMock,
        tmp_path: Path,
        fuzzy_series_dict: dict[str, Path],
    ) -> None:
        """Test fuzzy match when destination file already exists."""
        # Create a zip file
        zip_path = tmp_path / "進撃第1巻.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("進撃第1巻/", "")
            zf.writestr("進撃第1巻/test.txt", "test content")

        # Create existing file at destination
        dest_file = fuzzy_series_dict["進撃の巨人"] / "進撃の巨人第1巻.zip"
        dest_file.write_text("existing file")

        result = move_zip_file(zip_path, fuzzy_series_dict)

        assert result is False
        # Original file should be restored to original name
        assert zip_path.exists()

    @patch("src.manga_organizer.file_operations.process.extractOne")
    def test_fuzzy_match_score_threshold(
        self,
        mock_extract_one: MagicMock,
        tmp_path: Path,
        fuzzy_series_dict: dict[str, Path],
    ) -> None:
        """Test that fuzzy matching respects the score threshold."""
        # Create a zip file
        zip_path = tmp_path / "テスト第1巻.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("テスト第1巻/", "")
            zf.writestr("テスト第1巻/test.txt", "test content")

        # Mock low score (below threshold of 80)
        mock_extract_one.return_value = ("進撃の巨人", 70)

        result = move_zip_file(zip_path, fuzzy_series_dict)

        assert result is False
        assert zip_path.exists()
        mock_extract_one.assert_called_once()

    @patch("src.manga_organizer.file_operations.process.extractOne")
    @patch("src.manga_organizer.file_operations.messagebox.askyesno", return_value=True)
    @patch("src.manga_organizer.file_operations.tk.Tk")
    def test_fuzzy_match_exact_threshold(
        self,
        mock_tk: MagicMock,
        mock_messagebox: MagicMock,
        mock_extract_one: MagicMock,
        tmp_path: Path,
        fuzzy_series_dict: dict[str, Path],
    ) -> None:
        """Test fuzzy matching at exact threshold score."""
        # Create a zip file
        zip_path = tmp_path / "テスト第1巻.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("テスト第1巻/", "")
            zf.writestr("テスト第1巻/test.txt", "test content")

        # Mock score exactly at threshold (80)
        mock_extract_one.return_value = ("進撃の巨人", 80)

        result = move_zip_file(zip_path, fuzzy_series_dict)

        assert result is True
        mock_messagebox.assert_called_once()
        expected_path = fuzzy_series_dict["進撃の巨人"] / "進撃の巨人第1巻.zip"
        assert expected_path.exists()


# Keep the original function for manual testing if needed
def manual_test_move_function() -> None:
    """Manual test function that requires user interaction."""
    # テスト用のディレクトリ構造を作成
    test_dir = Path("test_temp")
    test_dir.mkdir(exist_ok=True)

    # テスト用のzipファイルを作成(実際のzipファイルをコピー).
    source_zip = Path("test/test_files/てすとフォルダ2.zip")
    test_zip = test_dir / "てすと第1巻.zip"

    if source_zip.exists():
        shutil.copy(source_zip, test_zip)
        print(f"Created test zip: {test_zip}")
    else:
        print("Source zip file not found")
        return

    # series_title_dictを模擬
    series_title_dict = {
        "てすとフォルダ1": Path("test/dest/あ) [作者x作者2] てすとフォルダ1"),
        "てすとフォルダ2": Path("test/dest/あ) [作者x作者2] てすとフォルダ2"),
    }

    # テスト実行
    print(f"\nTesting with zip file: {test_zip.name}")
    print(f"Available series: {list(series_title_dict.keys())}")

    try:
        result = move_zip_file(test_zip, series_title_dict)
        print(f"Move result: {result}")
    except Exception as e:  # noqa: BLE001
        print(f"Error during move: {e}")

    # クリーンアップ
    if test_zip.exists():
        test_zip.unlink()
    if test_dir.exists():
        test_dir.rmdir()
    print("Test completed and cleaned up.")


if __name__ == "__main__":
    manual_test_move_function()
