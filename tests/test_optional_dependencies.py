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

"""Tests for optional dependency handling.

This test verifies that tddata can be imported and used correctly
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
        import tddata

        # Core components should always be available
        self.assertIsNotNone(tddata.downloader)
        self.assertIn("downloader", tddata.__all__)

        # Constants should always be available
        self.assertIn("Column", tddata.__all__)
        self.assertIn("BondType", tddata.__all__)
        self.assertIn("OperationType", tddata.__all__)

    def test_analysis_extras_detection(self):
        """Test that _HAS_ANALYSIS flag is set correctly."""
        import tddata

        # _HAS_ANALYSIS should be a boolean
        self.assertIsInstance(tddata._HAS_ANALYSIS, bool)

        # If analysis is available, plot and reader should be in __all__
        if tddata._HAS_ANALYSIS:
            self.assertIn("plot", tddata.__all__)
            self.assertIn("reader", tddata.__all__)
            self.assertIsNotNone(tddata.plot)
            self.assertIsNotNone(tddata.reader)
        else:
            # Without analysis extras, these should not be in __all__
            self.assertNotIn("plot", tddata.__all__)
            self.assertNotIn("reader", tddata.__all__)

    def test_downloader_functions_available(self):
        """Test that downloader module has expected functions."""
        import tddata

        # These functions should be available without extras
        self.assertTrue(hasattr(tddata.downloader, "download"))
        self.assertTrue(hasattr(tddata.downloader, "download_resource"))
        self.assertTrue(hasattr(tddata.downloader, "get_dataset_resources"))

    @unittest.skipUnless(
        _has_polars(),
        "Requires analysis extras (polars, seaborn)",
    )
    def test_reader_functions_with_extras(self):
        """Test that reader module works when extras are installed."""
        import tddata

        self.assertTrue(tddata._HAS_ANALYSIS)
        self.assertIsNotNone(tddata.reader)

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
                hasattr(tddata.reader, reader_func),
                f"{reader_func} should be available",
            )

    @unittest.skipUnless(
        _has_polars(),
        "Requires analysis extras (polars, seaborn)",
    )
    def test_plot_functions_with_extras(self):
        """Test that plot module works when extras are installed."""
        import tddata

        self.assertTrue(tddata._HAS_ANALYSIS)
        self.assertIsNotNone(tddata.plot)

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
            self.assertTrue(hasattr(tddata.plot, plot_func), f"{plot_func} should be available")


if __name__ == "__main__":
    unittest.main()
