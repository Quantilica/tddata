# tesouro-direto-fetcher CLI Documentation

## Overview

The `tesouro-direto-fetcher` command-line interface (CLI) provides a convenient way to download, inspect, and convert Brazilian Tesouro Direto data from the official CKAN API. The CLI supports three main operations: downloading datasets, getting download information without downloading, and converting CSV files to Parquet format.

## Installation

The CLI is included with the `tesouro-direto-fetcher` package. Install it using one of the following methods:

**Minimal installation (download only):**
```bash
pip install "git+https://github.com/Quantilica/tesouro-direto-fetcher#egg=tesouro-direto-fetcher"
```

**Full installation (with analysis features):**
```bash
pip install "git+https://github.com/Quantilica/tesouro-direto-fetcher#egg=tesouro-direto-fetcher[analysis]"
```

The `analysis` extras are required for the `convert` command.

## General Usage

```bash
tesouro-direto-fetcher <command> [options]
```

### Available Commands

- `download` - Download datasets from the Tesouro Transparente CKAN API
- `info` - Show information about datasets without downloading
- `convert` - Convert CSV files to Parquet format (requires analysis extras)

### Global Options

- `-h, --help` - Show help message and exit

## Commands

### `download`

Download one or more datasets to a local directory.

**Syntax:**
```bash
tesouro-direto-fetcher download [-o OUTPUT_DIR] [--dataset DATASET]
```

**Options:**

- `-o OUTPUT_DIR, --output OUTPUT_DIR`
  - Output directory for downloaded files
  - Type: Path
  - Default: `data`
  - Example: `-o ./my_data`

- `--dataset DATASET`
  - Dataset to download
  - Choices: `prices`, `operations`, `investors`, `stock`, `buybacks`, `sales`, `all`
  - Default: `prices`
  - When `all` is specified, downloads all available datasets sequentially

**Examples:**

```bash
# Download prices dataset to default data directory
tesouro-direto-fetcher download

# Download prices dataset to custom directory
tesouro-direto-fetcher download -o ./tesouro_data

# Download stock data
tesouro-direto-fetcher download --dataset stock -o ./data

# Download all datasets
tesouro-direto-fetcher download --dataset all -o ./data

# Download operations and investors data
# Note: Use separate commands for multiple specific datasets
tesouro-direto-fetcher download --dataset operations -o ./data
tesouro-direto-fetcher download --dataset investors -o ./data
```

**Output:**
The command will display a progress bar for each file being downloaded. Files are saved with timestamps in their filenames (e.g., `taxas-dos-titulos-ofertados-pelo-tesouro-direto@20251230T102010.csv`).

### `info`

Display information about datasets that would be downloaded, including file sizes, modification dates, and whether files are already up-to-date locally.

**Syntax:**
```bash
tesouro-direto-fetcher info [-o OUTPUT_DIR] [--dataset DATASET]
```

**Options:**

- `-o OUTPUT_DIR, --output OUTPUT_DIR`
  - Output directory to check for existing files
  - Type: Path
  - Default: `data`
  - Example: `-o ./my_data`

- `--dataset DATASET`
  - Dataset to get information about
  - Choices: `prices`, `operations`, `investors`, `stock`, `buybacks`, `sales`, `all`
  - Default: `prices`
  - When `all` is specified, shows information for all datasets

**Examples:**

```bash
# Get info about prices dataset
tesouro-direto-fetcher info --dataset prices

# Get info about all datasets
tesouro-direto-fetcher info --dataset all -o ./data

# Check stock data with custom output directory
tesouro-direto-fetcher info --dataset stock -o ./tesouro_data
```

**Sample Output:**
```
Fetching download info for prices...

Found 1 CSV resources:
================================================================================

Resource: Taxas dos Títulos Ofertados pelo Tesouro Direto
  Filename: taxas-dos-titulos-ofertados-pelo-tesouro-direto@20251230T102010.csv
  Destination: data\taxas-dos-titulos-ofertados-pelo-tesouro-direto@20251230T102010.csv
  Size: 13,788,359 bytes
  Last Modified: 2025-12-30T10:22:12.278476
  Would Download: Yes

================================================================================
Total resources: 1
Would download: 1
Total size: 13,788,359 bytes (13.15 MB)
```

**Output Fields:**

- `Resource`: Name of the dataset resource from CKAN
- `Filename`: Generated filename with timestamp
- `Destination`: Full local path where the file would be saved
- `Size`: File size in bytes (or "Unknown" if not available)
- `Last Modified`: Last modification timestamp from CKAN
- `Would Download`: Whether the file would be downloaded (Yes/No)
- `Latest Local`: Path to the most recent local version (if exists)

### `convert`

Convert CSV files downloaded by tesouro-direto-fetcher to Parquet format for better performance and storage efficiency. This command is only available when the `analysis` optional dependencies are installed.

