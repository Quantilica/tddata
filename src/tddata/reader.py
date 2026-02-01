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


"""Functions to read Tesouro Direto's data files.

This module provides functions to parse raw CSV files downloaded from the
Tesouro Transparente API into clean, analyst-friendly pandas DataFrames.
It handles column renaming (Portuguese to English), type conversion,
and data normalization using the schema defined in `constants.py`.

The DataFrames returned by these functions use standardized column names
defined in the `Column` enum.
"""

from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Union

import pandas as pd

from .constants import (
    AccountStatus,
    Channel,
    Gender,
    TradedLast12Months,
    normalize_bond_type,
)
from .constants import Column as C


def _read_and_process_csv(
    filepath: Path,
    column_mapping: Dict[str, str],
    date_columns: Optional[List[str]] = None,
    dtype_mapping: Optional[Dict[str, str]] = None,
    post_process_func: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
    chunksize: Optional[int] = None,
) -> Union[pd.DataFrame, Iterator[pd.DataFrame]]:
    """Generic function to read and process a CSV file."""
    data = pd.read_csv(
        filepath,
        sep=";",
        decimal=",",
        parse_dates=date_columns,
        dayfirst=True,
        chunksize=chunksize,
    )

    def _process(df: pd.DataFrame) -> pd.DataFrame:
        df = df.rename(columns=column_mapping)
        if C.BOND_TYPE.value in df.columns:
            df[C.BOND_TYPE.value] = df[C.BOND_TYPE.value].apply(normalize_bond_type)
        if dtype_mapping:
            df = df.astype(dtype_mapping)
        if post_process_func:
            df = post_process_func(df)
        return df

    if chunksize is None:
        return _process(data)
    return (_process(chunk) for chunk in data)


def read_prices(
    filepath: Path, chunksize: Optional[int] = None
) -> Union[pd.DataFrame, Iterator[pd.DataFrame]]:
    """Read bond prices and rates (Taxas e Preços dos Títulos)."""
    column_mapping = {
        "Data Base": C.REFERENCE_DATE.value,
        "Tipo Titulo": C.BOND_TYPE.value,
        "Data Vencimento": C.MATURITY_DATE.value,
        "Taxa Compra Manha": C.BUY_YIELD.value,
        "Taxa Venda Manha": C.SELL_YIELD.value,
        "PU Compra Manha": C.BUY_PRICE.value,
        "PU Venda Manha": C.SELL_PRICE.value,
        "PU Base Manha": C.BASE_PRICE.value,
    }
    return _read_and_process_csv(
        filepath,
        column_mapping,
        date_columns=["Data Vencimento", "Data Base"],
        chunksize=chunksize,
    )



def read_stock(
    filepath: Path, chunksize: Optional[int] = None
) -> Union[pd.DataFrame, Iterator[pd.DataFrame]]:
    """Read bond stock (Estoque)."""
    column_mapping = {
        "Tipo Titulo": C.BOND_TYPE.value,
        "Vencimento do Titulo": C.MATURITY_DATE.value,
        "Mes Estoque": C.STOCK_MONTH.value,
        "PU": C.UNIT_PRICE.value,
        "Quantidade": C.QUANTITY.value,
        "Valor Estoque": C.STOCK_VALUE.value,
    }

    def post_process(df: pd.DataFrame) -> pd.DataFrame:
        df[C.MATURITY_DATE.value] = pd.to_datetime(
            df[C.MATURITY_DATE.value], dayfirst=True
        )
        df[C.STOCK_MONTH.value] = pd.to_datetime(df[C.STOCK_MONTH.value], format="%m/%Y")
        return df

    return _read_and_process_csv(
        filepath,
        column_mapping,
        post_process_func=post_process,
        chunksize=chunksize,
    )


def read_investors(
    filepath: Path, chunksize: Optional[int] = None
) -> Union[pd.DataFrame, Iterator[pd.DataFrame]]:
    """Read investors data (Investidores)."""
    column_mapping = {
        "Codigo do Investidor": C.INVESTOR_ID.value,
        "Data de Adesao": C.JOIN_DATE.value,
        "Estado Civil": C.MARITAL_STATUS.value,
        "Genero": C.GENDER.value,
        "Profissao": C.PROFESSION.value,
        "Idade": C.AGE.value,
        "UF do Investidor": C.STATE.value,
        "Cidade do Investidor": C.CITY.value,
        "Pais do Investidor": C.COUNTRY.value,
        "Situacao da Conta": C.ACCOUNT_STATUS.value,
        "Operou 12 Meses": C.TRADED_LAST_12_MONTHS.value,
    }
    dtype_mapping = {
        C.MARITAL_STATUS.value: "category",
        C.PROFESSION.value: "category",
        C.STATE.value: "category",
        C.CITY.value: "category",
        C.COUNTRY.value: "category",
    }

    def post_process(df: pd.DataFrame) -> pd.DataFrame:
        gender_map = {e.value: e.value for e in Gender}
        df[C.GENDER.value] = df[C.GENDER.value].map(gender_map).astype("category")
        status_map = {e.value: e.value for e in AccountStatus}
        df[C.ACCOUNT_STATUS.value] = (
            df[C.ACCOUNT_STATUS.value].map(status_map).astype("category")
        )
        traded_map = {e.value: e.value for e in TradedLast12Months}
        df[C.TRADED_LAST_12_MONTHS.value] = (
            df[C.TRADED_LAST_12_MONTHS.value].map(traded_map).astype("category")
        )
        return df

    return _read_and_process_csv(
        filepath,
        column_mapping,
        date_columns=["Data de Adesao"],
        dtype_mapping=dtype_mapping,
        post_process_func=post_process,
        chunksize=chunksize,
    )


