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

import altair as alt
import polars as pl

from tddata import analytics, plot
from tddata.constants import Column


class TestPlot(unittest.TestCase):
    def setUp(self):
        # Create dummy data for testing
        self.stock_data = pl.DataFrame(
            {
                Column.STOCK_MONTH.value: [datetime(2024, 1, 1), datetime(2024, 2, 1)],
                Column.BOND_TYPE.value: ["Type A", "Type A"],
                Column.STOCK_VALUE.value: [1000.0, 1100.0],
            }
        )

        self.investors_data = pl.DataFrame(
            {
                Column.JOIN_DATE.value: [datetime(2024, 1, 1), datetime(2024, 1, 15)],
                Column.STATE.value: ["SP", "RJ"],
                Column.GENDER.value: ["M", "F"],
                Column.AGE.value: [30, 25],
            }
        )

        self.operations_data = pl.DataFrame(
            {
                Column.OPERATION_DATE.value: [
                    datetime(2024, 1, 1),
                    datetime(2024, 1, 2),
                ],
                Column.OPERATION_TYPE.value: ["Invest", "Invest"],
                Column.OPERATION_VALUE.value: [500.0, 600.0],
            }
        )

        self.sales_data = pl.DataFrame(
            {
                Column.SALE_DATE.value: [datetime(2024, 1, 1)],
                Column.VALUE.value: [1000.0],
                Column.BOND_TYPE.value: ["Type A"],
            }
        )

        self.buybacks_data = pl.DataFrame(
            {
                Column.BUYBACK_DATE.value: [datetime(2024, 1, 1)],
                Column.VALUE.value: [1000.0],
                Column.BOND_TYPE.value: ["Type A"],
            }
        )

        self.maturities_data = pl.DataFrame(
            {
                Column.BUYBACK_DATE.value: [datetime(2024, 1, 1)],
                Column.VALUE.value: [1000.0],
                Column.BOND_TYPE.value: ["Type A"],
            }
        )

        self.prices_data = pl.DataFrame(
            {
                Column.REFERENCE_DATE.value: [
                    datetime(2024, 1, 1),
                    datetime(2024, 1, 2),
                ],
                Column.MATURITY_DATE.value: [
                    datetime(2025, 1, 1),
                    datetime(2025, 1, 1),
                ],
                Column.BOND_TYPE.value: ["Type A", "Type A"],
                Column.BUY_PRICE.value: [900.0, 905.0],
                Column.SELL_PRICE.value: [890.0, 895.0],
            }
        )

    def test_plot_stock(self):
        chart = plot.plot_stock(self.stock_data)
        self.assertIsInstance(chart, alt.Chart)

        chart = plot.plot_stock(self.stock_data, by_bond_type=False)
        self.assertIsInstance(chart, alt.Chart)

    def test_plot_investors_demographics(self):
        chart = plot.plot_investors_demographics(self.investors_data, column=Column.STATE.value)
        self.assertIsInstance(chart, alt.Chart)

        chart = plot.plot_investors_demographics(self.investors_data, column=Column.STATE.value, chart_type="pie")
        self.assertIsInstance(chart, alt.Chart)

        chart = plot.plot_investors_demographics(self.investors_data, column=Column.STATE.value, chart_type="barh")
        self.assertIsInstance(chart, alt.Chart)

    def test_plot_investors_population_pyramid(self):
        chart = plot.plot_investors_population_pyramid(self.investors_data)
        self.assertIsInstance(chart, alt.Chart)

    def test_plot_investors_population_pyramid_sort(self):
        # Create ages spanning bins and ensure chart uses explicit y-sort matching analytics
        data = pl.DataFrame(
            {
                Column.AGE.value: [25, 45, 5],
                Column.GENDER.value: ["M", "F", "M"],
            }
        )
        chart = plot.plot_investors_population_pyramid(data)
        chart_dict = chart.to_dict()
        y_sort = chart_dict.get("encoding", {}).get("y", {}).get("sort")

        expected_order = analytics.prepare_population_pyramid(data)["age_group"].to_list()
        self.assertEqual(y_sort, expected_order)

    def test_plot_investors_evolution(self):
        chart = plot.plot_investors_evolution(self.investors_data)
        self.assertIsInstance(chart, alt.Chart)

    def test_plot_operations(self):
        chart = plot.plot_operations(self.operations_data)
        self.assertIsInstance(chart, alt.Chart)

        chart = plot.plot_operations(self.operations_data, by_type=False)
        self.assertIsInstance(chart, alt.Chart)

    def test_plot_sales(self):
        chart = plot.plot_sales(self.sales_data)
        self.assertIsInstance(chart, alt.Chart)

    def test_plot_buybacks(self):
        chart = plot.plot_buybacks(self.buybacks_data)
        self.assertIsInstance(chart, alt.Chart)

    def test_plot_maturities(self):
        chart = plot.plot_maturities(self.maturities_data)
        self.assertIsInstance(chart, alt.Chart)

    def test_plot_interest_coupons(self):
        # Interest coupons uses same structure as maturities
        chart = plot.plot_interest_coupons(self.maturities_data)
        self.assertIsInstance(chart, alt.Chart)

    def test_plot_prices(self):
        chart = plot.plot_prices(self.prices_data, "Type A", Column.BUY_PRICE.value)
        self.assertIsInstance(chart, alt.Chart)


if __name__ == "__main__":
    unittest.main()
