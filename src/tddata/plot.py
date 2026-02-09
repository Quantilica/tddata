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


from typing import Optional

import altair as alt
import polars as pl

from . import analytics
from .constants import Column as C
from .constants import Gender


def plot_prices(data: pl.DataFrame, bond_type: str, variable: str) -> alt.Chart:
    """Plot bond prices over time by maturity date.

    Args:
        data: Polars DataFrame with prices data
        bond_type: Bond type to filter
        variable: Variable to plot (e.g., 'buy_price', 'sell_price')

    Returns:
        Altair Chart object
    """
    subset = analytics.prepare_prices(data, bond_type)

    variable_description = ""
    if variable == C.BUY_YIELD.value:
        variable_description = "Buy Yield (%)"
    elif variable == C.SELL_YIELD.value:
        variable_description = "Sell Yield (%)"
    elif variable == C.BUY_PRICE.value:
        variable_description = "Buy Price (R$)"
    elif variable == C.SELL_PRICE.value:
        variable_description = "Sell Price (R$)"
    elif variable == C.BASE_PRICE.value:
        variable_description = "Base Price (R$)"

    # Format maturity dates for legend
    subset = subset.with_columns(pl.col(C.MATURITY_DATE.value).dt.strftime("%b/%Y").alias("maturity_formatted"))

    # Build an explicit ordered list of maturities (formatted labels) sorted by the
    # actual maturity date so the legend is chronological rather than alphabetical.
    if C.MATURITY_DATE.value in subset.columns:
        pairs = (
            subset.select([C.MATURITY_DATE.value, "maturity_formatted"])
            .unique()
            .sort(C.MATURITY_DATE.value)
            .filter(pl.col("maturity_formatted").is_not_null())
            .to_dicts()
        )
        maturity_order = []
        seen = set()
        for r in pairs:
            label = r.get("maturity_formatted")
            if label not in seen:
                seen.add(label)
                maturity_order.append(label)
    else:
        maturity_order = None

    chart = (
        alt.Chart(subset)
        .mark_line()
        .encode(
            x=alt.X(f"{C.REFERENCE_DATE.value}:T", title="Date"),
            y=alt.Y(f"{variable}:Q", title=variable_description),
            color=alt.Color(
                "maturity_formatted:N",
                title="Maturity",
                scale=alt.Scale(scheme="viridis"),
                sort=maturity_order,
            ),
            tooltip=[
                alt.Tooltip(f"{C.REFERENCE_DATE.value}:T", title="Date"),
                alt.Tooltip("maturity_formatted:N", title="Maturity"),
                alt.Tooltip(f"{variable}:Q", title=variable_description, format=",.2f"),
            ],
        )
        .properties(
            width=800,
            height=400,
            title=f"Tesouro Direto | {bond_type} | {variable_description}",
        )
    )

    return chart


def plot_stock(data: pl.DataFrame, by_bond_type: bool = True) -> alt.Chart:
    """Plot the evolution of the Stock Value.

    Args:
        data: Polars DataFrame with stock data
        by_bond_type: Whether to split by bond type

    Returns:
        Altair Chart object
    """
    df_grouped = analytics.aggregate_stock(data, by_bond_type=by_bond_type)

    if by_bond_type:
        chart = (
            alt.Chart(df_grouped)
            .mark_line()
            .encode(
                x=alt.X(f"{C.STOCK_MONTH.value}:T", title="Date"),
                y=alt.Y(
                    f"{C.STOCK_VALUE.value}:Q",
                    title="Stock Value (R$)",
                    axis=alt.Axis(format="~s"),
                ),
                color=alt.Color(f"{C.BOND_TYPE.value}:N", title="Bond Type"),
                tooltip=[
                    alt.Tooltip(f"{C.STOCK_MONTH.value}:T", title="Date"),
                    alt.Tooltip(f"{C.BOND_TYPE.value}:N", title="Bond Type"),
                    alt.Tooltip(f"{C.STOCK_VALUE.value}:Q", title="Value", format=",.0f"),
                ],
            )
        )
    else:
        chart = (
            alt.Chart(df_grouped)
            .mark_line()
            .encode(
                x=alt.X(f"{C.STOCK_MONTH.value}:T", title="Date"),
                y=alt.Y(
                    f"{C.STOCK_VALUE.value}:Q",
                    title="Stock Value (R$)",
                    axis=alt.Axis(format="~s"),
                ),
                tooltip=[
                    alt.Tooltip(f"{C.STOCK_MONTH.value}:T", title="Date"),
                    alt.Tooltip(f"{C.STOCK_VALUE.value}:Q", title="Value", format=",.0f"),
                ],
            )
        )

    return chart.properties(
        width=800,
        height=500,
        title="Tesouro Direto Stock Value Evolution",
    )


