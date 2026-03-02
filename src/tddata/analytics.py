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


from datetime import date, datetime, timedelta
from typing import Optional

import polars as pl

from .constants import (
    AccountStatus,
    Gender,
    OperationType,
    TradedLast12Months,
)
from .constants import Column as C


def aggregate_stock(data: pl.DataFrame, by_bond_type: bool = True) -> pl.DataFrame:
    """Aggregate stock value by month and optionally bond type."""
    if by_bond_type:
        return (
            data.group_by([C.STOCK_MONTH.value, C.BOND_TYPE.value])
            .agg(pl.col(C.STOCK_VALUE.value).sum())
            .sort([C.STOCK_MONTH.value, C.BOND_TYPE.value])
        )
    return data.group_by(C.STOCK_MONTH.value).agg(pl.col(C.STOCK_VALUE.value).sum()).sort(C.STOCK_MONTH.value)


def prepare_prices(data: pl.DataFrame, bond_type: str) -> pl.DataFrame:
    """Filter and sort prices data for plotting."""
    return data.filter(
        (pl.col(C.BOND_TYPE.value) == bond_type) & (pl.col(C.BUY_PRICE.value) > 0) & (pl.col(C.SELL_PRICE.value) > 0)
    ).sort([C.MATURITY_DATE.value, C.REFERENCE_DATE.value])


def prepare_demographics_counts(data: pl.DataFrame, column: str, top_n: int = 15) -> pl.DataFrame:
    """Get value counts for demographics data with human readable labels.

    Returns a DataFrame with columns: [column_name, count] sorted by count descending.
    """
    df = data.clone()

    # Deduplicate by investor ID to avoid counting same investor multiple times
    # (investors can have multiple records if registered with multiple institutions)
    if C.INVESTOR_ID.value in df.columns:
        df = df.unique(subset=[C.INVESTOR_ID.value], keep="first")

    # Map enum codes to human-readable labels
    if column == C.GENDER.value:
        df = df.with_columns(pl.col(column).replace(Gender.get_labels()))
    elif column == C.ACCOUNT_STATUS.value:
        df = df.with_columns(pl.col(column).replace(AccountStatus.get_labels()))
    elif column == C.TRADED_LAST_12_MONTHS.value:
        df = df.with_columns(pl.col(column).replace(TradedLast12Months.get_labels()))

    counts = df.group_by(column).len(name="count")

    if column == C.AGE.value:
        return counts.sort(column)
    return counts.sort("count", descending=True).head(top_n)


def prepare_population_pyramid(data: pl.DataFrame) -> pl.DataFrame:
    """Prepare data for population pyramid (age bins x gender)."""
    df = data.clone()

    # Deduplicate by investor ID to avoid counting same investor multiple times
    # (investors can have multiple record if registered with multiple institutions)
    if C.INVESTOR_ID.value in df.columns:
        df = df.unique(subset=[C.INVESTOR_ID.value], keep="first")

    df = df.select([C.AGE.value, C.GENDER.value])

    # Map gender codes to labels
    df = df.with_columns(pl.col(C.GENDER.value).replace(Gender.get_labels()))

    # Create age bins (5-year intervals)
    if df.filter(pl.col(C.AGE.value).is_not_null()).height == 0:
        return pl.DataFrame()

    max_age = int(df[C.AGE.value].max())
    min_age = int(df[C.AGE.value].min())
    bins = list(range(min_age - (min_age % 5), max_age + 5, 5))
    labels = [f"{i}-{i + 4}" for i in bins[:-1]]

    # Create age groups using cut
    # Polars doesn't have cut, so we'll do it manually with when/then
    age_group_expr = pl.lit(None)
    for i, (start, end) in enumerate(zip(bins[:-1], bins[1:])):
        age_group_expr = (
            pl.when((pl.col(C.AGE.value) >= start) & (pl.col(C.AGE.value) < end))
            .then(pl.lit(labels[i]))
            .otherwise(age_group_expr)
        )

    df = df.with_columns(age_group_expr.alias("age_group"))

    # Count by age group and gender
    grouped = df.group_by(["age_group", C.GENDER.value]).len(name="count")

    # Pivot to get male and female columns
    pivoted = grouped.pivot(
        index="age_group",
        on=C.GENDER.value,
        values="count",
    ).fill_null(0)

    # Ensure age groups are sorted by numeric lower bound (eg '0-4', '5-9', ...)
    # Create an ordering map from age_group label to its lower bound
    def _lower_bound(label: str) -> int:
        try:
            return int(label.split("-")[0])
        except Exception:
            # Place malformed or null labels at the end
            return 10**9

    # Remove null age groups and compute ordering from numeric lower bound
    pivoted = pivoted.filter(pl.col("age_group").is_not_null())
    order_map = {row["age_group"]: _lower_bound(row["age_group"]) for row in pivoted.to_dicts()}

    pivoted = (
        pivoted.with_columns(
            pl.col("age_group")
            .map_elements(lambda x: order_map.get(x, 10**9), return_dtype=pl.Int64)
            .alias("_age_order")
        )
        .sort("_age_order", descending=True)
        .drop("_age_order")
    )

    return pivoted


