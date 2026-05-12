"""Tests for get_download_info() function."""

import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from quantilica_core.exceptions import FetchError

from tesouro_direto_fetcher.downloader import get_download_info


class TestGetDownloadInfo(unittest.TestCase):
    def setUp(self):
        self.dest_dir = Path("test_data")
        self.dataset_id = "test-dataset"

    @patch("tesouro_direto_fetcher.downloader.get_dataset_resources")
    def test_basic_info_retrieval(self, mock_get_resources):
        mock_get_resources.return_value = [
            {
                "name": "Test Resource",
                "url": "https://example.com/test.csv",
                "format": "CSV",
                "size": "1024",
                "last_modified": "2026-02-07T10:00:00",
            }
        ]

        info_list = asyncio.run(get_download_info(self.dest_dir, self.dataset_id))

        self.assertEqual(len(info_list), 1)
        info = info_list[0]
        self.assertEqual(info["resource_name"], "Test Resource")
        self.assertEqual(info["url"], "https://example.com/test.csv")
        self.assertEqual(info["size"], 1024)
        self.assertTrue(info["would_download"])
        self.assertIsNone(info["latest_local"])

    @patch("tesouro_direto_fetcher.downloader.get_dataset_resources")
    def test_skip_non_csv(self, mock_get_resources):
        mock_get_resources.return_value = [
            {
                "name": "CSV Resource",
                "url": "https://example.com/data.csv",
                "format": "CSV",
                "size": "1024",
            },
            {
                "name": "JSON Resource",
                "url": "https://example.com/data.json",
                "format": "JSON",
                "size": "512",
            },
        ]

        info_list = asyncio.run(get_download_info(self.dest_dir, self.dataset_id))

        self.assertEqual(len(info_list), 1)
        self.assertEqual(info_list[0]["resource_name"], "CSV Resource")

    @patch("tesouro_direto_fetcher.downloader.get_dataset_resources")
    def test_existing_file_same_size_skipped(self, mock_get_resources):
        mock_get_resources.return_value = [
            {
                "name": "Test Resource",
                "url": "https://example.com/test.csv",
                "format": "CSV",
                "size": "1024",
                "last_modified": "2026-02-07T10:00:00",
            }
        ]

        mock_file = MagicMock(spec=Path)
        mock_file.stat.return_value.st_size = 1024
        mock_file.__str__ = MagicMock(return_value="/tmp/test.csv")

        with patch(
            "tesouro_direto_fetcher.downloader.DataRepository.get_latest_stamped_file",
            return_value=mock_file,
        ):
            info_list = asyncio.run(
                get_download_info(self.dest_dir, self.dataset_id)
            )

        self.assertFalse(info_list[0]["would_download"])

    @patch("tesouro_direto_fetcher.downloader.get_dataset_resources")
    def test_size_conversion(self, mock_get_resources):
        mock_get_resources.return_value = [
            {
                "name": "Test Resource",
                "url": "https://example.com/test.csv",
                "format": "CSV",
                "size": "12345",
                "last_modified": "2026-02-07T10:00:00",
            }
        ]

        info_list = asyncio.run(get_download_info(self.dest_dir, self.dataset_id))

        self.assertIsInstance(info_list[0]["size"], int)
        self.assertEqual(info_list[0]["size"], 12345)

    @patch("tesouro_direto_fetcher.downloader.get_dataset_resources")
    def test_error_handling_raises_fetch_error(self, mock_get_resources):
        mock_get_resources.side_effect = Exception("API Error")

        with self.assertRaises(FetchError) as ctx:
            asyncio.run(get_download_info(self.dest_dir, self.dataset_id))

        self.assertIn("Error fetching resources", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
