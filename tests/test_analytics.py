import unittest
from datetime import datetime

import polars as pl

from tesouro_direto_fetcher import analytics
from tesouro_direto_fetcher.constants import Column


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

    def test_aggregate_new_investors_unsorted(self):
        # Create unsorted join dates across months and verify aggregation
        data = pl.DataFrame(
            {
                Column.INVESTOR_ID.value: [1, 2, 3],
                Column.JOIN_DATE.value: [
                    datetime(2024, 3, 15),
                    datetime(2024, 1, 10),
                    datetime(2024, 3, 20),
                ],
            }
        )

        res = analytics.aggregate_new_investors(data, freq="1mo")

        # Expect two months: 2024-01 (1 new investor) and 2024-03 (2 new investors)
        self.assertEqual(res.height, 2)
        # The grouped date should be truncated to first of month
        expected_months = [datetime(2024, 1, 1), datetime(2024, 3, 1)]
        self.assertListEqual(res[Column.JOIN_DATE.value].to_list(), expected_months)
        self.assertListEqual(res["new_investors"].to_list(), [1, 2])

    def test_prepare_population_pyramid_ordering(self):
        # Create ages that fall into several 5-year bins and include a null age to verify
        # null groups are removed and ordering is descending (older groups first)
        data = pl.DataFrame(
            {
                Column.AGE.value: [1, 6, 11, 16, None],
                Column.GENDER.value: ["F", "M", "F", "M", "F"],
            }
        )

        pivoted = analytics.prepare_population_pyramid(data)
        age_groups = pivoted["age_group"].to_list()

        def _lower(label: str) -> int:
            try:
                return int(label.split("-")[0])
            except Exception:
                return 10**9

        # Ensure no null age group present
        self.assertTrue(all((ag is not None and str(ag).lower() != "null") for ag in age_groups))
        # Expect descending order by numeric lower bound (oldest first)
        self.assertListEqual(age_groups, sorted(age_groups, key=_lower, reverse=True))

    def test_aggregate_value_over_time_semiannual(self):
        data = pl.DataFrame(
            {
                Column.BUYBACK_DATE.value: [
                    datetime(2024, 1, 10),
                    datetime(2024, 3, 15),
                    datetime(2024, 7, 1),
                ],
                Column.VALUE.value: [100, 200, 300],
            }
        )

        res = analytics.aggregate_value_over_time(data, Column.BUYBACK_DATE.value, Column.VALUE.value, freq="6mo")

        # Expect two periods: 2024-01-01 (100+200=300), 2024-07-01 (300)
        self.assertEqual(res.height, 2)
        self.assertListEqual(res["month"].to_list(), [datetime(2024, 1, 1), datetime(2024, 7, 1)])
        self.assertListEqual(res[Column.VALUE.value].to_list(), [300, 300])


if __name__ == "__main__":
    unittest.main()
