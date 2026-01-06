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
import asyncio
from pathlib import Path

from . import converter, downloader
from .constants import (
    DATASET_BUYBACKS,
    DATASET_INVESTORS,
    DATASET_MINT_STOCK,
    DATASET_OPERATIONS,
    DATASET_PRICES_RATES,
    DATASET_SALES,
)


def set_parser():
    parser = argparse.ArgumentParser(
        description="Tesouro Direto Data Downloader & Converter"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Download command
    download_parser = subparsers.add_parser("download", help="Download datasets")
    download_parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default=Path("data"),
        type=Path,
        help="Output directory",
    )
    download_parser.add_argument(
        "--dataset",
        choices=[
            "prices",
            "operations",
            "investors",
            "stock",
            "buybacks",
            "sales",
            "all",
        ],
        default="prices",
        help="Dataset to download",
    )

    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert CSV to Parquet")
    convert_parser.add_argument(
        "file",
        type=Path,
        help="Path to CSV file to convert",
    )
    convert_parser.add_argument(
        "--type",
        dest="dataset_type",
        default="infer",
        choices=[
            "prices",
            "operations",
            "investors",
            "stock",
            "buybacks",
            "sales",
            "maturities",
            "infer",
        ],
        help="Dataset type (default: infer from filename)",
    )

    return parser


async def run_download(args):
    dataset_map = {
        "prices": DATASET_PRICES_RATES,
        "operations": DATASET_OPERATIONS,
        "investors": DATASET_INVESTORS,
        "stock": DATASET_MINT_STOCK,
        "buybacks": DATASET_BUYBACKS,
        "sales": DATASET_SALES,
    }

    if args.dataset == "all":
        for dataset_id in dataset_map.values():
            # We run sequential dataset downloads to avoid overwhelming,
            # but files within dataset are concurrent.
            # Alternatively, we could gather all, but that's thousands of files.
            # Let's keep dataset level sequential.
            await downloader.download(args.output, dataset_id=dataset_id)
    else:
        await downloader.download(args.output, dataset_id=dataset_map[args.dataset])


def main():
    parser = set_parser()
    args = parser.parse_args()

    if args.command == "download":
        try:
            asyncio.run(run_download(args))
        except KeyboardInterrupt:
            print("\nDownload cancelled.")

    elif args.command == "convert":
        try:
            output_path = converter.convert_to_parquet(
                args.file, dataset_type=args.dataset_type
            )
            print(f"Successfully converted to {output_path}")
        except Exception as e:
            print(f"Error converting file: {e}")
