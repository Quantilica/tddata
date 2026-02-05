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


import pandas as pd

from .constants import (
    AccountStatus,
    Gender,
    OperationType,
    TradedLast12Months,
)
from .constants import Column as C


def aggregate_stock(data: pd.DataFrame, by_bond_type: bool = True) -> pd.DataFrame:
    """Aggregate stock value by month and optionally bond type."""
    if by_bond_type:
        return data.groupby([C.STOCK_MONTH.value, C.BOND_TYPE.value])[C.STOCK_VALUE.value].sum().reset_index()
    return data.groupby([C.STOCK_MONTH.value])[C.STOCK_VALUE.value].sum().reset_index()


def prepare_prices(data: pd.DataFrame, bond_type: str) -> pd.DataFrame:
    """Filter and sort prices data for plotting."""
    cond_a = data[C.BOND_TYPE.value] == bond_type  # Filter by bond type
    cond_b = data[C.BUY_PRICE.value] > 0  # Filter out rows with zero prices
    cond_c = data[C.SELL_PRICE.value] > 0  # Filter out rows with zero prices
    subset = data[cond_a & cond_b & cond_c]
    # Sort the data by maturity date
    subset = subset.sort_values(by=[C.MATURITY_DATE.value, C.REFERENCE_DATE.value])
    return subset



def prepare_demographics_counts(
    data: pd.DataFrame, column: str, top_n: int = 15
) -> pd.Series:
    """Get value counts for demographics data with human readable labels."""
    df = data.copy()

    # Deduplicate by investor ID to avoid counting same investor multiple times
    # (investors can have multiple records if registered with multiple institutions)
    if C.INVESTOR_ID.value in df.columns:
        df = df.drop_duplicates(subset=[C.INVESTOR_ID.value], keep="first")

    # Map enum codes to human-readable labels
    if column == C.GENDER.value:
        df[column] = df[column].map(Gender.get_labels())
    elif column == C.ACCOUNT_STATUS.value:
        df[column] = df[column].map(AccountStatus.get_labels())
    elif column == C.TRADED_LAST_12_MONTHS.value:
        df[column] = df[column].map(TradedLast12Months.get_labels())

    if column == C.AGE.value:
        return df[column].value_counts().sort_index()
    return df[column].value_counts().head(top_n)


def prepare_population_pyramid(data: pd.DataFrame) -> pd.DataFrame:
    """Prepare data for population pyramid (age bins x gender)."""
    df = data.copy()

    # Deduplicate by investor ID to avoid counting same investor multiple times
    # (investors can have multiple records if registered with multiple institutions)
    if C.INVESTOR_ID.value in df.columns:
        df = df.drop_duplicates(subset=[C.INVESTOR_ID.value], keep="first")

    df = df[[C.AGE.value, C.GENDER.value]].copy()

    # Map gender codes to labels
    df[C.GENDER.value] = df[C.GENDER.value].map(Gender.get_labels())

    # Create age bins (5-year intervals)
    if df[C.AGE.value].dropna().empty:
        return pd.DataFrame()

    max_age = int(df[C.AGE.value].max())
    min_age = int(df[C.AGE.value].min())
    bins = list(range(min_age - (min_age % 5), max_age + 5, 5))
    labels = [f"{i}-{i + 4}" for i in bins[:-1]]

    df["age_group"] = pd.cut(df[C.AGE.value], bins=bins, labels=labels, right=False)

    # Count by age group and gender
    grouped = df.groupby(["age_group", C.GENDER.value], observed=False).size().reset_index(name="count")

    # Pivot to get male and female columns
    pivoted = grouped.pivot(index="age_group", columns=C.GENDER.value, values="count").fillna(0)

    return pivoted


