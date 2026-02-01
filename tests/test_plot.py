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

import matplotlib.pyplot as plt
import pandas as pd

from tddata import plot
from tddata.constants import Column


class TestPlot(unittest.TestCase):
    def setUp(self):
        # Create dummy data for testing
        self.stock_data = pd.DataFrame(
            {
                Column.STOCK_MONTH.value: [datetime(2024, 1, 1), datetime(2024, 2, 1)],
                Column.BOND_TYPE.value: ["Type A", "Type A"],
                Column.STOCK_VALUE.value: [1000.0, 1100.0],
            }
        )

        self.investors_data = pd.DataFrame(
            {
                Column.JOIN_DATE.value: [datetime(2024, 1, 1), datetime(2024, 1, 15)],
                Column.STATE.value: ["SP", "RJ"],
                Column.GENDER.value: ["M", "F"],
                Column.AGE.value: [30, 25],
            }
        )

        self.operations_data = pd.DataFrame(
            {
                Column.OPERATION_DATE.value: [
                    datetime(2024, 1, 1),
                    datetime(2024, 1, 2),
                ],
                Column.OPERATION_TYPE.value: ["Invest", "Invest"],
                Column.OPERATION_VALUE.value: [500.0, 600.0],
            }
        )

        self.sales_data = pd.DataFrame(
            {
                Column.SALE_DATE.value: [datetime(2024, 1, 1)],
                Column.VALUE.value: [1000.0],
                Column.BOND_TYPE.value: ["Type A"],
            }
        )

        self.buybacks_data = pd.DataFrame(
            {
                Column.BUYBACK_DATE.value: [datetime(2024, 1, 1)],
                Column.VALUE.value: [1000.0],
                Column.BOND_TYPE.value: ["Type A"],
            }
        )

        self.maturities_data = pd.DataFrame(
            {
                Column.BUYBACK_DATE.value: [datetime(2024, 1, 1)],
                Column.VALUE.value: [1000.0],
                Column.BOND_TYPE.value: ["Type A"],
            }
        )

        self.prices_data = pd.DataFrame(
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

    def tearDown(self):
        plt.close("all")

    def test_plot_stock(self):
        result = plot.plot_stock(self.stock_data)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], plt.Figure)
        self.assertIsInstance(result[1], plt.Axes)

        result = plot.plot_stock(self.stock_data, by_bond_type=False)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], plt.Figure)
        self.assertIsInstance(result[1], plt.Axes)

    def test_plot_investors_demographics(self):
        fig = plot.plot_investors_demographics(
            self.investors_data, column=Column.STATE.value
        )
        self.assertIsInstance(fig, plt.Figure)

        fig = plot.plot_investors_demographics(
            self.investors_data, column=Column.STATE.value, chart_type="pie"
        )
        self.assertIsInstance(fig, plt.Figure)

        fig = plot.plot_investors_demographics(
            self.investors_data, column=Column.STATE.value, chart_type="barh"
        )
        self.assertIsInstance(fig, plt.Figure)

    def test_plot_investors_population_pyramid(self):
        fig = plot.plot_investors_population_pyramid(self.investors_data)
        self.assertIsInstance(fig, plt.Figure)

    def test_plot_investors_evolution(self):
        result = plot.plot_investors_evolution(self.investors_data)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], plt.Figure)
        self.assertIsInstance(result[1], plt.Axes)

    def test_plot_operations(self):
        result = plot.plot_operations(self.operations_data)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], plt.Figure)
        self.assertIsInstance(result[1], plt.Axes)

        result = plot.plot_operations(self.operations_data, by_type=False)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], plt.Figure)
        self.assertIsInstance(result[1], plt.Axes)

    def test_plot_sales(self):
        result = plot.plot_sales(self.sales_data)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], plt.Figure)
        self.assertIsInstance(result[1], plt.Axes)

    def test_plot_buybacks(self):
        result = plot.plot_buybacks(self.buybacks_data)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], plt.Figure)
        self.assertIsInstance(result[1], plt.Axes)

    def test_plot_maturities(self):
        result = plot.plot_maturities(self.maturities_data)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], plt.Figure)
        self.assertIsInstance(result[1], plt.Axes)

    def test_plot_interest_coupons(self):
        # Interest coupons uses same structure as maturities
        result = plot.plot_interest_coupons(self.maturities_data)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], plt.Figure)
        self.assertIsInstance(result[1], plt.Axes)

    def test_plot_prices(self):
        fig = plot.plot_prices(self.prices_data, "Type A", Column.BUY_PRICE.value)
        self.assertIsInstance(fig, plt.Figure)


if __name__ == "__main__":
    unittest.main()
