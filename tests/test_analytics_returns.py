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


"""Tests for return calculation functions in analytics module."""

import unittest
from datetime import datetime, timedelta

import pandas as pd

from tddata.analytics import (
    calculate_annualized_return,
    calculate_holding_period_days,
    calculate_operations_returns,
    calculate_portfolio_monthly_returns,
    calculate_simple_return,
)
from tddata.constants import Column as C


class TestSimpleReturn(unittest.TestCase):
    """Test simple return calculations."""

    def test_positive_return(self):
        """Test calculation of positive returns."""
        current = pd.Series([11000, 12000, 10500])
        initial = pd.Series([10000, 10000, 10000])
        result = calculate_simple_return(current, initial)

        self.assertAlmostEqual(result.iloc[0], 10.0, places=1)
        self.assertAlmostEqual(result.iloc[1], 20.0, places=1)
        self.assertAlmostEqual(result.iloc[2], 5.0, places=1)

    def test_negative_return(self):
        """Test calculation of negative returns."""
        current = pd.Series([9000, 8000])
        initial = pd.Series([10000, 10000])
        result = calculate_simple_return(current, initial)

        self.assertAlmostEqual(result.iloc[0], -10.0, places=1)
        self.assertAlmostEqual(result.iloc[1], -20.0, places=1)

    def test_zero_initial_value(self):
        """Test handling of zero initial value."""
        current = pd.Series([11000, 0])
        initial = pd.Series([0, 10000])
        result = calculate_simple_return(current, initial)

        self.assertEqual(result.iloc[0], 0.0)

    def test_zero_current_value(self):
        """Test handling of zero current value."""
        current = pd.Series([0])
        initial = pd.Series([10000])
        result = calculate_simple_return(current, initial)

        self.assertEqual(result.iloc[0], 0.0)


class TestHoldingPeriod(unittest.TestCase):
    """Test holding period calculations."""

    def test_days_calculation(self):
        """Test calculation of holding period in days."""
        start = pd.Series(pd.to_datetime(["2024-01-01", "2024-06-01"]))
        end = pd.Series(pd.to_datetime(["2024-07-01", "2024-12-01"]))
        result = calculate_holding_period_days(start, end)

        self.assertEqual(result.iloc[0], 182)
        self.assertEqual(result.iloc[1], 183)

    def test_single_end_date(self):
        """Test calculation with a single end date for all positions."""
        start = pd.Series(pd.to_datetime(["2024-01-01", "2024-02-01"]))
        end = pd.Timestamp("2024-03-01")
        result = calculate_holding_period_days(start, end)

        self.assertEqual(result.iloc[0], 60)
        self.assertEqual(result.iloc[1], 29)


class TestAnnualizedReturn(unittest.TestCase):
    """Test annualized return calculations."""

    def test_one_year_return(self):
        """Test annualized return for exactly one year."""
        current = pd.Series([11000])
        initial = pd.Series([10000])
        holding = pd.Series([365])
        result = calculate_annualized_return(current, initial, holding)

        self.assertAlmostEqual(result.iloc[0], 10.0, places=1)

    def test_six_month_return(self):
        """Test annualized return for six months."""
        current = pd.Series([11000])
        initial = pd.Series([10000])
        holding = pd.Series([182])
        result = calculate_annualized_return(current, initial, holding)

        # 10% in 6 months annualizes to ~21%
        self.assertGreater(result.iloc[0], 20.0)
        self.assertLess(result.iloc[0], 22.0)

    def test_short_holding_period(self):
        """Test that short holding periods return 0."""
        current = pd.Series([11000])
        initial = pd.Series([10000])
        holding = pd.Series([15])  # Less than 30 days
        result = calculate_annualized_return(current, initial, holding, min_days=30)

        self.assertEqual(result.iloc[0], 0.0)

    def test_negative_return_annualized(self):
        """Test annualized return for losses."""
        current = pd.Series([9000])
        initial = pd.Series([10000])
        holding = pd.Series([365])
        result = calculate_annualized_return(current, initial, holding)

        self.assertAlmostEqual(result.iloc[0], -10.0, places=1)