def aggregate_new_investors(data: pl.DataFrame, freq: str = "1mo") -> pl.DataFrame:
    """Resample new investors data by frequency.

    Args:
        data: DataFrame with join_date column
        freq: Frequency string for grouping. Use '1mo' for monthly, '1w' for weekly, etc.
    """
    df = data.clone()

    # Deduplicate by investor ID to avoid counting same investor multiple times
    # (investors can have multiple records if registered with multiple institutions)
    if C.INVESTOR_ID.value in df.columns:
        df = df.unique(subset=[C.INVESTOR_ID.value], keep="first")

    # Polars requires the grouping column to be sorted for group_by_dynamic
    if C.JOIN_DATE.value in df.columns:
        df = df.sort(C.JOIN_DATE.value)

    return (
        df.group_by_dynamic(C.JOIN_DATE.value, every=freq).agg(pl.len().alias("new_investors")).sort(C.JOIN_DATE.value)
    )


def aggregate_operations(data: pl.DataFrame, by_type: bool = True) -> pl.DataFrame:
    """Aggregate operations by month and optionally type."""
    df = data.with_columns(pl.col(C.OPERATION_DATE.value).dt.truncate("1mo").alias("month"))

    if by_type:
        df = df.with_columns(pl.col(C.OPERATION_TYPE.value).replace(OperationType.get_labels()))
        return (
            df.group_by(["month", C.OPERATION_TYPE.value])
            .agg(pl.col(C.OPERATION_VALUE.value).sum())
            .sort(["month", C.OPERATION_TYPE.value])
        )

    return df.group_by("month").agg(pl.col(C.OPERATION_VALUE.value).sum()).sort("month")


def aggregate_value_over_time(
    data: pl.DataFrame, date_col: str, value_col: str, group_col: str | None = None, freq: str = "1mo"
) -> pl.DataFrame:
    """Generic aggregation of value over time.

    Args:
        data: DataFrame containing the date and value columns
        date_col: Name of the date column
        value_col: Name of the value column to aggregate
        group_col: Optional column to group by alongside the time period
        freq: Frequency string for grouping (e.g., '1mo' for monthly, '6mo' for semiannual)
    """
    df = data.clone()

    # Monthly truncation (default, simple path)
    if freq == "1mo":
        df = df.with_columns(pl.col(date_col).dt.truncate("1mo").alias("month"))
        if group_col:
            return df.group_by(["month", group_col]).agg(pl.col(value_col).sum()).sort(["month", group_col])
        return df.group_by("month").agg(pl.col(value_col).sum()).sort("month")

    # For other frequencies (e.g., '6mo'), use group_by_dynamic which requires sorted input
    # Ensure the date column is sorted
    if date_col in df.columns:
        df = df.sort(date_col)

    if group_col:
        # Use the new `group_by` argument name (replaces deprecated `by`)
        res = df.group_by_dynamic(date_col, every=freq, group_by=group_col).agg(pl.col(value_col).sum())
        # Rename the grouping column to 'month' for consistency
        if date_col in res.columns:
            res = res.rename({date_col: "month"})
        return res.sort(["month", group_col])

    res = df.group_by_dynamic(date_col, every=freq).agg(pl.col(value_col).sum())
    if date_col in res.columns:
        res = res.rename({date_col: "month"})
    return res.sort("month")


# ============================================================================
# Return Calculations (Pure Polars)
# ============================================================================


def _generate_monthly_dates(start: date, end: date) -> list[date]:
    """Generate a list of first-of-month dates between start and end (inclusive)."""
    # Normalize to first of month
    current = start.replace(day=1)
    end_month = end.replace(day=1)
    months = []
    while current <= end_month:
        months.append(current)
        # Advance to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months


def _last_day_of_month(d: date) -> date:
    """Return the last day of the month for a given date."""
    if d.month == 12:
        return d.replace(day=31)
    return d.replace(month=d.month + 1, day=1) - timedelta(days=1)


