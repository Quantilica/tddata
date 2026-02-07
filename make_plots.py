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


import argparse
from pathlib import Path

import polars as pl

from tddata import plot, reader, storage
from tddata.constants import Column as C

PLOTS_DIR = Path("plots")
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def save_plot(chart, filename):
    """Save an Altair chart to a file."""
    filepath = PLOTS_DIR / filename
    print(f"Saving {filepath}...")
    chart.save(str(filepath))


def run_prices(data_dir: Path):
    f = storage.get_latest_file(data_dir, "taxas-dos-titulos-ofertados*.csv")
    if not f:
        print("No prices file found.")
        return

    print(f"Loading prices from {f.name}...")
    data = reader.read_prices(f)

    variables = [
        C.BUY_PRICE.value,
        C.BUY_YIELD.value,
        C.SELL_PRICE.value,
        C.SELL_YIELD.value,
        C.BASE_PRICE.value,
    ]

    for bond_type in data[C.BOND_TYPE.value].unique():
        # Clean filename friendly bond type
        bond_slug = storage.slugify(bond_type)
        for var in variables:
            print(f"  Plotting {bond_type} - {var}...")
            try:
                chart = plot.plot_prices(data, bond_type, var)
                save_plot(chart, f"prices_{bond_slug}_{var}.html")
            except Exception as e:
                print(f"  Error plotting {bond_type} {var}: {e}")


def run_stock(data_dir: Path):
    f = storage.get_latest_file(data_dir, "estoque-do-tesouro-direto*.csv")
    if not f:
        print("No stock file found.")
        return

    print(f"Loading stock from {f.name}...")
    data = reader.read_stock(f)

    print("  Plotting stock evolution by bond type...")
    chart = plot.plot_stock(data, by_bond_type=True)
    save_plot(chart, "stock_evolution_by_type.html")

    print("  Plotting total stock evolution...")
    chart = plot.plot_stock(data, by_bond_type=False)
    save_plot(chart, "stock_evolution_total.html")


def run_investors(data_dir: Path):
    # Load all investors files
    # Use storage.get_latest_files to get the latest version of each year's file
    # The pattern for investors is "investidores-do-tesouro-direto-YYYY@timestamp.csv"
    # storage.get_latest_files handles the versioning correctly

    all_files = storage.get_latest_files(data_dir)
    files = [f for f in all_files if "investidores-do-tesouro-direto-" in f.name]

    if not files:
        print("No investors file found.")
        return

    print(f"Loading {len(files)} investors files...")
    all_data = []
    for f in files:
        print(f"    Reading {f.name}...")
        df = reader.read_investors(f)
        all_data.append(df)

    if not all_data:
        return

    full_data = pl.concat(all_data)
    # Deduplicate by investor ID only (investors can have multiple records if registered with multiple institutions)
    # Keep the first occurrence
    full_data = full_data.unique(subset=[C.INVESTOR_ID.value], keep="first")
    # Drop dates before 2000
    full_data = full_data.filter(pl.col(C.JOIN_DATE.value) >= pl.date(2000, 1, 1))

    # Plot population pyramid (age by gender)
    print("  Plotting population pyramid (age by gender)...")
    chart = plot.plot_investors_population_pyramid(full_data)
    save_plot(chart, "investors_population_pyramid.html")

    # Plot other demographics
    demographics = [
        C.STATE.value,
        C.PROFESSION.value,
        C.MARITAL_STATUS.value,
    ]

    for demo in demographics:
        print(f"  Plotting demographics: {demo}...")

        kind = "bar"
        if demo in [C.PROFESSION.value, C.MARITAL_STATUS.value]:
            kind = "barh"

        chart = plot.plot_investors_demographics(full_data, column=demo, chart_type=kind)
        save_plot(chart, f"investors_demographics_{demo}.html")

    print("  Plotting new investors evolution (all history)...")
    chart = plot.plot_investors_evolution(full_data, freq="1mo")
    save_plot(chart, "investors_new_evolution_history.html")


def run_operations(data_dir: Path):
    # Use storage.get_latest_files to get the latest version of each year's file
    all_files = storage.get_latest_files(data_dir)
    files = [f for f in all_files if "operacoes-do-tesouro-direto-" in f.name]

    if not files:
        print("No operations file found.")
        return

    print(f"Loading {len(files)} operations files for evolution...")
    all_data = []
    for f in files:
        print(f"    Reading {f.name}...")
        df = reader.read_operations(f)
        all_data.append(df)

    if all_data:
        full_data = pl.concat(all_data)
        print("  Plotting operations by type (all history)...")
        chart = plot.plot_operations(full_data, by_type=True)
        save_plot(chart, "operations_evolution_by_type_history.html")


def run_sales(data_dir: Path):
    f = storage.get_latest_file(data_dir, "vendas-do-tesouro-direto*.csv")
    if not f:
        print("No sales file found.")
        return

    print(f"Loading sales from {f.name}...")
    data = reader.read_sales(f)

    print("  Plotting sales by bond type...")
    chart = plot.plot_sales(data, by_bond_type=True)
    save_plot(chart, "sales_evolution_by_type.html")


def run_buybacks(data_dir: Path):
    f = storage.get_latest_file(data_dir, "recompras-do-tesouro-direto*.csv")
    if not f:
        print("No buybacks file found.")
        return

    print(f"Loading buybacks from {f.name}...")
    data = reader.read_buybacks(f)

    print("  Plotting buybacks by bond type...")
    chart = plot.plot_buybacks(data, by_bond_type=True)
    save_plot(chart, "buybacks_evolution_by_type.html")


def run_maturities(data_dir: Path):
    f = storage.get_latest_file(data_dir, "vencimentos-do-tesouro-direto*.csv")
    if not f:
        print("No maturities file found.")
        return

    print(f"Loading maturities from {f.name}...")
    data = reader.read_maturities(f)

    print("  Plotting maturities by bond type...")
    chart = plot.plot_maturities(data, by_bond_type=True)
    save_plot(chart, "maturities_evolution_by_type.html")


def run_interest_coupons(data_dir: Path):
    f = storage.get_latest_file(
        data_dir, "pagamento-de-cupom-de-juros-do-tesouro-direto*.csv"
    )
    if not f:
        print("No interest coupons file found.")
        return

    print(f"Loading interest coupons from {f.name}...")
    data = reader.read_interest_coupons(f)

    print("  Plotting interest coupons by bond type...")
    chart = plot.plot_interest_coupons(data, by_bond_type=True)
    save_plot(chart, "interest_coupons_evolution_by_type.html")


def main():
    parser = argparse.ArgumentParser(
        description="Generate plots for Tesouro Direto data"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="~/data/tddata",
        help="Directory containing the data files (default: ~/data/tddata)",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser()

    print("Starting plot generation...")
    run_prices(data_dir)
    run_stock(data_dir)
    run_investors(data_dir)
    run_operations(data_dir)
    run_sales(data_dir)
    run_buybacks(data_dir)
    run_maturities(data_dir)
    run_interest_coupons(data_dir)
    print("Done!")


if __name__ == "__main__":
    main()
