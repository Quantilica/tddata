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


import textwrap
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import seaborn as sns

from . import analytics
from .constants import Column as C
from .constants import Gender


def human_format(num, pos):
    """
    Format large numbers with suffixes (K, M, B, T).
    Use generic logic for both currency and counts.
    """
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # Add more suffixes if you need
    suffixes = ["", "K", "M", "B", "T"]
    if magnitude < len(suffixes):
        return f"{num:.1f}{suffixes[magnitude]}"
    return f"{num:.1f}E{magnitude}"


def plot_prices(data: pd.DataFrame, bond_type: str, variable: str):
    # To avoid long code lines we create conditions separately
    cond_a = data[C.BOND_TYPE.value] == bond_type  # Filter by bond type
    cond_b = data[C.BUY_PRICE.value] > 0  # Filter out rows with zero prices
    cond_c = data[C.SELL_PRICE.value] > 0  # Filter out rows with zero prices
    subset = data[cond_a & cond_b & cond_c]
    # Sort the data by maturity date
    subset = subset.sort_values(by=[C.MATURITY_DATE.value, C.REFERENCE_DATE.value])
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
    f, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(
        data=subset,
        x=C.REFERENCE_DATE.value,
        y=variable,
        hue=C.MATURITY_DATE.value,
        estimator=None,
        ax=ax,
        palette="viridis",
        legend="full",
        linewidth=1,
    )
    ax.set_title(f"Tesouro Direto | {bond_type} | {variable_description}")
    ax.set_xlabel("Date")
    ax.set_ylabel(f"{variable_description}")

    # Format Y axis
    if "Yield" not in variable_description:
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(human_format))

    # Legend title and position
    handles, labels = ax.get_legend_handles_labels()

    # Format the maturity dates in the legend as %b/%Y
    # Ensure labels are parsed as datetime if they aren't already string-formatted well
    # But seaborn/matplotlib sometimes return different things in labels depending on version.
    # We will try to be safe.
    new_labels = []
    for label in labels:
        try:
            new_labels.append(pd.to_datetime(label).strftime("%b/%Y"))
        except Exception:
            new_labels.append(str(label))
    labels = new_labels

    # If there are more than 10 labels, show only a subset of them
    n_labels = len(labels)
    if n_labels > 10:
        step = n_labels // 10
        labels = labels[::step]
        handles = handles[::step]

    ax.legend(
        handles=handles,
        labels=labels,
        title="Maturity",
        loc="center left",
        bbox_to_anchor=(1, 0.5),
    )
    _add_footer(f)
    # Grid off
    sns.despine(ax=ax)
    f.tight_layout()
    return f


def plot_stock(data: pd.DataFrame, by_bond_type: bool = True):
    """Plot the evolution of the Stock Value."""
    f, ax = plt.subplots(figsize=(10, 6))

    df_grouped = analytics.aggregate_stock(data, by_bond_type=by_bond_type)

    if by_bond_type:
        sns.lineplot(
            data=df_grouped,
            x=C.STOCK_MONTH.value,
            y=C.STOCK_VALUE.value,
            hue=C.BOND_TYPE.value,
            ax=ax,
        )
        ax.legend(title="Bond Type")
    else:
        sns.lineplot(
            data=df_grouped,
            x=C.STOCK_MONTH.value,
            y=C.STOCK_VALUE.value,
            ax=ax,
        )

    ax.set_title("Tesouro Direto Stock Value Evolution")
    ax.set_ylabel("Stock Value (R$)")
    ax.set_xlabel("Date")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(human_format))
    _add_footer(f)
    sns.despine(ax=ax)
    f.tight_layout()
    return f