**Syntax:**
```bash
tesouro-direto-fetcher convert <file> [--type DATASET_TYPE]
```

**Arguments:**

- `file`
  - Path to the CSV file to convert
  - Type: Path
  - Required
  - Example: `data/taxas-dos-titulos-ofertados-pelo-tesouro-direto@20251230T102010.csv`

**Options:**

- `--type DATASET_TYPE`
  - Dataset type for proper column parsing
  - Choices: `prices`, `operations`, `investors`, `stock`, `buybacks`, `sales`, `maturities`, `infer`
  - Default: `infer`
  - When `infer` is used, the type is automatically detected from the filename

**Examples:**

```bash
# Convert a prices CSV file with automatic type detection
tesouro-direto-fetcher convert data/taxas-dos-titulos-ofertados-pelo-tesouro-direto@20251230T102010.csv

# Convert with explicit type specification
tesouro-direto-fetcher convert data/operacoes-do-tesouro-direto@20251201T102018.csv --type operations

# Convert investors data
tesouro-direto-fetcher convert data/investidores-do-tesouro-direto@20251205T131939.csv --type investors
```

**Output:**
The command creates a Parquet file with the same base name as the input CSV but with a `.parquet` extension. For example:
```
Successfully converted to data/taxas-dos-titulos-ofertados-pelo-tesouro-direto@20251230T102010.parquet
```

## Dataset Types

The following dataset types are supported:

- `prices` - Daily price rates for all Tesouro Direto bonds
- `operations` - Individual buy/sell operations by investors
- `investors` - Demographic data about Tesouro Direto investors
- `stock` - Current stock/holdings of Tesouro Direto bonds
- `buybacks` - Bond redemption/buyback operations
- `sales` - Bond sales data
- `maturities` - Bond maturity information (convert command only)

## Error Handling

### Common Errors

**Command not found:**
```
tesouro-direto-fetcher: command not found
```
**Solution:** Ensure `tesouro-direto-fetcher` is installed and available in your PATH, or use `uv run tesouro-direto-fetcher` if using uv.

**Convert command not available:**
```
Error: Convert feature requires analysis extras.
Install with: pip install tesouro-direto-fetcher[analysis]
```
**Solution:** Install with analysis extras: `pip install "git+https://github.com/Quantilica/tesouro-direto-fetcher#egg=tesouro-direto-fetcher[analysis]"`

**Invalid dataset:**
```
usage: tesouro-direto-fetcher download [-o OUTPUT_DIR] [--dataset {prices,operations,investors,stock,buybacks,sales,all}]
tesouro-direto-fetcher download: error: argument --dataset: invalid choice: 'invalid_dataset'
```
**Solution:** Use one of the valid dataset choices listed in the error message.

**File not found (convert command):**
```
Error converting file: [Errno 2] No such file or directory: 'nonexistent.csv'
```
**Solution:** Ensure the CSV file path is correct and the file exists.

**Network errors (download/info commands):**
```
Error fetching download info: Connection timeout
```
**Solution:** Check your internet connection and try again. The Tesouro Transparente API may be temporarily unavailable.

### Exit Codes

- `0` - Success
- `1` - Error (invalid arguments, file not found, network issues, etc.)
- `130` - Interrupted (Ctrl+C)

## Advanced Usage

### Batch Processing

To download multiple specific datasets, run separate commands:

```bash
# Download prices and operations
tesouro-direto-fetcher download --dataset prices -o ./data
tesouro-direto-fetcher download --dataset operations -o ./data

# Or use all for everything
tesouro-direto-fetcher download --dataset all -o ./data
```

### Checking Before Downloading

Always use the `info` command first to see what will be downloaded:

```bash
# Check what's available
tesouro-direto-fetcher info --dataset prices

# Then download if satisfied
tesouro-direto-fetcher download --dataset prices
```

### Converting Multiple Files

Use shell globbing or loops to convert multiple files:

```bash
# Convert all CSV files in data directory
for file in data/*.csv; do
    tesouro-direto-fetcher convert "$file"
done
```

### Integration with Scripts

The CLI can be easily integrated into shell scripts or automation tools:

```bash
#!/bin/bash
# Download latest data and convert to Parquet

DATA_DIR="./tesouro_data"
mkdir -p "$DATA_DIR"

# Download all datasets
tesouro-direto-fetcher download --dataset all -o "$DATA_DIR"

# Convert all CSV files to Parquet
find "$DATA_DIR" -name "*.csv" -exec tesouro-direto-fetcher convert {} \;
```

## See Also

- [README.md](../README.md) - General package documentation
- [download_info.md](download_info.md) - Detailed download info feature documentation
- [examples/download_info_example.py](../examples/download_info_example.py) - Programmatic usage examples
- [Tesouro Transparente CKAN API](https://www.tesourotransparente.gov.br/ckan/) - Official data source