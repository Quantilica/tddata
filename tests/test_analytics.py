# Copyright (C) 2020-2026 Daniel Kiyoyudi Komesu
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


import unittest
from datetime import datetime

import polars as pl

from tddata import analytics
from tddata.constants import Column


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.prices_data = pl.DataFrame(
            {
                Column.REFERENCE_DATE.value: [
                    datetime(2024, 1, 2),
                    datetime(2024, 1, 1),
                    datetime(2024, 1, 3),
                ],
                Column.MATURITY_DATE.value: [
                    datetime(2025, 1, 1),
                    datetime(2025, 1, 1),
                    datetime(2026, 1, 1),
                ],
                Column.BOND_TYPE.value: ["Type A", "Type A", "Type B"],
                Column.BUY_PRICE.value: [905.0, 900.0, 1000.0],
                Column.SELL_PRICE.value: [895.0, 890.0, 990.0],
            }
        )
        self.prices_data_with_zeros = pl.DataFrame(
            {
                Column.REFERENCE_DATE.value: [
                    datetime(2024, 1, 2),
                    datetime(2024, 1, 1),
                ],
                Column.MATURITY_DATE.value: [
                    datetime(2025, 1, 1),
                    datetime(2025, 1, 1),
                ],
                Column.BOND_TYPE.value: ["Type A", "Type A"],
                Column.BUY_PRICE.value: [905.0, 0],
                Column.SELL_PRICE.value: [895.0, 890.0],
            }
        )

    def test_prepare_prices(self):
        # Test filtering by bond type
        result = analytics.prepare_prices(self.prices_data, "Type A")
        self.assertEqual(result.height, 2)
        self.assertTrue((result[Column.BOND_TYPE.value] == "Type A").all())

        # Test sorting
        expected_dates = [datetime(2024, 1, 1), datetime(2024, 1, 2)]
        self.assertListEqual(result[Column.REFERENCE_DATE.value].to_list(), expected_dates)

        # Test filtering out zero prices
        result_with_zeros = analytics.prepare_prices(self.prices_data_with_zeros, "Type A")
        self.assertEqual(result_with_zeros.height, 1)
        self.assertEqual(result_with_zeros[Column.BUY_PRICE.value][0], 905.0)


if __name__ == "__main__":
    unittest.main()