def plot_investors_demographics(
    data: pd.DataFrame,
    column: str = C.STATE.value,
    top_n: int = 15,
    chart_type: str = "bar",
):
    """Plot distribution of investors by a categorical column (State, Gender, etc)."""
    f, ax = plt.subplots(figsize=(10, 6))

    counts = analytics.prepare_demographics_counts(data, column, top_n)
    human_col = _humanize_label(column)

    # Plot based on chart type
    if chart_type == "pie":
        _plot_demographics_pie(ax, counts)
    elif chart_type == "barh":
        _plot_demographics_barh(ax, counts, human_col)
    else:
        _plot_demographics_bar(ax, counts, human_col, column)

    ax.set_title(f"Investors Distribution by {human_col}")
    _add_footer(f)
    f.tight_layout()
    return f


def _plot_demographics_pie(ax, counts: pd.Series):
    """Plot demographics data as a pie chart."""
    ax.pie(
        counts.values,
        labels=counts.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=sns.color_palette("viridis", len(counts)),
    )
    # Equal aspect ratio ensures that pie is drawn as a circle.
    ax.axis("equal")


def _plot_demographics_barh(ax, counts: pd.Series, human_col: str):
    """Plot demographics data as a horizontal bar chart."""
    sns.barplot(
        x=counts.values,
        y=counts.index,
        hue=counts.index,
        palette="viridis",
        legend=False,
        ax=ax,
    )
    ax.set_xlabel("Count")
    ax.set_ylabel(human_col)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(human_format))

    # Wrap long labels
    max_width = 30
    new_labels = [textwrap.fill(str(label), width=max_width) for label in counts.index]
    ax.set_yticks(range(len(counts)))
    ax.set_yticklabels(new_labels)

    sns.despine(ax=ax)


def _plot_demographics_bar(ax, counts: pd.Series, human_col: str, column: str):
    """Plot demographics data as a vertical bar chart."""
    sns.barplot(
        x=counts.index,
        y=counts.values,
        hue=counts.index,
        palette="viridis",
        legend=False,
        ax=ax,
    )
    ax.set_ylabel("Count")
    ax.set_xlabel(human_col)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(human_format))

    # For age, limit the number of x-axis ticks to avoid overcrowding
    if column == C.AGE.value:
        ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=20, integer=True))

    plt.xticks(rotation=45)
    sns.despine(ax=ax)


def plot_investors_population_pyramid(data: pd.DataFrame):
    """Plot a population pyramid showing age distribution by gender."""

    pivoted = analytics.prepare_population_pyramid(data)

    # Get labels for male and female (handle missing genders gracefully)
    male_label = Gender.get_labels()[Gender.MALE.value]
    female_label = Gender.get_labels()[Gender.FEMALE.value]

    # Create the plot
    f, ax = plt.subplots(figsize=(10, 8))

    y_pos = range(len(pivoted))

    # Plot males on the left (negative values)
    if male_label in pivoted.columns:
        ax.barh(
            y_pos,
            -pivoted[male_label],
            height=0.8,
            label=male_label,
            color="steelblue",
        )

    # Plot females on the right (positive values)
    if female_label in pivoted.columns:
        ax.barh(
            y_pos,
            pivoted[female_label],
            height=0.8,
            label=female_label,
            color="coral",
        )

    # Customize the plot
    ax.set_yticks(y_pos)
    ax.set_yticklabels(pivoted.index)
    ax.set_xlabel("Number of Investors")
    ax.set_ylabel("Age Group")
    ax.set_title("Investors Population Pyramid by Age and Gender")

    # Format x-axis to show absolute values
    ax.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, pos: human_format(abs(x), pos))
    )

    # Add vertical line at zero
    ax.axvline(0, color="black", linewidth=0.8)

    # Add legend
    ax.legend(loc="upper right")

    # Remove top and right spines
    sns.despine(ax=ax)

    _add_footer(f)
    f.tight_layout()
    return f


def plot_investors_evolution(data: pd.DataFrame, freq: str = "ME"):
    """Plot the number of new investors over time."""
    f, ax = plt.subplots(figsize=(10, 6))

    resampled = analytics.aggregate_new_investors(data, freq)

    sns.lineplot(data=resampled, x=C.JOIN_DATE.value, y="new_investors", ax=ax)

    ax.set_title("New Investors Over Time")
    ax.set_ylabel("Number of New Investors")
    ax.set_xlabel("Date")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(human_format))
    _add_footer(f)
    sns.despine(ax=ax)
    f.tight_layout()
    return f


