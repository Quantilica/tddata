# Gemini Code Assistant - Project Guide: tddata

This document provides a guide for the Gemini Code Assistant to understand and interact with the `tddata` project.

## 1. Project Overview

`tddata` is a Python library for downloading, reading, analyzing, and visualizing historical data from the Brazilian "Tesouro Direto" program. It fetches data from the official Tesouro Transparente CKAN API, provides reader functions to parse the data into standardized pandas DataFrames, and includes plotting capabilities for data visualization.

The project is structured into several modules:

- **`downloader.py`**: Handles asynchronous downloading of datasets from the CKAN API.
- **`reader.py`**: Contains specialized functions to read raw CSV files into cleaned and typed pandas DataFrames.
- **`plot.py`**: Provides high-level functions to generate plots from the data using Matplotlib and Seaborn.
- **`analytics.py`**: Includes functions for data aggregation and preparation for plotting.
- **`constants.py`**: Defines all constants, enums (like `BondType`, `OperationType`), and DataFrame column names (`Column` enum). This is the single source of truth for schema definitions.
- **`storage.py`**: Contains utilities for file naming conventions, including slugifying names and handling timestamped versions.
- **`cli.py`**: Implements the command-line interface for downloading data.

## 2. Code Style and Conventions

- **Style**: The project follows PEP 8 style guidelines. Line length is configured to 120 characters in `pyproject.toml`.
- **Typing**: The codebase uses type hints extensively. All new code should include type annotations.
- **Constants and Enums**: All column names, API endpoints, and categorical data mappings are defined in `src/tddata/constants.py`. When working with DataFrame columns or categorical data, always import and use the enums from this file (e.g., `from tddata.constants import Column as C`). This ensures consistency and avoids hardcoded strings.
- **Docstrings**: Functions and modules are documented with docstrings explaining their purpose, arguments, and return values.
- **Linting**: The project uses `ruff` for linting. The configuration is in `pyproject.toml`.

## 3. Package Structure and Key Files

```
.
├── .github/              # CI/CD workflows
│   └── workflows/
│       └── run-tests.yml # GitHub Actions workflow for running tests
├── src/
│   └── tddata/           # Main package source code
│       ├── __init__.py
│       ├── analytics.py  # Data aggregation and preparation logic
│       ├── cli.py        # Command-line interface implementation
│       ├── constants.py  # Central location for all constants and enums
│       ├── converter.py  # CSV to Parquet conversion utility
│       ├── downloader.py # Asynchronous data downloader
│       ├── plot.py       # Plotting functions
│       ├── reader.py     # Functions to read and parse CSV data
│       └── storage.py    # File storage and naming utilities
├── tests/                # Unit tests
│   ├── test_*.py
├── make_plots.py         # Script to generate all plots
├── pyproject.toml        # Project metadata and dependencies
└── README.md             # Project description
```

## 4. Dependencies and Setup

- **Core Dependencies**: `httpx` for HTTP requests and `tqdm` for progress bars.
- **Optional (`analysis`) Dependencies**: `pandas`, `pyarrow`, `seaborn` for data analysis and plotting.
- **Installation**: The project is installed in editable mode. The full installation for development is `pip install -e .[analysis]`. The project uses `uv` for package management. Use `uv add` to add new dependencies. Use `uv run` to run scripts.
- **Testing**: Tests are located in the `tests/` directory and are run using the `unittest` framework. The command to run all tests is `python -m unittest discover -s tests -p "test_*.py"`. The CI pipeline in `.github/workflows/run-tests.yml` shows the full setup and test execution process.

## 5. How to Work with the Codebase

### Adding a new feature

1.  **Understand the existing modules**: Identify which module is the most appropriate for the new feature.
2.  **Follow the conventions**: Adhere to the coding style, use constants and enums from `constants.py`, and add type hints.
3.  **Add tests**: Create a new test file in the `tests/` directory or add new tests to an existing one.
4.  **Update documentation**: If the feature is user-facing, update the `README.md` and any relevant docstrings.

### Fixing a bug

1.  **Identify the root cause**: Use the existing tests or write a new one to reproduce the bug.
2.  **Apply the fix**: Modify the code to fix the bug, ensuring that the changes do not break other parts of the application.
3.  **Run the tests**: Make sure all tests pass after applying the fix.

### Generating plots

The `make_plots.py` script serves as an example of how to use the library to generate all the plots present in the `plots/` directory. It shows how to load data and use the `plot` module.
