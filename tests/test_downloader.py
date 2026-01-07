# Copyright (C) 2020-2025 Daniel Kiyoyudi Komesu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tddata import downloader


class TestDownloader(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("tddata.downloader.httpx.AsyncClient")
    async def test_get_dataset_resources(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "resources": [
                    {"name": "Resource 1", "format": "CSV"},
                    {"name": "Resource 2", "format": "PDF"},
                ]
            },
        }
        mock_response.status_code = 200

        # Async mock setup
        future = asyncio.Future()
        future.set_result(mock_response)
        mock_client.get.return_value = future

        # When AsyncClient is instantiated, return our mock
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # We need to manually invoke the function with the client to test it in isolation
        # Or test 'download' which calls it.
        # But get_dataset_resources uses a client instance.
        # Let's test the logic by calling it directly.

        resources = await downloader.get_dataset_resources(mock_client, "fake-id")
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0]["name"], "Resource 1")

    @patch("tddata.downloader.httpx.AsyncClient")
    async def test_get_dataset_resources_failure(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "error": "Dataset not found",
        }
        mock_response.status_code = 200

        future = asyncio.Future()
        future.set_result(mock_response)
        mock_client.get.return_value = future

        with self.assertRaises(ValueError):
            await downloader.get_dataset_resources(mock_client, "bad-id")

    @patch("tddata.downloader.get_dataset_resources")
    @patch("tddata.downloader.httpx.AsyncClient")
    async def test_download_success(self, mock_client_cls, mock_get_resources):
        # Mock resources
        mock_get_resources.return_value = [
            {
                "name": "Resource 1",
                "format": "CSV",
                "url": "http://example.com/file1.csv",
                "last_modified": "2024-01-01T12:00:00.000000",
                "size": 100,
            },
            {
                "name": "Resource 2",
                "format": "PDF",  # Should be skipped
                "url": "http://example.com/file2.pdf",
            },
        ]

        # Mock client and stream
        mock_client = MagicMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock stream response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Length": "12"}

        # aiter_bytes needs to be an async iterator
        async def async_iter():
            yield b"chunk1"
            yield b"chunk2"

        mock_response.aiter_bytes = lambda chunk_size: async_iter()

        # stream is an async context manager
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__.return_value = mock_response
        mock_stream_ctx.__aexit__.return_value = None

        # stream method returns the context manager
        mock_client.stream.return_value = mock_stream_ctx

        # Execute download
        results = await downloader.download(self.test_dir, "fake-dataset")

        # Verify
        expected_filename = "resource-1@20240101T120000.csv"
        expected_path = self.test_dir / expected_filename

        self.assertTrue(expected_path.exists())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["filename"], expected_filename)

        with open(expected_path, "rb") as f:
            content = f.read()
        self.assertEqual(content, b"chunk1chunk2")

    @patch("tddata.downloader.get_dataset_resources")
    @patch("tddata.downloader.httpx.AsyncClient")
    async def test_download_skip_existing(self, mock_client_cls, mock_get_resources):
        # Set up an existing file
        filename = "resource-1@20240101T120000.csv"
        filepath = self.test_dir / filename
        with open(filepath, "w") as f:
            f.write("existing content")

        mock_get_resources.return_value = [
            {
                "name": "Resource 1",
                "format": "CSV",
                "url": "http://example.com/file1.csv",
                "last_modified": "2024-01-01T12:00:00.000000",
                "size": 100,
            }
        ]

        mock_client = MagicMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Execute download (should skip)
        results = await downloader.download(self.test_dir, "fake-dataset")

        # Verify no stream call was made
        mock_client.stream.assert_not_called()

        self.assertEqual(
            len(results), 0
        )  # The async download returns only downloaded files, filter None
        # Actually my implementation filters None. existing files return None in download_resource.
        # Wait, I should double check implementation.
        # "Filter out None values".
        # If it exists, download_resource returns None.
        # So results should be empty list?
        # Let's check download_resource implementation.
        # if dest_filepath.exists(): return None.
        # So yes, results will be empty.

        # Check that content is unchanged
        with open(filepath, "r") as f:
            self.assertEqual(f.read(), "existing content")


if __name__ == "__main__":
    unittest.main()