def plot_operations(data: pd.DataFrame, by_type: bool = True):
    """Plot operations value over time."""
    f, ax = plt.subplots(figsize=(10, 6))

    grouped = analytics.aggregate_operations(data, by_type)

    if by_type:
        sns.lineplot(
            data=grouped,
            x="month",
            y=C.OPERATION_VALUE.value,
            hue=C.OPERATION_TYPE.value,
            ax=ax,
        )
        ax.legend(title="Operation Type")
    else:
        sns.lineplot(data=grouped, x="month", y=C.OPERATION_VALUE.value, ax=ax)

    ax.set_title("Operations Volume Over Time")
    ax.set_ylabel("Total Value (R$)")
    ax.set_xlabel("Date")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(human_format))
    _add_footer(f)
    sns.despine(ax=ax)
    f.tight_layout()
    return f


def plot_sales(data: pd.DataFrame, by_bond_type: bool = True):
    """Plot sales value over time."""
    return _plot_value_over_time(
        data,
        date_col=C.SALE_DATE.value,
        value_col=C.VALUE.value,
        title="Sales Volume Over Time",
        hue_col=C.BOND_TYPE.value if by_bond_type else None,
        legend_title="Bond Type",
    )


def plot_buybacks(data: pd.DataFrame, by_bond_type: bool = True):
    """Plot buybacks (redemptions) value over time."""
    return _plot_value_over_time(
        data,
        date_col=C.BUYBACK_DATE.value,
        value_col=C.VALUE.value,
        title="Buybacks Volume Over Time",
        hue_col=C.BOND_TYPE.value if by_bond_type else None,
        legend_title="Bond Type",
    )


def plot_maturities(data: pd.DataFrame, by_bond_type: bool = True):
    """Plot maturities value over time."""
    return _plot_value_over_time(
        data,
        date_col=C.BUYBACK_DATE.value,  # Maturities file uses 'Data Resgate' -> BUYBACK_DATE/REDEMPTION_DATE
        value_col=C.VALUE.value,
        title="Maturities Volume Over Time",
        hue_col=C.BOND_TYPE.value if by_bond_type else None,
        legend_title="Bond Type",
    )


def plot_interest_coupons(data: pd.DataFrame, by_bond_type: bool = True):
    """Plot interest coupons payments value over time."""
    return _plot_value_over_time(
        data,
        date_col=C.BUYBACK_DATE.value,  # Interest coupons file uses 'Data Resgate' similar to maturities
        value_col=C.VALUE.value,
        title="Interest Coupons Payments Over Time",
        hue_col=C.BOND_TYPE.value if by_bond_type else None,
        legend_title="Bond Type",
    )


def _plot_value_over_time(
    data: pd.DataFrame,
    date_col: str,
    value_col: str,
    title: str,
    hue_col: Optional[str] = None,
    legend_title: Optional[str] = None,
):
    f, ax = plt.subplots(figsize=(10, 6))

    grouped = analytics.aggregate_value_over_time(
        data, date_col, value_col, group_col=hue_col
    )

    if hue_col:
        sns.lineplot(data=grouped, x="month", y=value_col, hue=hue_col, ax=ax)
        if legend_title:
            ax.legend(title=legend_title)
    else:
        sns.lineplot(data=grouped, x="month", y=value_col, ax=ax)

    ax.set_title(title)
    ax.set_ylabel("Value (R$)")
    ax.set_xlabel("Date")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(human_format))
    _add_footer(f)
    sns.despine(ax=ax)
    f.tight_layout()
    return f


def _add_footer(fig):
    fig.text(
        0.01,
        0.01,
        "Data source: Tesouro Direto",
        horizontalalignment="left",
        fontsize=8,
        color="gray",
    )


def _humanize_label(label: str) -> str:
    return label.replace("_", " ").title()
