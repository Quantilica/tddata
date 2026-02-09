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
    data: pl.DataFrame, date_col: str, value_col: str, group_col: str | None = None
) -> pl.DataFrame:
    """Generic aggregation of value over time (monthly)."""
    df = data.with_columns(pl.col(date_col).dt.truncate("1mo").alias("month"))

    if group_col:
        return df.group_by(["month", group_col]).agg(pl.col(value_col).sum()).sort(["month", group_col])
    return df.group_by("month").agg(pl.col(value_col).sum()).sort("month")


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
    """Calculate returns for individual operations (buy/sell pairs).

    This function matches buy operations with their corresponding sell operations
    and calculates returns. For open positions, it uses current prices.
    Supports semiannual coupon payments for bonds with "Juros Semestrais".

    Args:
        operations: Polars DataFrame with columns: operation_date, bond_type, maturity_date,
            quantity, bond_value, operation_value, operation_type.
        prices: Polars DataFrame with columns: reference_date, bond_type, maturity_date,
            sell_price.
        current_date: Date to calculate returns as of (defaults to today).
            Accepts datetime.date or datetime.datetime.
        coupons: Polars DataFrame with coupon payment data (from read_interest_coupons).
            Expected columns: bond_type, maturity_date, buyback_date, unit_price.
            If provided, coupon income is included in return calculations.

    Returns:
        Polars DataFrame with buy operations and calculated returns.

    Example:
        >>> ops = pl.DataFrame({
        ...     "operation_date": [datetime(2024, 1, 1), datetime(2024, 7, 1)],
        ...     "bond_type": ["Tesouro Selic", "Tesouro Selic"],
        ...     "maturity_date": [datetime(2030, 1, 1), datetime(2030, 1, 1)],
        ...     "quantity": [10, -10],
        ...     "bond_value": [10000, 11000],
        ...     "operation_value": [10000, 11000],
        ...     "operation_type": ["C", "V"],
        ... })
        >>> prices_df = pl.DataFrame({
        ...     "reference_date": [datetime(2024, 6, 1)],
        ...     "bond_type": ["Tesouro Selic"],
        ...     "maturity_date": [datetime(2030, 1, 1)],
        ...     "sell_price": [10500],
        ... })
        >>> returns = calculate_operations_returns(ops, prices_df)
    """
    if current_date is None:
        current_date = date.today()
    elif isinstance(current_date, datetime):
        current_date = current_date.date()

    # Filter out rows with zero bond value
    df = operations.filter(pl.col(C.BOND_VALUE.value) > 0)

    # Separate buys and sells
    buys = df.filter(pl.col(C.OPERATION_TYPE.value).is_in(["C", "D", "buy"])).sort(C.OPERATION_DATE.value)
    sells = df.filter(~pl.col(C.OPERATION_TYPE.value).is_in(["C", "D", "buy"])).sort(C.OPERATION_DATE.value)

    if buys.height == 0:
        return pl.DataFrame()

    # Convert to list of dicts for FIFO matching (row-level mutation needed)
    buy_records = buys.to_dicts()
    sell_records = sells.to_dicts()

    current_date_dt = datetime(current_date.year, current_date.month, current_date.day)

    # Initialize computed fields
    for rec in buy_records:
        op_date = rec[C.OPERATION_DATE.value]
        if isinstance(op_date, date) and not isinstance(op_date, datetime):
            op_date = datetime(op_date.year, op_date.month, op_date.day)
        rec["holding_days"] = (current_date_dt - op_date).days
        rec["status"] = "open"
        rec["sell_date"] = None
        rec["sell_value"] = 0.0
        rec["current_value"] = 0.0

    # Match sells to buys (simplified FIFO)
    # Group buys by (bond_type, maturity_date)
    from collections import defaultdict

    buy_index = defaultdict(list)
    for i, rec in enumerate(buy_records):
        key = (rec[C.BOND_TYPE.value], rec[C.MATURITY_DATE.value])
        buy_index[key].append(i)

    for sell_rec in sell_records:
        sell_key = (sell_rec[C.BOND_TYPE.value], sell_rec[C.MATURITY_DATE.value])
        if sell_key not in buy_index:
            continue

        sell_date = sell_rec[C.OPERATION_DATE.value]
        if isinstance(sell_date, date) and not isinstance(sell_date, datetime):
            sell_date = datetime(sell_date.year, sell_date.month, sell_date.day)

        # Find first open buy before this sell
        for idx in buy_index[sell_key]:
            buy_rec = buy_records[idx]
            if buy_rec["status"] != "open":
                continue
            buy_date = buy_rec[C.OPERATION_DATE.value]
            if isinstance(buy_date, date) and not isinstance(buy_date, datetime):
                buy_date = datetime(buy_date.year, buy_date.month, buy_date.day)
            if buy_date <= sell_date:
                buy_rec["status"] = "closed"
                buy_rec["sell_date"] = sell_rec[C.OPERATION_DATE.value]
                buy_rec["sell_value"] = abs(sell_rec[C.OPERATION_VALUE.value])
                buy_rec["holding_days"] = (sell_date - buy_date).days
                break

    # Get current prices for open positions
    if prices.height > 0:
        # Get current month start for matching
        current_month_start = datetime(current_date.year, current_date.month, 1)

        # Get latest price per bond type/maturity up to current date
        latest_prices = (
            prices.filter(pl.col(C.REFERENCE_DATE.value) <= current_date_dt)
            .sort(C.REFERENCE_DATE.value)
            .group_by([C.BOND_TYPE.value, C.MATURITY_DATE.value])
            .last()
        )

        # Build a price lookup dict
        price_lookup = {}
        for row in latest_prices.iter_rows(named=True):
            price_lookup[(row[C.BOND_TYPE.value], row[C.MATURITY_DATE.value])] = row[C.SELL_PRICE.value]

        for rec in buy_records:
            if rec["status"] == "open":
                key = (rec[C.BOND_TYPE.value], rec[C.MATURITY_DATE.value])
                price = price_lookup.get(key)
                if price is not None:
                    rec["current_value"] = rec[C.QUANTITY.value] * price

    # Calculate coupon income per lot
    for rec in buy_records:
        rec["total_coupons"] = 0.0

    if coupons is not None and coupons.height > 0:
        for rec in buy_records:
            bond_coupons = coupons.filter(
                (pl.col(C.BOND_TYPE.value) == rec[C.BOND_TYPE.value])
                & (pl.col(C.MATURITY_DATE.value) == rec[C.MATURITY_DATE.value])
            )
            if bond_coupons.height == 0:
                continue

            buy_date = rec[C.OPERATION_DATE.value]
            if rec["status"] == "closed" and rec["sell_date"] is not None:
                end_dt = rec["sell_date"]
            else:
                end_dt = current_date_dt

            period_coupons = bond_coupons.filter(
                (pl.col(C.BUYBACK_DATE.value) >= buy_date) & (pl.col(C.BUYBACK_DATE.value) <= end_dt)
            )
            if period_coupons.height > 0:
                total_coupon_per_unit = period_coupons[C.UNIT_PRICE.value].sum()
                rec["total_coupons"] = rec[C.QUANTITY.value] * total_coupon_per_unit

    # Calculate returns
    for rec in buy_records:
        if rec["status"] == "closed":
            rec["end_value"] = rec["sell_value"] + rec["total_coupons"]
        else:
            rec["end_value"] = rec["current_value"] + rec["total_coupons"]

        # Simple return
        initial = rec[C.OPERATION_VALUE.value]
        end_val = rec["end_value"]
        if initial >= 0.01 and end_val > 0:
            rec["simple_return"] = ((end_val / initial) - 1) * 100
        else:
            rec["simple_return"] = 0.0

        # Annualized return
        holding = rec["holding_days"]
        if holding >= 30 and initial >= 0.01 and end_val > 0:
            value_ratio = end_val / initial
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

    if not buy_records:
        return pl.DataFrame()

    return pl.DataFrame(buy_records)