def aggregate_new_investors(data: pd.DataFrame, freq: str = "ME") -> pd.DataFrame:
    """Resample new investors data by frequency."""
    df = data.copy()

    # Deduplicate by investor ID to avoid counting same investor multiple times
    # (investors can have multiple records if registered with multiple institutions)
    if C.INVESTOR_ID.value in df.columns:
        df = df.drop_duplicates(subset=[C.INVESTOR_ID.value], keep="first")

    return df.set_index(C.JOIN_DATE.value).resample(freq).size().reset_index(name="new_investors")


def aggregate_operations(data: pd.DataFrame, by_type: bool = True) -> pd.DataFrame:
    """Aggregate operations by month and optionally type."""
    df = data.copy()
    df["month"] = df[C.OPERATION_DATE.value].dt.to_period("M").dt.to_timestamp()

    if by_type:
        df[C.OPERATION_TYPE.value] = df[C.OPERATION_TYPE.value].replace(OperationType.get_labels())
        return df.groupby(["month", C.OPERATION_TYPE.value])[C.OPERATION_VALUE.value].sum().reset_index()

    return df.groupby("month")[C.OPERATION_VALUE.value].sum().reset_index()


def aggregate_value_over_time(
    data: pd.DataFrame, date_col: str, value_col: str, group_col: str | None = None
) -> pd.DataFrame:
    """Generic aggregation of value over time (monthly)."""
    df = data.copy()
    df["month"] = df[date_col].dt.to_period("M").dt.to_timestamp()

    if group_col:
        return df.groupby(["month", group_col])[value_col].sum().reset_index()
    return df.groupby("month")[value_col].sum().reset_index()


# ============================================================================
# Return Calculations
# ============================================================================


def calculate_simple_return(
    current_value: pd.Series,
    initial_value: pd.Series,
    min_denominator: float = 0.01,
) -> pd.Series:
    """Calculate simple percentage return for series.

    Formula: ((current_value / initial_value) - 1) * 100

    Args:
        current_value: The current/ending values.
        initial_value: The initial/beginning values.
        min_denominator: Minimum value to avoid division by zero.

    Returns:
        Series of returns as percentages. Returns 0.0 where invalid.

    Example:
        >>> prices = pd.DataFrame({
        ...     'buy_price': [10000, 20000, 5000],
        ...     'sell_price': [11000, 18000, 5500]
        ... })
        >>> calculate_simple_return(prices['sell_price'], prices['buy_price'])
        0    10.0
        1   -10.0
        2    10.0
        dtype: float64
    """
    result = pd.Series(0.0, index=current_value.index)
    valid = (initial_value >= min_denominator) & (current_value > 0)
    result[valid] = ((current_value[valid] / initial_value[valid]) - 1) * 100
    return result


def calculate_holding_period_days(
    start_date: pd.Series,
    end_date: pd.Series | pd.Timestamp | None = None,
) -> pd.Series:
    """Calculate holding period in days.

    Args:
        start_date: Series of start dates.
        end_date: Series of end dates, single date, or None (defaults to today).

    Returns:
        Series of holding periods in days.

    Example:
        >>> operations = pd.DataFrame({
        ...     'buy_date': pd.to_datetime(['2024-01-01', '2024-06-01']),
        ...     'sell_date': pd.to_datetime(['2024-07-01', '2024-12-01'])
        ... })
        >>> calculate_holding_period_days(operations['buy_date'], operations['sell_date'])
        0    182
        1    183
        dtype: int64
    """
    if end_date is None:
        end_date = pd.Timestamp.now().normalize()

    if isinstance(end_date, pd.Timestamp):
        return (end_date - start_date).dt.days

    return (end_date - start_date).dt.days