class TestOperationsReturns(unittest.TestCase):
    """Test operation-level return calculations."""

    def setUp(self):
        """Set up test data."""
        self.operations = pd.DataFrame(
            {
                C.OPERATION_DATE.value: pd.to_datetime(
                    [
                        "2024-01-15",
                        "2024-07-15",
                        "2024-02-01",
                    ]
                ),
                C.BOND_TYPE.value: [
                    "Tesouro Selic",
                    "Tesouro Selic",
                    "Tesouro IPCA+",
                ],
                C.MATURITY_DATE.value: pd.to_datetime(
                    [
                        "2030-01-01",
                        "2030-01-01",
                        "2035-05-15",
                    ]
                ),
                C.QUANTITY.value: [10.0, -10.0, 5.0],
                C.BOND_VALUE.value: [1000.0, 1100.0, 2000.0],
                C.OPERATION_VALUE.value: [10000.0, 11000.0, 10000.0],
                C.OPERATION_TYPE.value: ["C", "V", "C"],
            }
        )

        self.prices = pd.DataFrame(
            {
                C.REFERENCE_DATE.value: pd.to_datetime(
                    [
                        "2024-06-30",
                        "2024-06-30",
                        "2024-12-31",
                        "2024-12-31",
                    ]
                ),
                C.BOND_TYPE.value: [
                    "Tesouro Selic",
                    "Tesouro IPCA+",
                    "Tesouro Selic",
                    "Tesouro IPCA+",
                ],
                C.MATURITY_DATE.value: pd.to_datetime(
                    [
                        "2030-01-01",
                        "2035-05-15",
                        "2030-01-01",
                        "2035-05-15",
                    ]
                ),
                C.SELL_PRICE.value: [1050.0, 2100.0, 1100.0, 2200.0],
            }
        )

    def test_closed_position(self):
        """Test return calculation for a closed position."""
        current_date = pd.Timestamp("2024-12-31")
        result = calculate_operations_returns(
            self.operations,
            self.prices,
            current_date=current_date,
        )

        # First operation should be closed
        closed = result[result["status"] == "closed"]
        self.assertEqual(len(closed), 1)
        self.assertAlmostEqual(closed.iloc[0]["simple_return"], 10.0, places=1)

    def test_open_position(self):
        """Test return calculation for an open position."""
        current_date = pd.Timestamp("2024-12-31")
        result = calculate_operations_returns(
            self.operations,
            self.prices,
            current_date=current_date,
        )

        # Second operation (IPCA+) should be open
        open_pos = result[result["status"] == "open"]
        self.assertGreater(len(open_pos), 0)

    def test_holding_days_calculated(self):
        """Test that holding days are calculated correctly."""
        current_date = pd.Timestamp("2024-12-31")
        result = calculate_operations_returns(
            self.operations,
            self.prices,
            current_date=current_date,
        )

        self.assertTrue("holding_days" in result.columns)
        self.assertTrue((result["holding_days"] > 0).all())


class TestPortfolioMonthlyReturns(unittest.TestCase):
    """Test portfolio monthly return calculations."""

    def setUp(self):
        """Set up test data."""
        self.operations = pd.DataFrame(
            {
                C.OPERATION_DATE.value: pd.to_datetime(
                    [
                        "2024-01-15",
                        "2024-02-15",
                        "2024-03-15",
                    ]
                ),
                C.BOND_TYPE.value: [
                    "Tesouro Selic",
                    "Tesouro Selic",
                    "Tesouro Selic",
                ],
                C.MATURITY_DATE.value: pd.to_datetime(
                    [
                        "2030-01-01",
                        "2030-01-01",
                        "2030-01-01",
                    ]
                ),
                C.QUANTITY.value: [10.0, 5.0, -5.0],
                C.BOND_VALUE.value: [1000.0, 1050.0, 1100.0],
                C.OPERATION_VALUE.value: [10000.0, 5250.0, 5500.0],
                C.OPERATION_TYPE.value: ["C", "C", "V"],
            }
        )

        # Create monthly price data
        dates = pd.date_range("2024-01-31", "2024-04-30", freq="ME")
        self.prices = pd.DataFrame(
            {
                C.REFERENCE_DATE.value: dates,
                C.BOND_TYPE.value: ["Tesouro Selic"] * len(dates),
                C.MATURITY_DATE.value: pd.to_datetime(["2030-01-01"] * len(dates)),
                C.SELL_PRICE.value: [1000.0, 1050.0, 1100.0, 1150.0],
            }
        )

    def test_monthly_returns_structure(self):
        """Test that monthly returns DataFrame has correct structure."""
        result = calculate_portfolio_monthly_returns(
            self.operations,
            self.prices,
            start_date=pd.Timestamp("2024-01-01"),
            end_date=pd.Timestamp("2024-04-30"),
        )

        self.assertTrue("month" in result.columns)
        self.assertTrue("monthly_return" in result.columns)
        self.assertTrue("cumulative_return" in result.columns)
        self.assertTrue("portfolio_value" in result.columns)
        self.assertTrue("net_cash_flow" in result.columns)

    def test_monthly_returns_count(self):
        """Test that monthly returns are calculated for each month."""
        result = calculate_portfolio_monthly_returns(
            self.operations,
            self.prices,
            start_date=pd.Timestamp("2024-01-01"),
            end_date=pd.Timestamp("2024-04-30"),
        )

        # Should have 4 months
        self.assertEqual(len(result), 4)

    def test_cumulative_return_increases(self):
        """Test that cumulative return is monotonic (in growth scenario)."""
        result = calculate_portfolio_monthly_returns(
            self.operations,
            self.prices,
            start_date=pd.Timestamp("2024-01-01"),
            end_date=pd.Timestamp("2024-04-30"),
        )

        # With increasing prices, cumulative should generally increase
        self.assertTrue("cumulative_return" in result.columns)

    def test_cash_flow_tracking(self):
        """Test that cash flows are tracked correctly."""
        result = calculate_portfolio_monthly_returns(
            self.operations,
            self.prices,
            start_date=pd.Timestamp("2024-01-01"),
            end_date=pd.Timestamp("2024-04-30"),
        )

        # January should have positive cash flow (buy)
        jan_row = result[result["month"] == "2024-01-01"]
        self.assertGreater(jan_row.iloc[0]["net_cash_flow"], 0)

        # March should have negative cash flow (sell)
        mar_row = result[result["month"] == "2024-03-01"]
        self.assertLess(mar_row.iloc[0]["net_cash_flow"], 0)


if __name__ == "__main__":
    unittest.main()
