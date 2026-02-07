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

from pathlib import Path
from typing import Callable, Optional

from . import reader


def convert_to_parquet(
    csv_path: Path, parquet_path: Optional[Path] = None, dataset_type: str = "infer"
) -> Path:
    """Read a raw CSV file using the appropriate reader and save it as Parquet.

    Args:
        csv_path: Path to the source CSV file.
        parquet_path: Path for the output Parquet file. If None, uses the same stem as CSV.
        dataset_type: Type of dataset to select the correct reader.
                      If 'infer', tries to guess based on filename/content.
                      Options: 'prices', 'stock', 'investors', 'operations',
                               'sales', 'buybacks', 'maturities'.

    Returns:
        Path: The path to the created parquet file.
    """
    if parquet_path is None:
        parquet_path = csv_path.with_suffix(".parquet")

    reader_func = _get_reader_function(csv_path, dataset_type)

    # Read the data using the specialized reader (which cleans and types it)
    # Polars DataFrames can be directly written to parquet
    df = reader_func(csv_path)
    df.write_parquet(parquet_path)

    return parquet_path


def _get_reader_function(filepath: Path, dataset_type: str) -> Callable:
    """Determine the appropriate reader function."""

    # Mapping logic
    mapping = {
        "prices": reader.read_prices,
        "stock": reader.read_stock,
        "investors": reader.read_investors,
        "operations": reader.read_operations,
        "sales": reader.read_sales,
        "buybacks": reader.read_buybacks,
        "maturities": reader.read_maturities,
        "interest": reader.read_interest_coupons,
    }

    if dataset_type in mapping:
        return mapping[dataset_type]

    # Inference logic based on filename keywords (naive)
    name = filepath.name.lower()
    if "taxas" in name:
        return reader.read_prices
    elif "estoque" in name:
        return reader.read_stock
    elif "investidores" in name:
        return reader.read_investors
    elif "operacoes" in name:
        return reader.read_operations
    elif "vendas" in name:
        return reader.read_sales
    elif "resgates" in name:
        return reader.read_buybacks
    elif "vencimentos" in name:
        return reader.read_maturities
    elif "cupom" in name:
        return reader.read_interest_coupons

    raise ValueError(f"Could not infer dataset type for {filepath}")
