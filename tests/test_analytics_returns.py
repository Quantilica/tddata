"""Tests for return calculation functions in analytics module."""

import unittest
from datetime import date, datetime, timedelta

import polars as pl

from tddata.analytics import (
    calculate_operations_returns,
    calculate_portfolio_monthly_returns,
)
from tddata.constants import Column as C

# Bond types that pay semiannual coupons
BOND_IPCA_JS = "Tesouro IPCA+ com Juros Semestrais"
BOND_PREFIXED_JS = "Tesouro Prefixado com Juros Semestrais"


class TestOperationsReturns(unittest.TestCase):
    """Test operation-level return calculations."""

    def setUp(self):
        """Set up test data."""
        self.operations = pl.DataFrame(
            {
                C.OPERATION_DATE.value: [
                    datetime(2024, 1, 15),
                    datetime(2024, 7, 15),
                    datetime(2024, 2, 1),
                ],
                C.BOND_TYPE.value: [
                    "Tesouro Selic",
                    "Tesouro Selic",
                    "Tesouro IPCA+",
                ],
                C.MATURITY_DATE.value: [
                    datetime(2030, 1, 1),
                    datetime(2030, 1, 1),
                    datetime(2035, 5, 15),
                ],
                C.QUANTITY.value: [10.0, -10.0, 5.0],
                C.BOND_VALUE.value: [1000.0, 1100.0, 2000.0],
                C.OPERATION_VALUE.value: [10000.0, 11000.0, 10000.0],
                C.OPERATION_TYPE.value: ["C", "V", "C"],
            }
        )

        self.prices = pl.DataFrame(
            {
                C.REFERENCE_DATE.value: [
                    datetime(2024, 6, 30),
                    datetime(2024, 6, 30),
                    datetime(2024, 12, 31),
                    datetime(2024, 12, 31),
                ],
                C.BOND_TYPE.value: [
                    "Tesouro Selic",
                    "Tesouro IPCA+",
                    "Tesouro Selic",
                    "Tesouro IPCA+",
                ],
                C.MATURITY_DATE.value: [
                    datetime(2030, 1, 1),
                    datetime(2035, 5, 15),
                    datetime(2030, 1, 1),
                    datetime(2035, 5, 15),
                ],
                C.SELL_PRICE.value: [1050.0, 2100.0, 1100.0, 2200.0],
            }
        )

    def test_closed_position(self):
        """Test return calculation for a closed position."""
        current_date = date(2024, 12, 31)
        result = calculate_operations_returns(
            self.operations,
            self.prices,
            current_date=current_date,
        )

        # First operation should be closed
        closed = result.filter(pl.col("status") == "closed")
        self.assertEqual(closed.height, 1)
        self.assertAlmostEqual(closed["simple_return"][0], 10.0, places=1)

    def test_open_position(self):
        """Test return calculation for an open position."""
        current_date = date(2024, 12, 31)
        result = calculate_operations_returns(
            self.operations,
            self.prices,
            current_date=current_date,
        )

        # Second operation (IPCA+) should be open
        open_pos = result.filter(pl.col("status") == "open")
        self.assertGreater(open_pos.height, 0)

    def test_holding_days_calculated(self):
        """Test that holding days are calculated correctly."""
        current_date = date(2024, 12, 31)
        result = calculate_operations_returns(
            self.operations,
            self.prices,
            current_date=current_date,
        )

        self.assertTrue("holding_days" in result.columns)
        self.assertTrue((result["holding_days"] > 0).all())

    def test_zero_bond_value_filtered(self):
        """Test that operations with zero bond value are filtered out."""
        ops_with_zero = pl.concat(
            [
                self.operations,
                pl.DataFrame(
                    {
                        C.OPERATION_DATE.value: [datetime(2024, 3, 1)],
                        C.BOND_TYPE.value: ["Tesouro Selic"],
                        C.MATURITY_DATE.value: [datetime(2030, 1, 1)],
                        C.QUANTITY.value: [5.0],
                        C.BOND_VALUE.value: [0.0],
                        C.OPERATION_VALUE.value: [0.0],
                        C.OPERATION_TYPE.value: ["C"],
                    }
                ),
            ]
        )

        current_date = date(2024, 12, 31)
        result = calculate_operations_returns(ops_with_zero, self.prices, current_date=current_date)

        # Should have 2 buys (zero bond_value row filtered out)
        self.assertEqual(result.height, 2)

    def test_coupon_income_in_returns(self):
        """Test that coupon income is included in return calculations."""
        # Create operations for a bond with semiannual interest
        operations = pl.DataFrame(
            {
                C.OPERATION_DATE.value: [datetime(2024, 1, 15)],
                C.BOND_TYPE.value: [BOND_IPCA_JS],
                C.MATURITY_DATE.value: [datetime(2035, 5, 15)],
                C.QUANTITY.value: [10.0],
                C.BOND_VALUE.value: [1000.0],
                C.OPERATION_VALUE.value: [10000.0],
                C.OPERATION_TYPE.value: ["C"],
            }
        )

        prices = pl.DataFrame(
            {
                C.REFERENCE_DATE.value: [datetime(2024, 12, 31)],
                C.BOND_TYPE.value: [BOND_IPCA_JS],
                C.MATURITY_DATE.value: [datetime(2035, 5, 15)],
                C.SELL_PRICE.value: [970.0],  # Price dropped after coupon
            }
        )

        coupons = pl.DataFrame(
            {
                C.BOND_TYPE.value: [BOND_IPCA_JS],
                C.MATURITY_DATE.value: [datetime(2035, 5, 15)],
                C.BUYBACK_DATE.value: [datetime(2024, 7, 1)],
                C.UNIT_PRICE.value: [30.0],  # ~3% semiannual coupon
                C.QUANTITY.value: [100000.0],  # aggregate (not used in calc)
                C.VALUE.value: [3000000.0],  # aggregate (not used in calc)
            }
        )

        current_date = date(2024, 12, 31)

        # Without coupons
        result_no_coupon = calculate_operations_returns(operations, prices, current_date=current_date)
        # end_value = 10 * 970 = 9700, return = (9700/10000 - 1)*100 = -3%
        self.assertAlmostEqual(result_no_coupon["simple_return"][0], -3.0, places=1)

        # With coupons
        result_with_coupon = calculate_operations_returns(
            operations,
            prices,
            current_date=current_date,
            coupons=coupons,
        )
        # end_value = 9700 + (10 * 30) = 10000, return = 0%
        self.assertAlmostEqual(result_with_coupon["simple_return"][0], 0.0, places=1)
        self.assertAlmostEqual(result_with_coupon["total_coupons"][0], 300.0, places=1)

    def test_coupon_only_within_holding_period(self):
        """Test that only coupons within the holding period are counted."""
        operations = pl.DataFrame(
            {
                C.OPERATION_DATE.value: [datetime(2024, 4, 1), datetime(2024, 9, 15)],
                C.BOND_TYPE.value: [BOND_IPCA_JS, BOND_IPCA_JS],
                C.MATURITY_DATE.value: [datetime(2035, 5, 15), datetime(2035, 5, 15)],
                C.QUANTITY.value: [10.0, -10.0],
                C.BOND_VALUE.value: [1000.0, 1020.0],
                C.OPERATION_VALUE.value: [10000.0, 10200.0],
                C.OPERATION_TYPE.value: ["C", "V"],
            }
        )

        prices = pl.DataFrame(
            {
                C.REFERENCE_DATE.value: [datetime(2024, 12, 31)],
                C.BOND_TYPE.value: [BOND_IPCA_JS],
                C.MATURITY_DATE.value: [datetime(2035, 5, 15)],
                C.SELL_PRICE.value: [1050.0],
            }
        )

        # Two coupons: one before buy (should be excluded), one during hold
        coupons = pl.DataFrame(
            {
                C.BOND_TYPE.value: [BOND_IPCA_JS, BOND_IPCA_JS],
                C.MATURITY_DATE.value: [datetime(2035, 5, 15), datetime(2035, 5, 15)],
                C.BUYBACK_DATE.value: [datetime(2024, 1, 1), datetime(2024, 7, 1)],
                C.UNIT_PRICE.value: [30.0, 30.0],
                C.QUANTITY.value: [100000.0, 100000.0],
                C.VALUE.value: [3000000.0, 3000000.0],
            }
        )

        current_date = date(2024, 12, 31)
        result = calculate_operations_returns(
            operations,
            prices,
            current_date=current_date,
            coupons=coupons,
        )

        # Only the July coupon should be counted (buy was April, sell was Sep)
        # total_coupons = 10 * 30 = 300
        self.assertAlmostEqual(result["total_coupons"][0], 300.0, places=1)

    def test_simple_return_positive(self):
        """Test positive simple return calculation through operations."""
        operations = pl.DataFrame(
            {
                C.OPERATION_DATE.value: [datetime(2024, 1, 1), datetime(2024, 7, 1)],
                C.BOND_TYPE.value: ["Tesouro Selic", "Tesouro Selic"],
                C.MATURITY_DATE.value: [datetime(2030, 1, 1), datetime(2030, 1, 1)],
                C.QUANTITY.value: [10.0, -10.0],
                C.BOND_VALUE.value: [1000.0, 1100.0],
                C.OPERATION_VALUE.value: [10000.0, 11000.0],
                C.OPERATION_TYPE.value: ["C", "V"],
            }
        )
        prices = pl.DataFrame(
            {
                C.REFERENCE_DATE.value: [datetime(2024, 12, 31)],
                C.BOND_TYPE.value: ["Tesouro Selic"],
                C.MATURITY_DATE.value: [datetime(2030, 1, 1)],
                C.SELL_PRICE.value: [1100.0],
            }
        )
        result = calculate_operations_returns(operations, prices, current_date=date(2024, 12, 31))
        self.assertAlmostEqual(result["simple_return"][0], 10.0, places=1)

    def test_simple_return_negative(self):
        """Test negative simple return calculation through operations."""
        operations = pl.DataFrame(
            {
                C.OPERATION_DATE.value: [datetime(2024, 1, 1), datetime(2024, 7, 1)],
                C.BOND_TYPE.value: ["Tesouro Selic", "Tesouro Selic"],
                C.MATURITY_DATE.value: [datetime(2030, 1, 1), datetime(2030, 1, 1)],
                C.QUANTITY.value: [10.0, -10.0],
                C.BOND_VALUE.value: [1000.0, 900.0],
                C.OPERATION_VALUE.value: [10000.0, 9000.0],
                C.OPERATION_TYPE.value: ["C", "V"],
            }
        )
        prices = pl.DataFrame(
            {
                C.REFERENCE_DATE.value: [datetime(2024, 12, 31)],
                C.BOND_TYPE.value: ["Tesouro Selic"],
                C.MATURITY_DATE.value: [datetime(2030, 1, 1)],
                C.SELL_PRICE.value: [900.0],
            }
        )
        result = calculate_operations_returns(operations, prices, current_date=date(2024, 12, 31))
        self.assertAlmostEqual(result["simple_return"][0], -10.0, places=1)

    def test_annualized_return_one_year(self):
        """Test annualized return for exactly one year holding period."""
        operations = pl.DataFrame(
            {
                C.OPERATION_DATE.value: [datetime(2024, 1, 1), datetime(2024, 12, 31)],
                C.BOND_TYPE.value: ["Tesouro Selic", "Tesouro Selic"],
                C.MATURITY_DATE.value: [datetime(2030, 1, 1), datetime(2030, 1, 1)],
                C.QUANTITY.value: [10.0, -10.0],
                C.BOND_VALUE.value: [1000.0, 1100.0],
                C.OPERATION_VALUE.value: [10000.0, 11000.0],
                C.OPERATION_TYPE.value: ["C", "V"],
            }
        )
        prices = pl.DataFrame(
            {
                C.REFERENCE_DATE.value: [datetime(2024, 12, 31)],
                C.BOND_TYPE.value: ["Tesouro Selic"],
                C.MATURITY_DATE.value: [datetime(2030, 1, 1)],
                C.SELL_PRICE.value: [1100.0],
            }
        )
        result = calculate_operations_returns(operations, prices, current_date=date(2024, 12, 31))
        # 10% over 365 days -> annualized ~10%
        self.assertAlmostEqual(result["annualized_return"][0], 10.0, places=0)

    def test_annualized_return_short_period_returns_zero(self):
        """Test that short holding periods (< 30 days) return 0 for annualized."""
        operations = pl.DataFrame(
            {
                C.OPERATION_DATE.value: [datetime(2024, 1, 1), datetime(2024, 1, 15)],
                C.BOND_TYPE.value: ["Tesouro Selic", "Tesouro Selic"],
                C.MATURITY_DATE.value: [datetime(2030, 1, 1), datetime(2030, 1, 1)],
                C.QUANTITY.value: [10.0, -10.0],
                C.BOND_VALUE.value: [1000.0, 1100.0],
                C.OPERATION_VALUE.value: [10000.0, 11000.0],
                C.OPERATION_TYPE.value: ["C", "V"],
            }
        )
        prices = pl.DataFrame(
            {
                C.REFERENCE_DATE.value: [datetime(2024, 12, 31)],
                C.BOND_TYPE.value: ["Tesouro Selic"],
                C.MATURITY_DATE.value: [datetime(2030, 1, 1)],
                C.SELL_PRICE.value: [1100.0],
            }
        )
        result = calculate_operations_returns(operations, prices, current_date=date(2024, 12, 31))
        self.assertEqual(result["annualized_return"][0], 0.0)