def calculate_operations_returns(
    operations: pl.DataFrame,
    prices: pl.DataFrame,
    current_date: Optional[date] = None,
    coupons: Optional[pl.DataFrame] = None,
) -> pl.DataFrame:
    """Calculate returns for each buy operation with FIFO matching for sells.

    Handles partial sells by splitting lots into closed and open positions.
    Returns a DataFrame with one row per lot (closed or open).
    """
    if operations.height == 0:
        return pl.DataFrame()

    # Filter out operations with zero bond value
    if C.BOND_VALUE.value in operations.columns:
        operations = operations.filter(pl.col(C.BOND_VALUE.value) != 0)

    if operations.height == 0:
        return pl.DataFrame()

    if current_date is None:
        current_date = date.today()
    current_date_dt = datetime(current_date.year, current_date.month, current_date.day)

    # Separate buys and sells
    buy_records = operations.filter(pl.col(C.OPERATION_TYPE.value) == OperationType.BUY.value).to_dicts()
    sell_records = operations.filter(pl.col(C.OPERATION_TYPE.value) == OperationType.SELL.value).to_dicts()

    if not buy_records:
        return pl.DataFrame()

    # Build price lookup dict: (bond_type, maturity_date) -> latest_sell_price
    price_lookup = {}
    if prices.height > 0:
        latest_prices = (
            prices.filter(pl.col(C.REFERENCE_DATE.value) <= current_date_dt)
            .sort(C.REFERENCE_DATE.value)
            .group_by([C.BOND_TYPE.value, C.MATURITY_DATE.value])
            .last()
        )

        for row in latest_prices.iter_rows(named=True):
            mat = row[C.MATURITY_DATE.value]
            # Normalize maturity_date to date for consistent key matching
            if isinstance(mat, datetime):
                mat_key = mat.date()
            else:
                mat_key = mat
            price_lookup[(row[C.BOND_TYPE.value], mat_key)] = row[C.SELL_PRICE.value]

    # Initialize remaining quantity tracking and maturity key for all buys
    for rec in buy_records:
        rec["_remaining_qty"] = float(rec.get(C.QUANTITY.value) or 0.0)
        mat = rec.get(C.MATURITY_DATE.value)
        if isinstance(mat, datetime):
            rec["_maturity_date_key"] = mat.date()
        else:
            rec["_maturity_date_key"] = mat

    # Build FIFO index: (bond_type, maturity_date) -> [buy_record_indices sorted by date]
    buy_index = {}
    for idx, rec in enumerate(buy_records):
        key = (rec[C.BOND_TYPE.value], rec["_maturity_date_key"])
        buy_index.setdefault(key, []).append(idx)

    # Sort each FIFO queue by operation date
    for key in buy_index:
        buy_index[key].sort(key=lambda i: buy_records[i][C.OPERATION_DATE.value])

    # Process sells using quantity-aware FIFO matching
    closed_lots = []
    for sell_rec in sell_records:
        mat = sell_rec[C.MATURITY_DATE.value]
        if isinstance(mat, datetime):
            mat_key = mat.date()
        else:
            mat_key = mat
        sell_key = (sell_rec[C.BOND_TYPE.value], mat_key)

        sell_date = sell_rec[C.OPERATION_DATE.value]
        if isinstance(sell_date, date) and not isinstance(sell_date, datetime):
            sell_date = datetime(sell_date.year, sell_date.month, sell_date.day)

        sell_qty = abs(float(sell_rec.get(C.QUANTITY.value) or 0.0))
        if sell_qty <= 0.0:
            continue

        sell_value_total = abs(float(sell_rec.get(C.OPERATION_VALUE.value) or 0.0))
        unit_sell_price = sell_value_total / sell_qty if sell_qty > 0 else 0.0

        remaining = sell_qty
        for idx in buy_index.get(sell_key, []):
            if remaining <= 0:
                break
            buy_rec = buy_records[idx]
            avail = buy_rec.get("_remaining_qty", 0.0)
            if avail <= 0.0:
                continue

            # Match quantity (FIFO)
            match_qty = min(avail, remaining)
            sell_value_portion = unit_sell_price * match_qty

            # Create closed lot record
            buy_date = buy_rec[C.OPERATION_DATE.value]
            if isinstance(buy_date, date) and not isinstance(buy_date, datetime):
                buy_date = datetime(buy_date.year, buy_date.month, buy_date.day)

            buy_qty_original = float(buy_rec.get(C.QUANTITY.value) or 0.0)
            buy_value_original = float(buy_rec.get(C.OPERATION_VALUE.value) or 0.0)
            unit_buy_price = buy_value_original / buy_qty_original if buy_qty_original > 0 else 0.0

            closed = {
                C.INVESTOR_ID.value: buy_rec.get(C.INVESTOR_ID.value),
                C.BOND_TYPE.value: buy_rec[C.BOND_TYPE.value],
                C.MATURITY_DATE.value: buy_rec[C.MATURITY_DATE.value],
                C.OPERATION_DATE.value: buy_rec[C.OPERATION_DATE.value],
                C.QUANTITY.value: match_qty,
                C.OPERATION_VALUE.value: unit_buy_price * match_qty,
                "sell_date": sell_rec[C.OPERATION_DATE.value],
                "sell_value": sell_value_portion,
                "holding_days": (sell_date - buy_date).days,
                "status": "closed",
                "total_coupons": 0.0,
                "_maturity_date_key": buy_rec["_maturity_date_key"],
            }
            closed_lots.append(closed)

            # Update remaining quantities
            buy_rec["_remaining_qty"] = avail - match_qty
            remaining -= match_qty

    # Build open lots from remaining quantities
    open_lots = []
    for rec in buy_records:
        rem = rec.get("_remaining_qty", 0.0)
        if rem > 0.0:
            mat_key = rec.get("_maturity_date_key")
            price = price_lookup.get((rec[C.BOND_TYPE.value], mat_key))
            current_value = rem * price if price is not None else 0.0

            buy_qty_original = float(rec.get(C.QUANTITY.value) or 0.0)
            buy_value_original = float(rec.get(C.OPERATION_VALUE.value) or 0.0)
            unit_buy_price = buy_value_original / buy_qty_original if buy_qty_original > 0 else 0.0

            buy_date = rec[C.OPERATION_DATE.value]
            if isinstance(buy_date, date) and not isinstance(buy_date, datetime):
                buy_date = datetime(buy_date.year, buy_date.month, buy_date.day)

            open_rec = {
                C.INVESTOR_ID.value: rec.get(C.INVESTOR_ID.value),
                C.BOND_TYPE.value: rec[C.BOND_TYPE.value],
                C.MATURITY_DATE.value: rec[C.MATURITY_DATE.value],
                C.OPERATION_DATE.value: rec[C.OPERATION_DATE.value],
                C.QUANTITY.value: rem,
                C.OPERATION_VALUE.value: unit_buy_price * rem,
                "current_value": current_value,
                "status": "open",
                "sell_date": None,
                "sell_value": 0.0,
                "holding_days": (current_date_dt - buy_date).days,
                "total_coupons": 0.0,
                "_maturity_date_key": rec.get("_maturity_date_key"),
            }
            open_lots.append(open_rec)

    # Combine all lots for coupon allocation
    all_lots = closed_lots + open_lots

    # Calculate coupon income per lot
    if coupons is not None and coupons.height > 0:
        for lot in all_lots:
            bond_coupons = coupons.filter(
                (pl.col(C.BOND_TYPE.value) == lot[C.BOND_TYPE.value])
                & (pl.col(C.MATURITY_DATE.value) == lot.get("_maturity_date_key", lot[C.MATURITY_DATE.value]))
            )
            if bond_coupons.height == 0:
                continue

            buy_date = lot[C.OPERATION_DATE.value]
            if lot.get("status") == "closed" and lot.get("sell_date") is not None:
                end_dt = lot["sell_date"]
            else:
                end_dt = current_date_dt

            period_coupons = bond_coupons.filter(
                (pl.col(C.BUYBACK_DATE.value) >= buy_date) & (pl.col(C.BUYBACK_DATE.value) <= end_dt)
            )
            if period_coupons.height > 0:
                total_coupon_per_unit = period_coupons[C.UNIT_PRICE.value].sum()
                lot["total_coupons"] = lot[C.QUANTITY.value] * total_coupon_per_unit

    # Calculate returns per lot
    final_records = []
    for rec in all_lots:
        if rec["status"] == "closed":
            endv = rec.get("sell_value", 0.0) + rec.get("total_coupons", 0.0)
        else:
            endv = rec.get("current_value", 0.0) + rec.get("total_coupons", 0.0)

        rec["end_value"] = endv
        initial = rec.get(C.OPERATION_VALUE.value, 0.0)
        rec["simple_return"] = ((endv / initial) - 1) * 100 if initial >= 0.01 and endv > 0 else 0.0

        holding = rec.get("holding_days", 0)
        if holding >= 30 and initial >= 0.01 and endv > 0:
            value_ratio = endv / initial
            if value_ratio > 0:
                try:
                    exponent = 365.0 / holding
                    ann = ((value_ratio**exponent) - 1) * 100
                    rec["annualized_return"] = max(-100.0, min(1000.0, ann))
                except (ValueError, OverflowError):
                    rec["annualized_return"] = 0.0
            else:
                rec["annualized_return"] = 0.0
        else:
            rec["annualized_return"] = 0.0

        final_records.append(rec)

    if not final_records:
        return pl.DataFrame()

    return pl.DataFrame(final_records)


