"""Tests for get_download_info() function."""

import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from tddata.downloader import get_download_info


class TestGetDownloadInfo(unittest.TestCase):
    """Test get_download_info function."""

    def setUp(self):
        """Set up test fixtures."""
        self.dest_dir = Path("test_data")
        self.dataset_id = "test-dataset"

    @patch("tddata.downloader.get_dataset_resources")
    @patch("tddata.downloader.get_latest_file")
    async def async_test_basic_info_retrieval(self, mock_get_latest, mock_get_resources):
        """Test basic info retrieval without existing files."""
        # Mock CKAN API response
        mock_resources = [
            {
                "name": "Test Resource",
                "url": "https://example.com/test.csv",
                "format": "CSV",
                "size": "1024",
                "last_modified": "2026-02-07T10:00:00",
            }
        ]
        mock_get_resources.return_value = mock_resources
        mock_get_latest.return_value = None

        # Test
        info_list = await get_download_info(self.dest_dir, self.dataset_id)

        # Assertions
        self.assertEqual(len(info_list), 1)
        info = info_list[0]
        self.assertEqual(info["resource_name"], "Test Resource")
        self.assertEqual(info["url"], "https://example.com/test.csv")
        self.assertEqual(info["size"], 1024)  # Should be converted to int
        self.assertTrue(info["would_download"])
        self.assertIsNone(info["latest_local"])

    @patch("tddata.downloader.get_dataset_resources")
    @patch("tddata.downloader.get_latest_file")
    async def async_test_skip_non_csv(self, mock_get_latest, mock_get_resources):
        """Test that non-CSV resources are filtered out."""
        # Mock CKAN API response with mixed formats
        mock_resources = [
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
        mock_get_resources.return_value = mock_resources
        mock_get_latest.return_value = None

        # Test
        info_list = await get_download_info(self.dest_dir, self.dataset_id)

        # Only CSV should be included
        self.assertEqual(len(info_list), 1)
        self.assertEqual(info_list[0]["resource_name"], "CSV Resource")

    @patch("tddata.downloader.get_dataset_resources")
    @patch("tddata.downloader.get_latest_file")
    async def async_test_existing_file_same_size(self, mock_get_latest, mock_get_resources):
        """Test that existing files with same size are marked as not needing download."""
        # Mock CKAN API response
        mock_resources = [
            {
                "name": "Test Resource",
                "url": "https://example.com/test.csv",
                "format": "CSV",
                "size": "1024",
                "last_modified": "2026-02-07T10:00:00",
            }
        ]
        mock_get_resources.return_value = mock_resources

        # Mock existing file with same size
        mock_file = MagicMock(spec=Path)
        mock_file.stat.return_value.st_size = 1024
        mock_get_latest.return_value = mock_file

        # Test
        info_list = await get_download_info(self.dest_dir, self.dataset_id)

        # Should not download
        self.assertFalse(info_list[0]["would_download"])

    @patch("tddata.downloader.get_dataset_resources")
    @patch("tddata.downloader.get_latest_file")
    async def async_test_size_conversion(self, mock_get_latest, mock_get_resources):
        """Test that size strings are converted to integers."""
        # Mock CKAN API response with size as string
        mock_resources = [
            {
                "name": "Test Resource",
                "url": "https://example.com/test.csv",
                "format": "CSV",
                "size": "12345",
                "last_modified": "2026-02-07T10:00:00",
            }
        ]
        mock_get_resources.return_value = mock_resources
        mock_get_latest.return_value = None

        # Test
        info_list = await get_download_info(self.dest_dir, self.dataset_id)

        # Size should be an integer
        self.assertIsInstance(info_list[0]["size"], int)
        self.assertEqual(info_list[0]["size"], 12345)

    @patch("tddata.downloader.get_dataset_resources")
    async def async_test_error_handling(self, mock_get_resources):
        """Test error handling when API call fails."""
        # Mock API error
        mock_get_resources.side_effect = Exception("API Error")

        # Test should raise ValueError with descriptive message
        with self.assertRaises(ValueError) as context:
            await get_download_info(self.dest_dir, self.dataset_id)

        self.assertIn("Error fetching resources", str(context.exception))

    # Sync wrappers for async tests
    def test_basic_info_retrieval(self):
        asyncio.run(self.async_test_basic_info_retrieval())

    def test_skip_non_csv(self):
        asyncio.run(self.async_test_skip_non_csv())

    def test_existing_file_same_size(self):
        asyncio.run(self.async_test_existing_file_same_size())

    def test_size_conversion(self):
        asyncio.run(self.async_test_size_conversion())

    def test_error_handling(self):
        asyncio.run(self.async_test_error_handling())


if __name__ == "__main__":
    unittest.main()
