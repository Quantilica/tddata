# tddata - Download, Analyze & Plot Brazilian Tesouro Direto's Data (CKAN API)

![GitHub](https://img.shields.io/github/license/Quantilica/tddata?style=flat-square)
[![Tests](https://github.com/Quantilica/tddata/actions/workflows/run-tests.yml/badge.svg)](https://github.com/Quantilica/tddata/actions/workflows/run-tests.yml)

**tddata** is a powerful Python package designed to simplify the process of downloading, reading, and visualizing historical data from Brazil's Tesouro Direto program. It leverages the official CKAN API (Tesouro Transparente) to fetch the most up-to-date datasets.

## Features

*   **Automated Downloads**: Easily fetch datasets directly from the Government's CKAN API.
*   **Specialized Readers**: Dedicated functions to read and parse CSVs for Prices, Stock, Investors, Operations, Sales, Buybacks/Redemptions, and more.
*   **Standardized Data**: All DataFrames come with consistent, analyst-friendly column names defined in a robust schema.
*   **Visualization**: Built-in plotting module that returns **Altair** charts for time-series, distribution, and demographic analysis (no Matplotlib/Seaborn needed).
*   **CLI**: A convenient command-line interface for quick data fetching.

## 1. Installation

This package is available via GitHub. You can install it using `pip`:

**Download only (minimal dependencies):**
```shell
pip install "git+https://github.com/Quantilica/tddata#egg=tddata"
```

**Full installation with reading, analysis and plotting features:**
```shell
pip install "git+https://github.com/Quantilica/tddata#egg=tddata[analysis]"
```

The minimal installation includes only `httpx` and `tqdm` for downloading data. The `[analysis]` extras add `polars` (CSV parsing, analytics) and `altair[save]` (charts).

## 2. Usage

### 2.1 The `tddata` CLI

The package includes a comprehensive Command-Line Interface (CLI) for downloading, inspecting, and converting Tesouro Direto data. See [CLI.md](docs/CLI.md) for complete documentation including all commands, options, and examples.

### 2.2 The `tddata` Python Package

You can use `tddata` as a library in your Python scripts or Jupyter Notebooks.

#### Downloading Data

`downloader.download` is asynchronous; wrap it with `asyncio.run` (or `await` it inside another coroutine).

```python
import asyncio
from pathlib import Path
from tddata import downloader

# Download 'prices' dataset to ./data folder, max 3 concurrent connections
asyncio.run(
    downloader.download(
        dest_dir=Path("./data"),
        dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
        max_concurrency=3,
    )
)

# Inspect what would be downloaded without writing anything
infos = asyncio.run(
    downloader.get_download_info(
        dest_dir=Path("./data"),
        dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
    )
)
```

#### Reading Data

The `tddata.reader` module provides specialized functions for each dataset type.

```python
from pathlib import Path
from tddata import reader

# Read Prices/Rates
df_prices = reader.read_prices(
    Path(
        ".", "data",
        "taxas-dos-titulos-ofertados-pelo-tesouro-direto@20251230T102010.csv"
    )
)

# Read Stock
df_stock = reader.read_stock(
    Path(
        ".", "data",
        "estoque-do-tesouro-direto@20251201T102018.csv"
    )
)

# Read Investors
df_investors = reader.read_investors(
    Path(
        ".", "data",
        "investidores-do-tesouro-direto-de-2024@20251205T131939.csv"
    )
)
```

#### Plotting Data

The `tddata.plot` module returns Altair charts (`alt.Chart`). Display them in a notebook with `chart.display()` or save to disk with `chart.save("name.png")` / `.html` / `.svg`.

```python
from tddata import plot
from tddata.constants import Column

# 1. Plot Price History
chart_prices = plot.plot_prices(
    df_prices,
    bond_type="Tesouro Selic",
    variable=Column.BASE_PRICE.value,
)
chart_prices.save("prices_tesouro-selic.html")

# 2. Plot Stock Evolution by Bond Type
plot.plot_stock(df_stock, by_bond_type=True).save("stock_evolution_by_type.html")

# 3. Plot Investor Demographics (Population Pyramid)
plot.plot_investors_population_pyramid(df_investors).save("investors_pyramid.html")

# 4. Plot Investor Demographics (e.g., Profession bar chart)
plot.plot_investors_demographics(
    df_investors,
    column=Column.PROFESSION.value,
).save("investors_profession.html")
```

Other plotting helpers exposed by `tddata.plot`: `plot_investors_evolution`, `plot_operations`, `plot_sales`, `plot_buybacks`, `plot_maturities`, `plot_interest_coupons`.

![Price History](./plots/prices_tesouro-selic_base_price.png)

![Stock Evolution](./plots/stock_evolution_by_type.png)

![Investor Demographics by Age & Gender](./plots/investors_population_pyramid.png)

![Investor Demographics by Profession](./plots/investors_demographics_profession.png)

See more visualizations in the [PLOTS.md](docs/PLOTS.md) file.

## 3. Data Source

All data is fetched from the official **Tesouro Transparente** via their [CKAN API](https://www.tesourotransparente.gov.br/ckan/).

*   **Prices**: `taxas-dos-titulos-ofertados-pelo-tesouro-direto`
*   **Stock**: `estoque-do-tesouro-direto`
*   **Investors**: `investidores-do-tesouro-direto`
*   **Operations**: `operacoes-do-tesouro-direto`
*   **Sales**: `vendas-do-tesouro-direto`
*   **Buybacks**: `recompras-do-tesouro-direto`

## 4. License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).