def calculate_annualized_return(
    current_value: pd.Series,
    initial_value: pd.Series,
    holding_days: pd.Series,
    min_days: int = 30,
    min_denominator: float = 0.01,
) -> pd.Series:
    """Calculate annualized return (CAGR) for series.

    Formula: ((current_value / initial_value) ^ (365 / holding_days) - 1) * 100

    Args:
        current_value: The current/ending values.
        initial_value: The initial/beginning values.
        holding_days: Number of days held.
        min_days: Minimum holding period required.
        min_denominator: Minimum value to avoid division by zero.

    Returns:
        Series of annualized returns as percentages. Returns 0.0 where invalid.

    Example:
        >>> positions = pd.DataFrame({
        ...     'buy_value': [10000, 10000],
        ...     'current_value': [11000, 11000],
        ...     'holding_days': [365, 182]
        ... })
        >>> calculate_annualized_return(
        ...     positions['current_value'],
        ...     positions['buy_value'],
        ...     positions['holding_days']
        ... )
        0    10.0
        1    21.0
        dtype: float64
    """
    result = pd.Series(0.0, index=current_value.index)

    valid = (holding_days >= min_days) & (initial_value >= min_denominator) & (current_value > 0)

    value_ratio = current_value / initial_value
    valid = valid & (value_ratio > 0)

    if valid.any():
        exponent = 365.0 / holding_days[valid]
        try:
            annualized = ((value_ratio[valid] ** exponent) - 1) * 100
            # Cap extreme values
            annualized = annualized.clip(-100.0, 1000.0)
            result[valid] = annualized
        except (ValueError, OverflowError):
            pass

    return result


