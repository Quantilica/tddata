import shutil
import tempfile
import unittest
from pathlib import Path

from tesouro_direto_fetcher import storage
from tesouro_direto_fetcher.storage import DataRepository


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(storage.slugify("Tesouro Selic"), "tesouro-selic")
        self.assertEqual(storage.slugify("Ação & Reação"), "acao-reacao")
        self.assertEqual(storage.slugify("  Spaces  "), "spaces")
        self.assertEqual(storage.slugify("Mixed_CASE"), "mixed_case")


class TestGenerateFilename(unittest.TestCase):
    def test_with_valid_timestamp(self):
        filename = DataRepository.generate_filename(
            "Tesouro Selic", "2024-01-01T12:00:00.000000"
        )
        self.assertEqual(filename, "tesouro-selic@20240101T120000.csv")

    def test_with_invalid_timestamp(self):
        filename = DataRepository.generate_filename("Tesouro Selic", "invalid-date")
        self.assertEqual(filename, "tesouro-selic.csv")

    def test_without_timestamp(self):
        filename = DataRepository.generate_filename("Tesouro Selic")
        self.assertEqual(filename, "tesouro-selic.csv")


class TestDataRepository(unittest.TestCase):
    DATASET_ID = "tesouro-direto"

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.repo = DataRepository(self.test_dir)
        self.dataset_dir = self.repo.raw_path(self.DATASET_ID)
        self.dataset_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _touch(self, name: str) -> Path:
        p = self.dataset_dir / name
        p.touch()
        return p

    def test_get_all_latest_files(self):
        self._touch("file-a@20240101T100000.csv")
        self._touch("file-a@20240101T110000.csv")  # Newer
        self._touch("file-b@20240101T100000.csv")
        self._touch("other.txt")  # Should be ignored

        latest = self.repo.get_all_latest_files(self.DATASET_ID)

        self.assertEqual(len(latest), 2)
        names = [f.name for f in latest]
        self.assertIn("file-a@20240101T110000.csv", names)
        self.assertIn("file-b@20240101T100000.csv", names)
        self.assertNotIn("file-a@20240101T100000.csv", names)

    def test_get_latest_file(self):
        self._touch("investors-2023@20240101T100000.csv")
        self._touch("investors-2024@20240101T100000.csv")
        self._touch("investors-2024@20240101T110000.csv")  # Newer

        latest = self.repo.get_latest_file(self.DATASET_ID, "investors-2024*.csv")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.name, "investors-2024@20240101T110000.csv")

        latest = self.repo.get_latest_file(self.DATASET_ID, "nonexistent*.csv")
        self.assertIsNone(latest)


if __name__ == "__main__":
    unittest.main()
