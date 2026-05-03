import argparse
import asyncio
from pathlib import Path

from . import downloader
from .constants import (
    DATASET_BUYBACKS,
    DATASET_INVESTORS,
    DATASET_MINT_STOCK,
    DATASET_OPERATIONS,
    DATASET_PRICES_RATES,
    DATASET_SALES,
)


def set_parser():
    parser = argparse.ArgumentParser(description="Tesouro Direto Data Downloader & Converter")
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

    # Info command
    info_parser = subparsers.add_parser("info", help="Show download info without downloading")
    info_parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default=Path("data"),
        type=Path,
        help="Output directory (to check for existing files)",
    )
    info_parser.add_argument(
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
        help="Dataset to get info about",
    )

    # Convert command (only available with analysis extras)
    try:
        from . import converter  # noqa: F401

        convert_parser = subparsers.add_parser("convert", help="Convert all latest CSVs to Parquet")
        convert_parser.add_argument(
            "data_dir",
            type=Path,
            help="Data directory containing CSV files",
        )
    except ImportError:
        pass  # Convert command not available without analysis extras

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


async def run_info(args):
    dataset_map = {
        "prices": DATASET_PRICES_RATES,
        "operations": DATASET_OPERATIONS,
        "investors": DATASET_INVESTORS,
        "stock": DATASET_MINT_STOCK,
        "buybacks": DATASET_BUYBACKS,
        "sales": DATASET_SALES,
    }

    print(f"Fetching download info for {args.dataset}...")

    try:
        # Handle 'all' specially by iterating datasets
        if args.dataset == "all":
            grand_total_size = 0
            grand_would_download = 0
            grand_count = 0

            for ds_name, ds_id in dataset_map.items():
                print(f"\nDataset: {ds_name}")
                info_list = await downloader.get_download_info(args.output, dataset_id=ds_id)

                print(f"\nFound {len(info_list)} CSV resources:")
                print("=" * 80)

                total_size = 0
                would_download_count = 0

                for info in info_list:
                    print(f"\nResource: {info['resource_name']}")
                    print(f"  Filename: {info['filename']}")
                    print(f"  Destination: {info['destination']}")
                    if info["size"]:
                        print(f"  Size: {info['size']:,} bytes")
                    else:
                        print("  Size: Unknown")
                    print(f"  Last Modified: {info['last_modified']}")
                    print(f"  Would Download: {'Yes' if info['would_download'] else 'No (already up-to-date)'}")
                    if info["latest_local"]:
                        print(f"  Latest Local: {info['latest_local']}")

                    if info["size"]:
                        total_size += info["size"]
                    if info["would_download"]:
                        would_download_count += 1

                print("\n" + "=" * 80)
                print(f"Total resources: {len(info_list)}")
                print(f"Would download: {would_download_count}")
                print(f"Total size: {total_size:,} bytes ({total_size / (1024 * 1024):.2f} MB)")

                grand_total_size += total_size
                grand_would_download += would_download_count
                grand_count += len(info_list)

            # Grand totals across datasets
            print("\n" + "#" * 80)
            print(f"Grand total resources: {grand_count}")
            print(f"Grand would download: {grand_would_download}")
            print(f"Grand total size: {grand_total_size:,} bytes ({grand_total_size / (1024 * 1024):.2f} MB)")

        else:
            dataset_id = dataset_map[args.dataset]
            info_list = await downloader.get_download_info(args.output, dataset_id=dataset_id)

            print(f"\nFound {len(info_list)} CSV resources:")
            print("=" * 80)

            total_size = 0
            would_download_count = 0

            for info in info_list:
                print(f"\nResource: {info['resource_name']}")
                print(f"  Filename: {info['filename']}")
                print(f"  Destination: {info['destination']}")
                if info["size"]:
                    print(f"  Size: {info['size']:,} bytes")
                else:
                    print("  Size: Unknown")
                print(f"  Last Modified: {info['last_modified']}")
                print(f"  Would Download: {'Yes' if info['would_download'] else 'No (already up-to-date)'}")
                if info["latest_local"]:
                    print(f"  Latest Local: {info['latest_local']}")

                if info["size"]:
                    total_size += info["size"]
                if info["would_download"]:
                    would_download_count += 1

            print("\n" + "=" * 80)
            print(f"Total resources: {len(info_list)}")
            print(f"Would download: {would_download_count}")
            print(f"Total size: {total_size:,} bytes ({total_size / (1024 * 1024):.2f} MB)")

    except Exception as e:
        print(f"Error fetching download info: {e}")


def main():
    parser = set_parser()
    args = parser.parse_args()

    if args.command == "download":
        try:
            asyncio.run(run_download(args))
        except KeyboardInterrupt:
            print("\nDownload cancelled.")

    elif args.command == "info":
        try:
            asyncio.run(run_info(args))
        except KeyboardInterrupt:
            print("\nInfo cancelled.")

    elif args.command == "convert":
        try:
            from . import converter, storage
        except ImportError:
            print("Error: Convert feature requires analysis extras.")
            print("Install with: pip install tddata[analysis]")
            return

        if not args.data_dir.exists() or not args.data_dir.is_dir():
            print(f"Error: Directory '{args.data_dir}' does not exist or is not a directory.")
            return

        latest_files = storage.get_latest_files(args.data_dir)
        if not latest_files:
            print(f"No CSV files found in '{args.data_dir}'.")
            return

        print(f"Found {len(latest_files)} latest files to convert...")
        for file_path in latest_files:
            try:
                output_path = converter.convert_to_parquet(file_path)
                print(f"Successfully converted {file_path.name} to {output_path.name}")
            except Exception as e:
                print(f"Error converting {file_path.name}: {e}")