def plot_investors_demographics(
    data: pl.DataFrame,
    column: str = C.STATE.value,
    top_n: int = 15,
    chart_type: str = "bar",
) -> alt.Chart:
    """Plot distribution of investors by a categorical column.

    Args:
        data: Polars DataFrame with investor data
        column: Column to analyze (e.g., 'state', 'gender', 'age')
        top_n: Number of top categories to show
        chart_type: Type of chart ('bar', 'barh', or 'pie')

    Returns:
        Altair Chart object
    """
    counts_df = analytics.prepare_demographics_counts(data, column, top_n)
    human_col = _humanize_label(column)

    if chart_type == "pie":
        chart = (
            alt.Chart(counts_df)
            .mark_arc()
            .encode(
                theta=alt.Theta("count:Q"),
                color=alt.Color(f"{column}:N", title=human_col),
                tooltip=[
                    alt.Tooltip(f"{column}:N", title=human_col),
                    alt.Tooltip("count:Q", title="Count", format=","),
                ],
            )
        )
    elif chart_type == "barh":
        chart = (
            alt.Chart(counts_df)
            .mark_bar()
            .encode(
                x=alt.X("count:Q", title="Count", axis=alt.Axis(format="~s")),
                y=alt.Y(f"{column}:N", title=human_col, sort="-x"),
                color=alt.Color(f"{column}:N", legend=None),
                tooltip=[
                    alt.Tooltip(f"{column}:N", title=human_col),
                    alt.Tooltip("count:Q", title="Count", format=","),
                ],
            )
        )
    else:  # bar
        chart = (
            alt.Chart(counts_df)
            .mark_bar()
            .encode(
                x=alt.X(f"{column}:N", title=human_col, sort="-y"),
                y=alt.Y("count:Q", title="Count", axis=alt.Axis(format="~s")),
                color=alt.Color(f"{column}:N", legend=None),
                tooltip=[
                    alt.Tooltip(f"{column}:N", title=human_col),
                    alt.Tooltip("count:Q", title="Count", format=","),
                ],
            )
        )

    return chart.properties(
        width=800,
        height=500,
        title=f"Investors Distribution by {human_col}",
    )


def plot_investors_population_pyramid(data: pl.DataFrame) -> alt.Chart:
    """Plot a population pyramid showing age distribution by gender.

    Args:
        data: Polars DataFrame with investor data including age and gender

    Returns:
        Altair Chart object
    """
    pivoted = analytics.prepare_population_pyramid(data)

    # Get labels for male and female
    male_label = Gender.get_labels()[Gender.MALE.value]
    female_label = Gender.get_labels()[Gender.FEMALE.value]

    # Reshape for altair - need long format
    if male_label in pivoted.columns:
        male_data = pivoted.select(
            [
                pl.col("age_group"),
                pl.col(male_label).alias("count"),
            ]
        ).with_columns(
            pl.lit(male_label).alias("gender"),
            (pl.col("count") * -1).cast(pl.Int64).alias("count"),  # Negative for left side
        )
    else:
        male_data = pl.DataFrame(
            {
                "age_group": pl.Series([], dtype=pl.String),
                "count": pl.Series([], dtype=pl.Int64),
                "gender": pl.Series([], dtype=pl.String),
            }
        )

    if female_label in pivoted.columns:
        female_data = pivoted.select(
            [
                pl.col("age_group"),
                pl.col(female_label).alias("count"),
            ]
        ).with_columns(
            pl.lit(female_label).alias("gender"),
            pl.col("count").cast(pl.Int64).alias("count"),
        )
    else:
        female_data = pl.DataFrame(
            {
                "age_group": pl.Series([], dtype=pl.String),
                "count": pl.Series([], dtype=pl.Int64),
                "gender": pl.Series([], dtype=pl.String),
            }
        )

    combined = pl.concat([male_data, female_data])

    # Extract explicit age group order from the pivoted data to make visualization
    # resilient to any DataFrame row ordering changes later.
    age_order = pivoted["age_group"].to_list() if "age_group" in pivoted.columns else None

    chart = (
        alt.Chart(combined)
        .mark_bar()
        .encode(
            y=alt.Y("age_group:N", title="Age Group", sort=age_order),
            x=alt.X(
                "count:Q",
                title="Number of Investors",
                axis=alt.Axis(format="s"),
            ),
            color=alt.Color("gender:N", title="Gender"),
            tooltip=[
                alt.Tooltip("age_group:N", title="Age Group"),
                alt.Tooltip("gender:N", title="Gender"),
                alt.Tooltip("count:Q", title="Count", format=","),
            ],
        )
        .properties(
            width=800,
            height=600,
            title="Investors Population Pyramid by Age and Gender",
        )
    )

    return chart


