"""Tests for optional dependency handling.

This test verifies that tesouro-direto-fetcher can be imported and used correctly
both with and without the optional analysis extras.
"""

import sys
import unittest
from unittest.mock import patch


def _has_polars():
    """Check if polars is available."""
    try:
        import polars  # noqa: F401

        return True
    except ImportError:
        return False


class TestOptionalDependencies(unittest.TestCase):
    """Test that the package handles optional dependencies correctly."""

    def test_core_imports_always_available(self):
        """Core imports should always be available."""
        import tesouro_direto_fetcher

        # Core components should always be available
        self.assertIsNotNone(tesouro_direto_fetcher.downloader)
        self.assertIn("downloader", tesouro_direto_fetcher.__all__)

        # Constants should always be available
        self.assertIn("Column", tesouro_direto_fetcher.__all__)
        self.assertIn("BondType", tesouro_direto_fetcher.__all__)
        self.assertIn("OperationType", tesouro_direto_fetcher.__all__)

    def test_analysis_extras_detection(self):
        """Test that _HAS_ANALYSIS flag is set correctly."""
        import tesouro_direto_fetcher

        # _HAS_ANALYSIS should be a boolean
        self.assertIsInstance(tesouro_direto_fetcher._HAS_ANALYSIS, bool)

        # If analysis is available, plot and reader should be in __all__
        if tesouro_direto_fetcher._HAS_ANALYSIS:
            self.assertIn("plot", tesouro_direto_fetcher.__all__)
            self.assertIn("reader", tesouro_direto_fetcher.__all__)
            self.assertIsNotNone(tesouro_direto_fetcher.plot)
            self.assertIsNotNone(tesouro_direto_fetcher.reader)
        else:
            # Without analysis extras, these should not be in __all__
            self.assertNotIn("plot", tesouro_direto_fetcher.__all__)
            self.assertNotIn("reader", tesouro_direto_fetcher.__all__)

    def test_downloader_functions_available(self):
        """Test that downloader module has expected functions."""
        import tesouro_direto_fetcher

        # These functions should be available without extras
        self.assertTrue(hasattr(tesouro_direto_fetcher.downloader, "download"))
        self.assertTrue(hasattr(tesouro_direto_fetcher.downloader, "download_resource"))
        self.assertTrue(hasattr(tesouro_direto_fetcher.downloader, "get_dataset_resources"))

    @unittest.skipUnless(
        _has_polars(),
        "Requires analysis extras (polars, seaborn)",
    )
    def test_reader_functions_with_extras(self):
        """Test that reader module works when extras are installed."""
        import tesouro_direto_fetcher

        self.assertTrue(tesouro_direto_fetcher._HAS_ANALYSIS)
        self.assertIsNotNone(tesouro_direto_fetcher.reader)

        # Check that all read functions are available
        expected_readers = [
            "read_prices",
            "read_stock",
            "read_investors",
            "read_operations",
            "read_sales",
            "read_buybacks",
            "read_maturities",
            "read_interest_coupons",
        ]
        for reader_func in expected_readers:
            self.assertTrue(
                hasattr(tesouro_direto_fetcher.reader, reader_func),
                f"{reader_func} should be available",
            )

    @unittest.skipUnless(
        _has_polars(),
        "Requires analysis extras (polars, seaborn)",
    )
    def test_plot_functions_with_extras(self):
        """Test that plot module works when extras are installed."""
        import tesouro_direto_fetcher

        self.assertTrue(tesouro_direto_fetcher._HAS_ANALYSIS)
        self.assertIsNotNone(tesouro_direto_fetcher.plot)

        # Check that plot functions are available
        expected_plotters = [
            "plot_prices",
            "plot_stock",
            "plot_investors_evolution",
            "plot_operations",
            "plot_sales",
            "plot_buybacks",
        ]
        for plot_func in expected_plotters:
            self.assertTrue(hasattr(tesouro_direto_fetcher.plot, plot_func), f"{plot_func} should be available")


if __name__ == "__main__":
    unittest.main()