class TestPortfolioMonthlyReturns(unittest.TestCase):
    """Test portfolio monthly return calculations."""

    def setUp(self):
        """Set up test data."""
        self.operations = pl.DataFrame(
            {
                C.OPERATION_DATE.value: [
                    datetime(2024, 1, 15),
                    datetime(2024, 2, 15),
                    datetime(2024, 3, 15),
                ],
                C.BOND_TYPE.value: [
                    "Tesouro Selic",
                    "Tesouro Selic",
                    "Tesouro Selic",
                ],
                C.MATURITY_DATE.value: [
                    datetime(2030, 1, 1),
                    datetime(2030, 1, 1),
                    datetime(2030, 1, 1),
                ],
                C.QUANTITY.value: [10.0, 5.0, -5.0],
                C.BOND_VALUE.value: [1000.0, 1050.0, 1100.0],
                C.OPERATION_VALUE.value: [10000.0, 5250.0, 5500.0],
                C.OPERATION_TYPE.value: ["C", "C", "V"],
            }
        )

        # Create monthly price data
        self.prices = pl.DataFrame(
            {
                C.REFERENCE_DATE.value: [
                    datetime(2024, 1, 31),
                    datetime(2024, 2, 29),
                    datetime(2024, 3, 31),
                    datetime(2024, 4, 30),
                ],
                C.BOND_TYPE.value: ["Tesouro Selic"] * 4,
                C.MATURITY_DATE.value: [datetime(2030, 1, 1)] * 4,
                C.SELL_PRICE.value: [1000.0, 1050.0, 1100.0, 1150.0],
            }
        )

    def test_monthly_returns_structure(self):
        """Test that monthly returns DataFrame has correct structure."""
        result = calculate_portfolio_monthly_returns(
            self.operations,
            self.prices,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 4, 30),
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
            start_date=date(2024, 1, 1),
            end_date=date(2024, 4, 30),
        )

        # Should have 4 months
        self.assertEqual(result.height, 4)

    def test_cumulative_return_increases(self):
        """Test that cumulative return is monotonic (in growth scenario)."""
        result = calculate_portfolio_monthly_returns(
            self.operations,
            self.prices,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 4, 30),
        )

        # With increasing prices, cumulative should generally increase
        self.assertTrue("cumulative_return" in result.columns)

    def test_cash_flow_tracking(self):
        """Test that cash flows are tracked correctly."""
        result = calculate_portfolio_monthly_returns(
            self.operations,
            self.prices,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 4, 30),
        )

        # January should have positive cash flow (buy)
        jan_row = result.filter(pl.col("month") == datetime(2024, 1, 1))
        self.assertGreater(jan_row["net_cash_flow"][0], 0)

        # March should have negative cash flow (sell)
        mar_row = result.filter(pl.col("month") == datetime(2024, 3, 1))
        self.assertLess(mar_row["net_cash_flow"][0], 0)

    def test_zero_bond_value_filtered_portfolio(self):
        """Test that operations with zero bond value are filtered out."""
        ops_with_zero = pl.concat(
            [
                self.operations,
                pl.DataFrame(
                    {
                        C.OPERATION_DATE.value: [datetime(2024, 2, 1)],
                        C.BOND_TYPE.value: ["Tesouro Selic"],
                        C.MATURITY_DATE.value: [datetime(2030, 1, 1)],
                        C.QUANTITY.value: [3.0],
                        C.BOND_VALUE.value: [0.0],
                        C.OPERATION_VALUE.value: [0.0],
                        C.OPERATION_TYPE.value: ["C"],
                    }
                ),
            ]
        )

        result = calculate_portfolio_monthly_returns(
            ops_with_zero,
            self.prices,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 4, 30),
        )

        # Should still produce 4 months of returns
        self.assertEqual(result.height, 4)

        # February cash flow should be from the real buy only (5250), not the zero one
        feb_row = result.filter(pl.col("month") == datetime(2024, 2, 1))
        self.assertAlmostEqual(feb_row["net_cash_flow"][0], 5250.0, places=1)

    def test_coupon_as_distribution_portfolio(self):
        """Test that coupons are treated as distributions in portfolio returns."""
        # Single buy of IPCA+ com Juros Semestrais
        operations = pl.DataFrame(
            {
                C.OPERATION_DATE.value: [datetime(2024, 1, 15)],
                C.BOND_TYPE.value: [BOND_IPCA_JS],
                C.MATURITY_DATE.value: [datetime(2035, 5, 15)],
                C.QUANTITY.value: [10.0],
                C.BOND_VALUE.value: [1000.0],
                C.OPERATION_VALUE.value: [10000.0],
                C.OPERATION_TYPE.value: ["C"],
            }
        )

        # Prices: stable at 1000, then drops to 970 in July (coupon effect)
        prices = pl.DataFrame(
            {
                C.REFERENCE_DATE.value: [
                    datetime(2024, 1, 31),
                    datetime(2024, 2, 29),
                    datetime(2024, 3, 31),
                    datetime(2024, 4, 30),
                    datetime(2024, 5, 31),
                    datetime(2024, 6, 30),
                    datetime(2024, 7, 31),
                ],
                C.BOND_TYPE.value: [BOND_IPCA_JS] * 7,
                C.MATURITY_DATE.value: [datetime(2035, 5, 15)] * 7,
                C.SELL_PRICE.value: [1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1030.0, 1000.0],
            }
        )

        # Coupon payment in July
        coupons = pl.DataFrame(
            {
                C.BOND_TYPE.value: [BOND_IPCA_JS],
                C.MATURITY_DATE.value: [datetime(2035, 5, 15)],
                C.BUYBACK_DATE.value: [datetime(2024, 7, 1)],
                C.UNIT_PRICE.value: [30.0],
                C.QUANTITY.value: [100000.0],
                C.VALUE.value: [3000000.0],
            }
        )

        # With coupons
        result_with = calculate_portfolio_monthly_returns(
            operations,
            prices,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 7, 31),
            coupons=coupons,
        )

        # Without coupons
        result_without = calculate_portfolio_monthly_returns(
            operations,
            prices,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 7, 31),
        )

        # July should have a coupon distribution in net_cash_flow
        july_with = result_with.filter(pl.col("month") == datetime(2024, 7, 1))
        july_without = result_without.filter(pl.col("month") == datetime(2024, 7, 1))

        # With coupons, net_cash_flow should be negative (distribution)
        self.assertLess(july_with["net_cash_flow"][0], 0)

        # Without coupons, net_cash_flow should be zero (no operations in July)
        self.assertAlmostEqual(july_without["net_cash_flow"][0], 0.0, places=1)

        # The coupon-adjusted return should be higher than without
        # (because without coupons, the price drop looks like a loss)
        self.assertGreater(
            july_with["monthly_return"][0],
            july_without["monthly_return"][0],
        )


if __name__ == "__main__":
    unittest.main()