def calculate_portfolio_monthly_returns(
    operations: pl.DataFrame,
    prices: pl.DataFrame,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    coupons: Optional[pl.DataFrame] = None,
) -> pl.DataFrame:
    """Calculate monthly portfolio returns using Modified Dietz method.

    The Modified Dietz method properly accounts for cash flows by time-weighting
    them based on when they occur during the period.
    Supports semiannual coupon payments for bonds with "Juros Semestrais".
    Coupons are treated as distributions (negative cash flows).

    Args:
        operations: Polars DataFrame with operation_date, bond_type, maturity_date,
            quantity, bond_value, operation_value, operation_type columns.
        prices: Polars DataFrame with reference_date, bond_type, maturity_date,
            sell_price columns.
        start_date: Start date for calculations (defaults to first operation).
            Accepts datetime.date or datetime.datetime.
        end_date: End date (defaults to today).
            Accepts datetime.date or datetime.datetime.
        coupons: Polars DataFrame with coupon payment data (from read_interest_coupons).
            Expected columns: bond_type, maturity_date, buyback_date, unit_price.
            If provided, coupons are treated as distributions in the Modified
            Dietz formula.

    Returns:
        Polars DataFrame with monthly returns and cumulative returns.

    Example:
        >>> # See calculate_operations_returns for data structure
        >>> monthly_returns = calculate_portfolio_monthly_returns(operations, prices)
    """
    if operations.height == 0:
        return pl.DataFrame()

    # Filter out rows with zero bond value
    ops = operations.filter(pl.col(C.BOND_VALUE.value) > 0)

    if ops.height == 0:
        return pl.DataFrame()

    if start_date is None:
        start_date = ops[C.OPERATION_DATE.value].min()
    if isinstance(start_date, datetime):
        start_date = start_date.date()

    if end_date is None:
        end_date = date.today()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()

    # Generate monthly date range
    months = _generate_monthly_dates(start_date, end_date)

    # Convert ops and prices to list of dicts for iteration
    ops_records = ops.to_dicts()
    prices_records = prices.to_dicts() if prices.height > 0 else []

    results = []
    cumulative_return = 0.0

    # Track positions: (bond_type, maturity_date) -> {quantity, cost_basis}
    positions: dict[tuple, dict] = {}

    def _get_latest_price(bond_type, maturity_date, as_of_date):
        """Get latest price for a bond up to as_of_date."""
        best_price = None
        best_date = None
        for p in prices_records:
            if p[C.BOND_TYPE.value] != bond_type:
                continue
            if p[C.MATURITY_DATE.value] != maturity_date:
                continue
            ref_date = p[C.REFERENCE_DATE.value]
            if isinstance(ref_date, datetime):
                ref_d = ref_date.date()
            elif isinstance(ref_date, date):
                ref_d = ref_date
            else:
                continue
            if ref_d <= as_of_date:
                if best_date is None or ref_d > best_date:
                    best_date = ref_d
                    best_price = p[C.SELL_PRICE.value]
        return best_price

    for month_start in months:
        month_end = _last_day_of_month(month_start)
        month_start_dt = datetime(month_start.year, month_start.month, month_start.day)
        month_end_dt = datetime(month_end.year, month_end.month, month_end.day)

        # Get operations in this month
        month_ops = []
        for op in ops_records:
            op_date = op[C.OPERATION_DATE.value]
            if isinstance(op_date, datetime):
                op_d = op_date.date()
            elif isinstance(op_date, date):
                op_d = op_date
            else:
                continue
            if month_start <= op_d <= month_end:
                month_ops.append(op)

        # Calculate portfolio value at start of month (BMV)
        bmv = 0.0
        if positions:
            for (bond_type, maturity_date), pos in positions.items():
                price = _get_latest_price(bond_type, maturity_date, month_end)
                if price is not None:
                    bmv += pos["quantity"] * price

        # Process operations and calculate weighted cash flow
        net_cash_flow = 0.0
        weighted_cash_flow = 0.0
        total_days = (month_end - month_start).days + 1

        for op in month_ops:
            bond_key = (op[C.BOND_TYPE.value], op[C.MATURITY_DATE.value])
            is_buy = op[C.OPERATION_TYPE.value] in ["C", "D", "buy"]

            op_date = op[C.OPERATION_DATE.value]
            if isinstance(op_date, datetime):
                op_d = op_date.date()
            elif isinstance(op_date, date):
                op_d = op_date
            else:
                op_d = month_start

            days_remaining = (month_end - op_d).days
            weight = days_remaining / total_days if total_days > 0 else 0.0

            if is_buy:
                cash_flow = op[C.OPERATION_VALUE.value]
                net_cash_flow += cash_flow
                weighted_cash_flow += cash_flow * weight

                if bond_key not in positions:
                    positions[bond_key] = {"quantity": 0.0, "cost_basis": 0.0}
                positions[bond_key]["quantity"] += op[C.QUANTITY.value]
                positions[bond_key]["cost_basis"] += op[C.OPERATION_VALUE.value]
            else:
                cash_flow = -abs(op[C.OPERATION_VALUE.value])
                net_cash_flow += cash_flow
                weighted_cash_flow += cash_flow * weight

                if bond_key in positions:
                    positions[bond_key]["quantity"] += op[C.QUANTITY.value]  # negative quantity

        # Process coupon payments in this month
        if coupons is not None and coupons.height > 0 and positions:
            month_coupon_records = coupons.filter(
                (pl.col(C.BUYBACK_DATE.value) >= month_start_dt) & (pl.col(C.BUYBACK_DATE.value) <= month_end_dt)
            ).to_dicts()
            for coupon_row in month_coupon_records:
                coupon_key = (coupon_row[C.BOND_TYPE.value], coupon_row[C.MATURITY_DATE.value])
                if coupon_key in positions and positions[coupon_key]["quantity"] > 0:
                    coupon_amount = positions[coupon_key]["quantity"] * coupon_row[C.UNIT_PRICE.value]
                    coupon_date = coupon_row[C.BUYBACK_DATE.value]
                    if isinstance(coupon_date, datetime):
                        coupon_d = coupon_date.date()
                    elif isinstance(coupon_date, date):
                        coupon_d = coupon_date
                    else:
                        coupon_d = month_start
                    days_remaining = (month_end - coupon_d).days
                    weight = days_remaining / total_days if total_days > 0 else 0.0
                    net_cash_flow -= coupon_amount
                    weighted_cash_flow -= coupon_amount * weight

        # Calculate portfolio value at end of month (EMV)
        emv = 0.0
        if positions:
            for (bond_type, maturity_date), pos in positions.items():
                if pos["quantity"] > 0:
                    price = _get_latest_price(bond_type, maturity_date, month_end)
                    if price is not None:
                        emv += pos["quantity"] * price

        # Calculate Modified Dietz return
        denominator = bmv + weighted_cash_flow
        if denominator > 0.01:
            monthly_return = ((emv - bmv - net_cash_flow) / denominator) * 100
            monthly_return = max(-100.0, min(1000.0, monthly_return))
        elif emv > 0 and bmv < 0.01:
            monthly_return = 100.0  # New portfolio
        else:
            monthly_return = 0.0

        # Update cumulative return
        cumulative_return = (1 + cumulative_return / 100) * (1 + monthly_return / 100) - 1
        cumulative_return *= 100

        results.append(
            {
                "month": month_start_dt,
                "monthly_return": monthly_return,
                "cumulative_return": cumulative_return,
                "portfolio_value": emv,
                "net_cash_flow": net_cash_flow,
            }
        )

    if not results:
        return pl.DataFrame()

    return pl.DataFrame(results)