def plot_investors_evolution(data: pl.DataFrame, freq: str = "1mo") -> alt.Chart:
    """Plot the number of new investors over time.

    Args:
        data: Polars DataFrame with investor join dates
        freq: Frequency for aggregation (e.g., '1mo', '1w')

    Returns:
        Altair Chart object
    """
    resampled = analytics.aggregate_new_investors(data, freq)

    chart = (
        alt.Chart(resampled)
        .mark_line()
        .encode(
            x=alt.X(f"{C.JOIN_DATE.value}:T", title="Date"),
            y=alt.Y(
                "new_investors:Q",
                title="Number of New Investors",
                axis=alt.Axis(format="~s"),
            ),
            tooltip=[
                alt.Tooltip(f"{C.JOIN_DATE.value}:T", title="Date"),
                alt.Tooltip("new_investors:Q", title="New Investors", format=","),
            ],
        )
        .properties(
            width=800,
            height=500,
            title="New Investors Over Time",
        )
    )

    return chart


def plot_operations(data: pl.DataFrame, by_type: bool = True) -> alt.Chart:
    """Plot operations volume over time.

    Args:
        data: Polars DataFrame with operations data
        by_type: Whether to split by operation type

    Returns:
        Altair Chart object
    """
    grouped = analytics.aggregate_operations(data, by_type)

    if by_type:
        chart = (
            alt.Chart(grouped)
            .mark_line()
            .encode(
                x=alt.X("month:T", title="Date"),
                y=alt.Y(
                    f"{C.OPERATION_VALUE.value}:Q",
                    title="Total Value (R$)",
                    axis=alt.Axis(format="~s"),
                ),
                color=alt.Color(f"{C.OPERATION_TYPE.value}:N", title="Operation Type"),
                tooltip=[
                    alt.Tooltip("month:T", title="Date"),
                    alt.Tooltip(f"{C.OPERATION_TYPE.value}:N", title="Type"),
                    alt.Tooltip(f"{C.OPERATION_VALUE.value}:Q", title="Value", format=",.0f"),
                ],
            )
        )
    else:
        chart = (
            alt.Chart(grouped)
            .mark_line()
            .encode(
                x=alt.X("month:T", title="Date"),
                y=alt.Y(
                    f"{C.OPERATION_VALUE.value}:Q",
                    title="Total Value (R$)",
                    axis=alt.Axis(format="~s"),
                ),
                tooltip=[
                    alt.Tooltip("month:T", title="Date"),
                    alt.Tooltip(f"{C.OPERATION_VALUE.value}:Q", title="Value", format=",.0f"),
                ],
            )
        )

    return chart.properties(
        width=800,
        height=500,
        title="Operations Volume Over Time",
    )


