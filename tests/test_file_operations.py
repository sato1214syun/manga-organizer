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
