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


import pandas as pd

from .constants import (
    AccountStatus,
    Column,
    Gender,
    OperationType,
    TradedLast12Months,
)


def aggregate_stock(data: pd.DataFrame, by_bond_type: bool = True) -> pd.DataFrame:
    """Aggregate stock value by month and optionally bond type."""
    if by_bond_type:
        return (
            data.groupby([Column.STOCK_MONTH.value, Column.BOND_TYPE.value])[
                Column.STOCK_VALUE.value
            ]
            .sum()
            .reset_index()
        )
    return (
        data.groupby([Column.STOCK_MONTH.value])[Column.STOCK_VALUE.value]
        .sum()
        .reset_index()
    )


def prepare_demographics_counts(
    data: pd.DataFrame, column: str, top_n: int = 15
) -> pd.Series:
    """Get value counts for demographics data with human readable labels."""
    df = data.copy()

    # Map enum codes to human-readable labels
    if column == Column.GENDER.value:
        df[column] = df[column].map(Gender.get_labels())
    elif column == Column.ACCOUNT_STATUS.value:
        df[column] = df[column].map(AccountStatus.get_labels())
    elif column == Column.TRADED_LAST_12_MONTHS.value:
        df[column] = df[column].map(TradedLast12Months.get_labels())

    if column == Column.AGE.value:
        return df[column].value_counts().sort_index()
    return df[column].value_counts().head(top_n)


def prepare_population_pyramid(data: pd.DataFrame) -> pd.DataFrame:
    """Prepare data for population pyramid (age bins x gender)."""
    df = data[[Column.AGE.value, Column.GENDER.value]].copy()

    # Map gender codes to labels
    df[Column.GENDER.value] = df[Column.GENDER.value].map(Gender.get_labels())

    # Create age bins (5-year intervals)
    if df[Column.AGE.value].dropna().empty:
        return pd.DataFrame()

    max_age = int(df[Column.AGE.value].max())
    min_age = int(df[Column.AGE.value].min())
    bins = list(range(min_age - (min_age % 5), max_age + 5, 5))
    labels = [f"{i}-{i + 4}" for i in bins[:-1]]

    df["age_group"] = pd.cut(
        df[Column.AGE.value], bins=bins, labels=labels, right=False
    )

    # Count by age group and gender
    grouped = (
        df.groupby(["age_group", Column.GENDER.value], observed=False)
        .size()
        .reset_index(name="count")
    )

    # Pivot to get male and female columns
    pivoted = grouped.pivot(
        index="age_group", columns=Column.GENDER.value, values="count"
    ).fillna(0)

    return pivoted


def aggregate_new_investors(data: pd.DataFrame, freq: str = "ME") -> pd.DataFrame:
    """Resample new investors data by frequency."""
    return (
        data.set_index(Column.JOIN_DATE.value)
        .resample(freq)
        .size()
        .reset_index(name="new_investors")
    )


def aggregate_operations(data: pd.DataFrame, by_type: bool = True) -> pd.DataFrame:
    """Aggregate operations by month and optionally type."""
    df = data.copy()
    df["month"] = df[Column.OPERATION_DATE.value].dt.to_period("M").dt.to_timestamp()

    if by_type:
        df[Column.OPERATION_TYPE.value] = df[Column.OPERATION_TYPE.value].replace(
            OperationType.get_labels()
        )
        return (
            df.groupby(["month", Column.OPERATION_TYPE.value])[
                Column.OPERATION_VALUE.value
            ]
            .sum()
            .reset_index()
        )

    return df.groupby("month")[Column.OPERATION_VALUE.value].sum().reset_index()


def aggregate_value_over_time(
    data: pd.DataFrame, date_col: str, value_col: str, group_col: str | None = None
) -> pd.DataFrame:
    """Generic aggregation of value over time (monthly)."""
    df = data.copy()
    df["month"] = df[date_col].dt.to_period("M").dt.to_timestamp()

    if group_col:
        return df.groupby(["month", group_col])[value_col].sum().reset_index()
    return df.groupby("month")[value_col].sum().reset_index()