def plot_sales(data: pl.DataFrame, by_bond_type: bool = True) -> alt.Chart:
    """Plot sales value over time.

    Args:
        data: Polars DataFrame with sales data
        by_bond_type: Whether to split by bond type

    Returns:
        Altair Chart object
    """
    return _plot_value_over_time(
        data,
        date_col=C.SALE_DATE.value,
        value_col=C.VALUE.value,
        title="Sales Volume Over Time",
        hue_col=C.BOND_TYPE.value if by_bond_type else None,
        legend_title="Bond Type",
    )


def plot_buybacks(data: pl.DataFrame, by_bond_type: bool = True) -> alt.Chart:
    """Plot buybacks (redemptions) value over time.

    Args:
        data: Polars DataFrame with buyback data
        by_bond_type: Whether to split by bond type

    Returns:
        Altair Chart object
    """
    return _plot_value_over_time(
        data,
        date_col=C.BUYBACK_DATE.value,
        value_col=C.VALUE.value,
        title="Buybacks Volume Over Time",
        hue_col=C.BOND_TYPE.value if by_bond_type else None,
        legend_title="Bond Type",
    )


def plot_maturities(data: pl.DataFrame, by_bond_type: bool = True) -> alt.Chart:
    """Plot maturities value over time.

    Args:
        data: Polars DataFrame with maturities data
        by_bond_type: Whether to split by bond type

    Returns:
        Altair Chart object
    """
    return _plot_value_over_time(
        data,
        date_col=C.BUYBACK_DATE.value,
        value_col=C.VALUE.value,
        title="Maturities Volume Over Time",
        hue_col=C.BOND_TYPE.value if by_bond_type else None,
        legend_title="Bond Type",
    )


def plot_interest_coupons(data: pl.DataFrame, by_bond_type: bool = True) -> alt.Chart:
    """Plot interest coupons payments value over time.

    Args:
        data: Polars DataFrame with interest coupon data
        by_bond_type: Whether to split by bond type

    Returns:
        Altair Chart object
    """
    return _plot_value_over_time(
        data,
        date_col=C.BUYBACK_DATE.value,
        value_col=C.VALUE.value,
        title="Interest Coupons Payments Over Time",
        hue_col=C.BOND_TYPE.value if by_bond_type else None,
        legend_title="Bond Type",
    )


def _plot_value_over_time(
    data: pl.DataFrame,
    date_col: str,
    value_col: str,
    title: str,
    hue_col: Optional[str] = None,
    legend_title: Optional[str] = None,
) -> alt.Chart:
    """Helper function to plot values over time.

    Args:
        data: Polars DataFrame
        date_col: Name of date column
        value_col: Name of value column
        title: Chart title
        hue_col: Column to use for color encoding (optional)
        legend_title: Title for legend (optional)

    Returns:
        Altair Chart object
    """
    grouped = analytics.aggregate_value_over_time(
        data, date_col, value_col, group_col=hue_col
    )

    if hue_col:
        chart = (
            alt.Chart(grouped)
            .mark_line()
            .encode(
                x=alt.X("month:T", title="Date"),
                y=alt.Y(
                    f"{value_col}:Q",
                    title="Total Value (R$)",
                    axis=alt.Axis(format="~s"),
                ),
                color=alt.Color(f"{hue_col}:N", title=legend_title or hue_col),
                tooltip=[
                    alt.Tooltip("month:T", title="Date"),
                    alt.Tooltip(f"{hue_col}:N", title=legend_title or hue_col),
                    alt.Tooltip(f"{value_col}:Q", title="Value", format=",.0f"),
                ],
            )
        )
    else:
        chart = (
            alt.Chart(grouped)
            .mark_line()
            .encode(
                x=alt.X("month:T", title="Date"),
                y=alt.Y(
                    f"{value_col}:Q",
                    title="Total Value (R$)",
                    axis=alt.Axis(format="~s"),
                ),
                tooltip=[
                    alt.Tooltip("month:T", title="Date"),
                    alt.Tooltip(f"{value_col}:Q", title="Value", format=",.0f"),
                ],
            )
        )

    return chart.properties(
        width=800,
        height=500,
        title=title,
    )


def _humanize_label(label: str) -> str:
    """Convert snake_case to Title Case."""
    return label.replace("_", " ").title()
