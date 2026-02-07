# Copilot Instructions for tddata

## Project Overview
**tddata** is a Python library for downloading, parsing, and visualizing Brazilian Tesouro Direto (government bonds) data from the official CKAN API. The project follows a clean separation: downloader → reader → plotter.

## Architecture & Key Components

### Data Flow
1. **Download** (`downloader.py`): Fetches CSV files from Tesouro Transparente CKAN API
2. **Read** (`reader.py`): Parses raw CSVs into analyst-friendly Polars DataFrames with standardized columns
3. **Plot** (`plot.py`): Generates matplotlib/seaborn visualizations

### Column Name Convention (CRITICAL)
- **Always use `Column` enum** from `constants.py` for column references
- Original CSV columns (Portuguese, mixed case) are renamed to snake_case English equivalents
- Example: `"Data Base"` → `Column.REFERENCE_DATE.value` → `"reference_date"`
- This enum is the single source of truth for all column names across readers/plotters

### Reader Functions Pattern
All `read_*()` functions in `reader.py`:
- Accept `Path` argument (not string)
- Use `;` separator and `,` decimal for Brazilian CSV format
- Parse dates with `dayfirst=True`
- Return DataFrame with `Column` enum-based names
- Example: `read_prices()`, `read_stock()`, `read_investors()`

### Plotting Conventions
- All plot functions return matplotlib figure objects (not show/save)
- Use `_plot_value_over_time()` helper for time-series charts by bond type
- **Legend titles**: When plotting by bond type, always set `legend_title="Bond Type"`
- Use `human_format()` ticker for large currency/count values (K, M, B suffixes)
- Add footer with `_add_footer(fig)` for data attribution
- Monthly aggregation pattern: `df["month"] = df[date_col].dt.to_period("M").dt.to_timestamp()`

### File Naming Patterns
- Downloaded files: `<slugified-name>@<ISO-timestamp>.csv` (e.g., `taxas-dos-titulos-ofertados-pelo-tesouro-direto@20251230T102010.csv`)
- Plot files: Follow pattern in `make_plots.py` (e.g., `prices_tesouro-selic_base_price.png`, `stock_evolution_by_type.png`)

## Development Workflow

This project uses **uv** for package and virtual environment management. Do not use `pip` or `venv` directly unless necessary.

### Running & Testing
- **Install dependencies**: `uv sync` or `uv pip install -e .`
- **Generate all plots**: `uv run python make_plots.py` (requires data in `~/data/tddata/`)
- **Run tests**: `uv run python -m unittest discover -s tests -p "test_*.py"`
- **CLI usage**: `uv run tddata [prices|stock|investors|operations|sales|buybacks] -o ./data`

### Type Hints
- Use `Optional[str]` for nullable string parameters (not `str = None`)
- Import from `typing` module when needed

### Dependencies
Core: `Polars`, `Altair`, `httpx`, `tqdm`
No heavy frameworks - keep it lightweight and data-focused.

## Common Patterns

### Adding a new dataset type:
1. Add dataset constant to `constants.py` (e.g., `DATASET_MATURITIES`)
2. Create `read_maturities()` in `reader.py` following the CSV parsing pattern
3. Add corresponding plot function in `plot.py`
4. Update CLI `dataset_map` in `cli.py`
5. Generate sample plot in `make_plots.py`

### Extending visualization:
- New by-type charts should use `_plot_value_over_time()` with `legend_title="Bond Type"`
- For stock/evolution plots, ensure legend title is explicitly set via `ax.legend(title="Bond Type")`
- Always aggregate monthly for readability on time-series charts

## Critical Files to Reference
- `constants.py`: Column enums, bond types, dataset IDs - the schema authority
- `make_plots.py`: Complete example of download → read → plot workflow
- `plot.py`: `_plot_value_over_time()` - canonical pattern for time-series by category
- `reader.py`: Brazilian CSV parsing conventions (separators, decimals, dates)
- `storage.py`: Utilities for file storage and naming conventions