def calculate_operations_returns(
    operations: pd.DataFrame,
    prices: pd.DataFrame,
    current_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Calculate returns for individual operations (buy/sell pairs).

    This function matches buy operations with their corresponding sell operations
    and calculates returns. For open positions, it uses current prices.

    Args:
        operations: DataFrame with columns: operation_date, bond_type, maturity_date,
            quantity, bond_value, operation_value, operation_type.
        prices: DataFrame with columns: reference_date, bond_type, maturity_date,
            sell_price.
        current_date: Date to calculate returns as of (defaults to today).

    Returns:
        DataFrame with buy operations and calculated returns.

    Example:
        >>> ops = pd.DataFrame({
        ...     'operation_date': pd.to_datetime(['2024-01-01', '2024-07-01']),
        ...     'bond_type': ['Tesouro Selic', 'Tesouro Selic'],
        ...     'maturity_date': pd.to_datetime(['2030-01-01', '2030-01-01']),
        ...     'quantity': [10, -10],
        ...     'bond_value': [10000, 11000],
        ...     'operation_value': [10000, 11000],
        ...     'operation_type': ['C', 'V']
        ... })
        >>> prices_df = pd.DataFrame({
        ...     'reference_date': pd.to_datetime(['2024-06-01']),
        ...     'bond_type': ['Tesouro Selic'],
        ...     'maturity_date': pd.to_datetime(['2030-01-01']),
        ...     'sell_price': [10500]
        ... })
        >>> returns = calculate_operations_returns(ops, prices_df)
    """
    if current_date is None:
        current_date = pd.Timestamp.now().normalize()

    df = operations.copy()

    # Separate buys and sells
    is_buy = df[C.OPERATION_TYPE.value].isin(["C", "D", "buy"])
    buys = df[is_buy].copy()
    sells = df[~is_buy].copy()

    if buys.empty:
        return pd.DataFrame()

    # Add holding period for open positions
    buys["holding_days"] = (current_date - buys[C.OPERATION_DATE.value]).dt.days
    buys["status"] = "open"
    buys["sell_date"] = pd.NaT
    buys["sell_value"] = 0.0
    buys["current_value"] = 0.0

    # Match sells to buys (simplified FIFO)
    for bond_key in buys.groupby([C.BOND_TYPE.value, C.MATURITY_DATE.value]).groups.keys():
        bond_buys = buys[(buys[C.BOND_TYPE.value] == bond_key[0]) & (buys[C.MATURITY_DATE.value] == bond_key[1])]
        bond_sells = sells[
            (sells[C.BOND_TYPE.value] == bond_key[0]) & (sells[C.MATURITY_DATE.value] == bond_key[1])
        ].sort_values(C.OPERATION_DATE.value)

        for sell_idx, sell_row in bond_sells.iterrows():
            matching_buys = bond_buys[
                (bond_buys["status"] == "open")
                & (bond_buys[C.OPERATION_DATE.value] <= sell_row[C.OPERATION_DATE.value])
            ].sort_values(C.OPERATION_DATE.value)

            if not matching_buys.empty:
                buy_idx = matching_buys.index[0]
                buys.loc[buy_idx, "status"] = "closed"
                buys.loc[buy_idx, "sell_date"] = sell_row[C.OPERATION_DATE.value]
                buys.loc[buy_idx, "sell_value"] = abs(sell_row[C.OPERATION_VALUE.value])
                buys.loc[buy_idx, "holding_days"] = (
                    sell_row[C.OPERATION_DATE.value] - buys.loc[buy_idx, C.OPERATION_DATE.value]
                ).days

    # Get current prices for open positions
    if not prices.empty:
        # Create a month column for matching
        buys["month"] = current_date.to_period("M").to_timestamp()
        prices_monthly = prices.copy()
        prices_monthly["month"] = prices_monthly[C.REFERENCE_DATE.value].dt.to_period("M").dt.to_timestamp()

        # Get latest price per bond per month
        latest_prices = (
            prices_monthly.sort_values(C.REFERENCE_DATE.value)
            .groupby([C.BOND_TYPE.value, C.MATURITY_DATE.value, "month"])
            .last()
            .reset_index()
        )

        # Merge prices
        buys = buys.merge(
            latest_prices[[C.BOND_TYPE.value, C.MATURITY_DATE.value, "month", C.SELL_PRICE.value]],
            on=[C.BOND_TYPE.value, C.MATURITY_DATE.value, "month"],
            how="left",
        )

        # Calculate current value for open positions
        open_mask = buys["status"] == "open"
        buys.loc[open_mask, "current_value"] = (
            buys.loc[open_mask, C.QUANTITY.value] * buys.loc[open_mask, C.SELL_PRICE.value]
        )
        buys.drop(columns=["month", C.SELL_PRICE.value], inplace=True, errors="ignore")

    # Calculate returns
    buys["end_value"] = buys.apply(
        lambda row: row["sell_value"] if row["status"] == "closed" else row["current_value"], axis=1
    )

    buys["simple_return"] = calculate_simple_return(buys["end_value"], buys[C.OPERATION_VALUE.value])

    buys["annualized_return"] = calculate_annualized_return(
        buys["end_value"], buys[C.OPERATION_VALUE.value], buys["holding_days"]
    )

    return buys


def calculate_portfolio_monthly_returns(
    operations: pd.DataFrame,
    prices: pd.DataFrame,
    start_date: pd.Timestamp | None = None,
    end_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Calculate monthly portfolio returns using Modified Dietz method.

    The Modified Dietz method properly accounts for cash flows by time-weighting
    them based on when they occur during the period.

    Args:
        operations: DataFrame with operation_date, bond_type, maturity_date,
            quantity, bond_value, operation_value, operation_type columns.
        prices: DataFrame with reference_date, bond_type, maturity_date,
            sell_price columns.
        start_date: Start date for calculations (defaults to first operation).
        end_date: End date (defaults to today).

    Returns:
        DataFrame with monthly returns and cumulative returns.

    Example:
        >>> # See calculate_operations_returns for data structure
        >>> monthly_returns = calculate_portfolio_monthly_returns(operations, prices)
    """
    if operations.empty:
        return pd.DataFrame()

    if start_date is None:
        start_date = operations[C.OPERATION_DATE.value].min()

    if end_date is None:
        end_date = pd.Timestamp.now().normalize()

    # Create monthly date range
    months = pd.date_range(start_date.to_period("M").to_timestamp(), end_date.to_period("M").to_timestamp(), freq="MS")

    results = []
    cumulative_return = 0.0

    # Track positions
    positions = {}  # (bond_type, maturity_date) -> {quantity, cost_basis}

    for month_start in months:
        month_end = (month_start + pd.DateOffset(months=1)) - pd.DateOffset(days=1)

        # Get operations in this month
        month_ops = operations[
            (operations[C.OPERATION_DATE.value] >= month_start) & (operations[C.OPERATION_DATE.value] <= month_end)
        ]

        # Calculate portfolio value at start of month
        bmv = 0.0  # Beginning Market Value
        if positions:
            month_key = month_start.strftime("%Y-%m")
            for (bond_type, maturity_date), pos in positions.items():
                price_data = prices[
                    (prices[C.BOND_TYPE.value] == bond_type)
                    & (prices[C.MATURITY_DATE.value] == maturity_date)
                    & (prices[C.REFERENCE_DATE.value] <= month_end)
                ]
                if not price_data.empty:
                    latest_price = price_data.sort_values(C.REFERENCE_DATE.value).iloc[-1][C.SELL_PRICE.value]
                    bmv += pos["quantity"] * latest_price

        # Process operations and calculate weighted cash flow
        net_cash_flow = 0.0
        weighted_cash_flow = 0.0
        total_days = (month_end - month_start).days + 1

        for _, op in month_ops.iterrows():
            bond_key = (op[C.BOND_TYPE.value], op[C.MATURITY_DATE.value])
            is_buy = op[C.OPERATION_TYPE.value] in ["C", "D", "buy"]

            # Calculate time weight
            days_remaining = (month_end - op[C.OPERATION_DATE.value]).days
            weight = days_remaining / total_days if total_days > 0 else 0.0

            if is_buy:
                cash_flow = op[C.OPERATION_VALUE.value]
                net_cash_flow += cash_flow
                weighted_cash_flow += cash_flow * weight

                # Update position
                if bond_key not in positions:
                    positions[bond_key] = {"quantity": 0.0, "cost_basis": 0.0}
                positions[bond_key]["quantity"] += op[C.QUANTITY.value]
                positions[bond_key]["cost_basis"] += op[C.OPERATION_VALUE.value]
            else:
                cash_flow = -abs(op[C.OPERATION_VALUE.value])
                net_cash_flow += cash_flow
                weighted_cash_flow += cash_flow * weight

                # Update position
                if bond_key in positions:
                    positions[bond_key]["quantity"] += op[C.QUANTITY.value]  # negative quantity

        # Calculate portfolio value at end of month
        emv = 0.0  # Ending Market Value
        if positions:
            for (bond_type, maturity_date), pos in positions.items():
                if pos["quantity"] > 0:
                    price_data = prices[
                        (prices[C.BOND_TYPE.value] == bond_type)
                        & (prices[C.MATURITY_DATE.value] == maturity_date)
                        & (prices[C.REFERENCE_DATE.value] <= month_end)
                    ]
                    if not price_data.empty:
                        latest_price = price_data.sort_values(C.REFERENCE_DATE.value).iloc[-1][C.SELL_PRICE.value]
                        emv += pos["quantity"] * latest_price

        # Calculate Modified Dietz return
        denominator = bmv + weighted_cash_flow
        if denominator > 0.01:
            monthly_return = ((emv - bmv - net_cash_flow) / denominator) * 100
            monthly_return = max(-100.0, min(1000.0, monthly_return))  # Cap extremes
        elif emv > 0 and bmv < 0.01:
            monthly_return = 100.0  # New portfolio
        else:
            monthly_return = 0.0

        # Update cumulative return
        cumulative_return = (1 + cumulative_return / 100) * (1 + monthly_return / 100) - 1
        cumulative_return *= 100

        results.append(
            {
                "month": month_start,
                "monthly_return": monthly_return,
                "cumulative_return": cumulative_return,
                "portfolio_value": emv,
                "net_cash_flow": net_cash_flow,
            }
        )

    return pd.DataFrame(results)
