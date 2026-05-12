import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from quantilica_core.exceptions import FetchError

from tesouro_direto_fetcher import downloader
from tesouro_direto_fetcher.downloader import _to_remote_resources
from tesouro_direto_fetcher.storage import DataRepository


CKAN_RESOURCES = [
    {
        "name": "Resource 1",
        "format": "CSV",
        "url": "http://example.com/file1.csv",
        "last_modified": "2024-01-01T12:00:00.000000",
        "size": 100,
    },
    {
        "name": "Resource 2",
        "format": "PDF",  # Should be filtered out
        "url": "http://example.com/file2.pdf",
    },
]


class TestToRemoteResources(unittest.TestCase):
    def test_filters_non_csv(self):
        repo = DataRepository(Path("."))
        result = _to_remote_resources(CKAN_RESOURCES, repo)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Resource 1")

    def test_computes_filename(self):
        repo = DataRepository(Path("."))
        result = _to_remote_resources(CKAN_RESOURCES, repo)
        self.assertEqual(result[0].filename, "resource-1@20240101T120000.csv")

    def test_parses_size(self):
        repo = DataRepository(Path("."))
        result = _to_remote_resources(CKAN_RESOURCES, repo)
        self.assertEqual(result[0].size, 100)

    def test_handles_missing_size(self):
        repo = DataRepository(Path("."))
        resources = [{"name": "R", "format": "CSV", "url": "http://x.com/r.csv"}]
        result = _to_remote_resources(resources, repo)
        self.assertEqual(result[0].size, 0)


class TestGetDatasetResources(unittest.IsolatedAsyncioTestCase):
    @patch("tesouro_direto_fetcher.downloader.client")
    async def test_success(self, mock_client):
        mock_client.get_json = AsyncMock(
            return_value={
                "success": True,
                "result": {"resources": [{"name": "R1"}, {"name": "R2"}]},
            }
        )
        resources = await downloader.get_dataset_resources("fake-id")
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0]["name"], "R1")

    @patch("tesouro_direto_fetcher.downloader.client")
    async def test_failure_raises_fetch_error(self, mock_client):
        mock_client.get_json = AsyncMock(
            return_value={"success": False, "error": "Dataset not found"}
        )
        with self.assertRaises(FetchError):
            await downloader.get_dataset_resources("bad-id")


class TestDownload(unittest.IsolatedAsyncioTestCase):
    @patch("tesouro_direto_fetcher.downloader.download_resources")
    @patch("tesouro_direto_fetcher.downloader.get_dataset_resources")
    async def test_delegates_to_download_resources(
        self, mock_get_resources, mock_dl_resources
    ):
        mock_get_resources.return_value = CKAN_RESOURCES
        mock_dl_resources.return_value = [
            {
                "url": "http://example.com/file1.csv",
                "filename": "resource-1@20240101T120000.csv",
                "destination": Path("/tmp/resource-1@20240101T120000.csv"),
                "file_size": 100,
            }
        ]

        results = await downloader.download(Path("/tmp"), "fake-dataset")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["filename"], "resource-1@20240101T120000.csv")
        mock_dl_resources.assert_called_once()

    @patch("tesouro_direto_fetcher.downloader.get_dataset_resources")
    async def test_returns_empty_on_no_csv(self, mock_get_resources):
        mock_get_resources.return_value = [
            {"name": "PDF Only", "format": "PDF", "url": "http://x.com/f.pdf"}
        ]
        results = await downloader.download(Path("/tmp"), "fake-dataset")
        self.assertEqual(results, [])

    @patch("tesouro_direto_fetcher.downloader.get_dataset_resources")
    async def test_returns_empty_on_api_error(self, mock_get_resources):
        mock_get_resources.side_effect = Exception("Network error")
        results = await downloader.download(Path("/tmp"), "fake-dataset")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