def read_operations(
    filepath: Path, chunksize: Optional[int] = None
) -> Union[pd.DataFrame, Iterator[pd.DataFrame]]:
    """Read operations data (Operações)."""
    column_mapping = {
        "Codigo do Investidor": C.INVESTOR_ID.value,
        "Data da Operacao": C.OPERATION_DATE.value,
        "Tipo Titulo": C.BOND_TYPE.value,
        "Vencimento do Titulo": C.MATURITY_DATE.value,
        "Quantidade": C.QUANTITY.value,
        "Valor do Titulo": C.BOND_VALUE.value,
        "Valor da Operacao": C.OPERATION_VALUE.value,
        "Tipo da Operacao": C.OPERATION_TYPE.value,
        "Canal da Operacao": C.CHANNEL.value,
    }

    def post_process(df: pd.DataFrame) -> pd.DataFrame:
        df[C.OPERATION_DATE.value] = pd.to_datetime(df[C.OPERATION_DATE.value])
        df[C.MATURITY_DATE.value] = pd.to_datetime(df[C.MATURITY_DATE.value])
        channel_map = {e.value: e.value for e in Channel}
        df[C.CHANNEL.value] = df[C.CHANNEL.value].map(channel_map).astype("category")
        df[C.BOND_TYPE.value] = df[C.BOND_TYPE.value].astype("category")
        return df

    return _read_and_process_csv(
        filepath,
        column_mapping,
        date_columns=["Data da Operacao", "Vencimento do Titulo"],
        post_process_func=post_process,
        chunksize=chunksize,
    )


def read_sales(
    filepath: Path, chunksize: Optional[int] = None
) -> Union[pd.DataFrame, Iterator[pd.DataFrame]]:
    """Read sales data (Vendas)."""
    column_mapping = {
        "Tipo Titulo": C.BOND_TYPE.value,
        "Vencimento do Titulo": C.MATURITY_DATE.value,
        "Data Venda": C.SALE_DATE.value,
        "PU": C.UNIT_PRICE.value,
        "Quantidade": C.QUANTITY.value,
        "Valor": C.VALUE.value,
    }
    return _read_and_process_csv(
        filepath,
        column_mapping,
        date_columns=["Vencimento do Titulo", "Data Venda"],
        chunksize=chunksize,
    )


def read_buybacks(
    filepath: Path, chunksize: Optional[int] = None
) -> Union[pd.DataFrame, Iterator[pd.DataFrame]]:
    """Read buybacks data (Resgates)."""
    column_mapping = {
        "Tipo Titulo": C.BOND_TYPE.value,
        "Vencimento do Titulo": C.MATURITY_DATE.value,
        "Data Resgate": C.BUYBACK_DATE.value,
        "Quantidade": C.QUANTITY.value,
        "Valor": C.VALUE.value,
    }
    return _read_and_process_csv(
        filepath,
        column_mapping,
        date_columns=["Vencimento do Titulo", "Data Resgate"],
        chunksize=chunksize,
    )


def read_maturities(
    filepath: Path, chunksize: Optional[int] = None
) -> Union[pd.DataFrame, Iterator[pd.DataFrame]]:
    """Read maturities data (Vencimentos)."""
    column_mapping = {
        "Tipo Titulo": C.BOND_TYPE.value,
        "Vencimento do Titulo": C.MATURITY_DATE.value,
        "Data Resgate": C.BUYBACK_DATE.value,
        "PU": C.UNIT_PRICE.value,
        "Quantidade": C.QUANTITY.value,
        "Valor": C.VALUE.value,
    }
    return _read_and_process_csv(
        filepath,
        column_mapping,
        date_columns=["Vencimento do Titulo", "Data Resgate"],
        chunksize=chunksize,
    )


def read_interest_coupons(
    filepath: Path, chunksize: Optional[int] = None
) -> Union[pd.DataFrame, Iterator[pd.DataFrame]]:
    """Read interest coupons data (Pagamento de Cupom de Juros).

    Parses the history of interest coupon payments.
    This file shares the same structure as the maturities file.

    Args:
        filepath: Path to the CSV file.
        chunksize: Number of lines to read from the CSV file at a time.

    Returns:
        pd.DataFrame or Iterator[pd.DataFrame]: DataFrame with columns similar to `read_maturities`.
    """
    return read_maturities(filepath, chunksize=chunksize)