def calculate_portfolio_monthly_returns(
    operations: pl.DataFrame,
    prices: pl.DataFrame,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    coupons: Optional[pl.DataFrame] = None,
    price_lookup: Optional[dict] = None,
    coupon_lookup: Optional[dict] = None,
) -> pl.DataFrame:
    """Calculate monthly portfolio returns using Modified Dietz method.

    Returns DataFrame with columns: month, monthly_return, cumulative_return,
    portfolio_value, net_cash_flow.

    Args:
        operations: Operations DataFrame
        prices: Prices DataFrame
        start_date: Optional start date for calculation period
        end_date: Optional end date for calculation period
        coupons: Optional coupons DataFrame
        price_lookup: Optional pre-built price lookup dict for performance
        coupon_lookup: Optional pre-built coupon lookup dict for performance
    """
    if operations.height == 0 or prices.height == 0:
        return pl.DataFrame()

    # Determine date range from operations if not provided
    op_dates = operations[C.OPERATION_DATE.value]
    if start_date is None:
        min_date = op_dates.min()
        if isinstance(min_date, datetime):
            start_date = min_date.date()
        else:
            start_date = min_date
    if end_date is None:
        max_date = op_dates.max()
        if isinstance(max_date, datetime):
            end_date = max_date.date()
        else:
            end_date = max_date

    if start_date > end_date:
        return pl.DataFrame()

    # Build efficient price lookup if not provided
    if price_lookup is None:
        # Use optimized nested dict structure: {bond_type: {maturity_date: {ref_date: price}}}
        price_lookup = {}
        for row in prices.iter_rows(named=True):
            bond_type = row[C.BOND_TYPE.value]
            mat = row[C.MATURITY_DATE.value]
            mat_key = mat.date() if isinstance(mat, datetime) else mat
            ref = row[C.REFERENCE_DATE.value]
            ref_key = ref.date() if isinstance(ref, datetime) else ref
            price = row[C.SELL_PRICE.value]

            if bond_type not in price_lookup:
                price_lookup[bond_type] = {}
            if mat_key not in price_lookup[bond_type]:
                price_lookup[bond_type][mat_key] = {}
            price_lookup[bond_type][mat_key][ref_key] = price

    def _get_latest_price_fast(bond_type: str, maturity_date: date, ref_date: date) -> Optional[float]:
        """Fast price lookup using nested dict structure."""
        if bond_type not in price_lookup:
            return None
        if maturity_date not in price_lookup[bond_type]:
            return None

        # Try exact match first (most common case)
        mat_dict = price_lookup[bond_type][maturity_date]
        if ref_date in mat_dict:
            return mat_dict[ref_date]

        # Fall back to latest price before ref_date
        candidates = {d: p for d, p in mat_dict.items() if d <= ref_date}
        if candidates:
            latest_date = max(candidates.keys())
            return candidates[latest_date]
        return None

    # Generate monthly periods
    months = _generate_monthly_dates(start_date, end_date)
    if not months:
        return pl.DataFrame()

    # Track positions: (bond_type, maturity_date) -> {quantity, avg_cost}
    positions = {}
    monthly_results = []

    for month_start in months:
        month_end = _last_day_of_month(month_start)
        month_end_dt = datetime(month_end.year, month_end.month, month_end.day, 23, 59, 59)

        # Get operations in this month
        month_ops = operations.filter(
            (pl.col(C.OPERATION_DATE.value) >= datetime(month_start.year, month_start.month, month_start.day))
            & (pl.col(C.OPERATION_DATE.value) <= month_end_dt)
        )

        # Calculate BMV (Beginning Market Value) using month_start prices
        bmv = 0.0
        if positions:
            for (bond_type, maturity_date), pos in positions.items():
                price = _get_latest_price_fast(bond_type, maturity_date, month_start)
                if price is not None:
                    bmv += pos["quantity"] * price

        # Process operations
        net_cash_flow = 0.0
        for op in month_ops.iter_rows(named=True):
            op_type = op[C.OPERATION_TYPE.value]
            bond_type = op[C.BOND_TYPE.value]
            mat = op[C.MATURITY_DATE.value]
            if isinstance(mat, datetime):
                mat = mat.date()
            qty = float(op.get(C.QUANTITY.value) or 0.0)
            value = float(op.get(C.OPERATION_VALUE.value) or 0.0)

            key = (bond_type, mat)

            if op_type == OperationType.BUY.value:
                net_cash_flow += value
                if key not in positions:
                    positions[key] = {"quantity": 0.0, "avg_cost": 0.0}
                old_qty = positions[key]["quantity"]
                old_cost = positions[key]["avg_cost"]
                new_qty = old_qty + qty
                positions[key]["avg_cost"] = ((old_qty * old_cost) + value) / new_qty if new_qty > 0.0 else 0.0
                positions[key]["quantity"] = new_qty

            elif op_type == OperationType.SELL.value:
                net_cash_flow -= value
                if key in positions:
                    positions[key]["quantity"] -= abs(qty)
                    if positions[key]["quantity"] <= 0:
                        del positions[key]

        # Add coupon income for the month (using coupon_lookup if available)
        coupon_income = 0.0
        if coupons is not None and coupons.height > 0:
            if coupon_lookup is None:
                # Build lookup on demand
                month_coupons = coupons.filter(
                    (pl.col(C.BUYBACK_DATE.value) >= datetime(month_start.year, month_start.month, month_start.day))
                    & (pl.col(C.BUYBACK_DATE.value) <= month_end_dt)
                )
                for cpn in month_coupons.iter_rows(named=True):
                    bond_type = cpn[C.BOND_TYPE.value]
                    mat = cpn[C.MATURITY_DATE.value]
                    if isinstance(mat, datetime):
                        mat = mat.date()
                    key = (bond_type, mat)
                    if key in positions:
                        unit_cpn = float(cpn.get(C.UNIT_PRICE.value) or 0.0)
                        coupon_income += positions[key]["quantity"] * unit_cpn
            else:
                # Use pre-built coupon lookup
                for (bond_type, maturity_date), position_qty in [(k[0], k[1]) for k in positions.keys()]:
                    key = (bond_type, maturity_date)
                    if key in coupon_lookup:
                        for coupon_date, unit_price in coupon_lookup[key]:
                            if (
                                datetime(month_start.year, month_start.month, month_start.day)
                                <= coupon_date
                                <= month_end_dt
                            ):
                                coupon_income += positions.get(key, {}).get("quantity", 0.0) * unit_price

        net_cash_flow -= coupon_income

        # Calculate EMV (Ending Market Value) using month_end prices
        emv = 0.0
        if positions:
            for (bond_type, maturity_date), pos in positions.items():
                price = _get_latest_price_fast(bond_type, maturity_date, month_end)
                if price is not None:
                    emv += pos["quantity"] * price

        # Modified Dietz monthly return
        denominator = bmv + (net_cash_flow / 2.0)
        if denominator > 0.01:
            monthly_return = ((emv - bmv - net_cash_flow) / denominator) * 100
        else:
            monthly_return = 0.0

        monthly_results.append(
            {
                "month": month_start,
                "monthly_return": monthly_return,
                "portfolio_value": emv,
                "net_cash_flow": net_cash_flow,
            }
        )

    if not monthly_results:
        return pl.DataFrame()

    df = pl.DataFrame(monthly_results)

    # Calculate cumulative returns
    cumulative = 1.0
    cum_returns = []
    for ret in df["monthly_return"].to_list():
        cumulative *= 1 + ret / 100
        cum_returns.append((cumulative - 1) * 100)

    df = df.with_columns(pl.Series("cumulative_return", cum_returns))

    return df


def _generate_monthly_dates(start: date, end: date) -> list[date]:
    """Generate list of first day of each month between start and end dates."""
    if start > end:
        return []
    months = []
    current = date(start.year, start.month, 1)
    end_month = date(end.year, end.month, 1)
    while current <= end_month:
        months.append(current)
        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


def _last_day_of_month(d: date) -> date:
    """Return the last day of the month for a given date."""
    if d.month == 12:
        next_month = date(d.year + 1, 1, 1)
    else:
        next_month = date(d.year, d.month + 1, 1)
    return next_month - timedelta(days=1)
