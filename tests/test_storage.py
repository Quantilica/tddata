import shutil
import tempfile
import unittest
from pathlib import Path

from tesouro_direto_fetcher import storage


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_slugify(self):
        self.assertEqual(storage.slugify("Tesouro Selic"), "tesouro-selic")
        self.assertEqual(storage.slugify("Ação & Reação"), "acao-reacao")
        self.assertEqual(storage.slugify("  Spaces  "), "spaces")
        self.assertEqual(storage.slugify("Mixed_CASE"), "mixed_case")

    def test_generate_filename(self):
        # Test with explicit timestamp
        filename = storage.generate_filename(
            "Tesouro Selic", "2024-01-01T12:00:00.000000"
        )
        self.assertEqual(filename, "tesouro-selic@20240101T120000.csv")

        # Test with invalid timestamp (fallback to current time)
        # We can't easily check exact time, but we can check format
        filename = storage.generate_filename("Tesouro Selic", "invalid-date")
        self.assertTrue(filename.startswith("tesouro-selic@"))
        self.assertTrue(filename.endswith(".csv"))

        # Test without timestamp
        filename = storage.generate_filename("Tesouro Selic")
        self.assertTrue(filename.startswith("tesouro-selic@"))
        self.assertTrue(filename.endswith(".csv"))

    def test_get_latest_files(self):
        # Create dummy files
        (self.test_dir / "file-a@20240101T100000.csv").touch()
        (self.test_dir / "file-a@20240101T110000.csv").touch()  # Newer
        (self.test_dir / "file-b@20240101T100000.csv").touch()
        (self.test_dir / "other.txt").touch()  # Should be ignored

        latest_files = storage.get_latest_files(self.test_dir)

        self.assertEqual(len(latest_files), 2)
        filenames = [f.name for f in latest_files]
        self.assertIn("file-a@20240101T110000.csv", filenames)
        self.assertIn("file-b@20240101T100000.csv", filenames)
        self.assertNotIn("file-a@20240101T100000.csv", filenames)

    def test_get_latest_file(self):
        # Create dummy files
        (self.test_dir / "investors-2023@20240101T100000.csv").touch()
        (self.test_dir / "investors-2024@20240101T100000.csv").touch()
        (self.test_dir / "investors-2024@20240101T110000.csv").touch()  # Newer

        # Test finding latest file with pattern
        latest = storage.get_latest_file(self.test_dir, "investors-2024*.csv")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.name, "investors-2024@20240101T110000.csv")

        # Test pattern with no matches
        latest = storage.get_latest_file(self.test_dir, "nonexistent*.csv")
        self.assertIsNone(latest)


if __name__ == "__main__":
    unittest.main()
