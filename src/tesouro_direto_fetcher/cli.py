"""Command-line interface for tesouro-direto-fetcher."""

import argparse
import asyncio
import logging
from pathlib import Path

from quantilica_core.logging import configure_cli_logging

from . import __version__, downloader, logger
from .constants import (
    DATASET_BUYBACKS,
    DATASET_INVESTORS,
    DATASET_MINT_STOCK,
    DATASET_OPERATIONS,
    DATASET_PRICES_RATES,
    DATASET_SALES,
)
from .storage import DataRepository

_DEFAULT_OUTPUT = Path("/data/tesouro-direto")

DATASET_MAP = {
    "prices": DATASET_PRICES_RATES,
    "operations": DATASET_OPERATIONS,
    "investors": DATASET_INVESTORS,
    "stock": DATASET_MINT_STOCK,
    "buybacks": DATASET_BUYBACKS,
    "sales": DATASET_SALES,
}
DATASET_CHOICES = [*DATASET_MAP, "all"]


def _resolve_dataset_ids(name: str) -> list[str]:
    if name == "all":
        return list(DATASET_MAP.values())
    return [DATASET_MAP[name]]


async def _run_download(args, show_progress: bool = True):
    for dataset_id in _resolve_dataset_ids(args.dataset):
        await downloader.download(
            args.output, dataset_id=dataset_id, show_progress=show_progress
        )


def _print_info_list(info_list: list[dict]) -> tuple[int, int]:
    """Print one info report; return (total_size, would_download_count)."""
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
        flag = "Yes" if info["would_download"] else "No (already up-to-date)"
        print(f"  Would Download: {flag}")
        if info["latest_local"]:
            print(f"  Latest Local: {info['latest_local']}")

        if info["size"]:
            total_size += info["size"]
        if info["would_download"]:
            would_download_count += 1

    print("\n" + "=" * 80)
    print(f"Total resources: {len(info_list)}")
    print(f"Would download: {would_download_count}")
    mb = total_size / (1024 * 1024)
    print(f"Total size: {total_size:,} bytes ({mb:.2f} MB)")
    return total_size, would_download_count


async def _run_dry_run(args):
    logger.info(f"Fetching download info for {args.dataset}...")

    if args.dataset == "all":
        grand_total_size = 0
        grand_would_download = 0
        grand_count = 0

        for ds_name in DATASET_MAP:
            ds_id = DATASET_MAP[ds_name]
            print(f"\nDataset: {ds_name}")
            info_list = await downloader.get_download_info(
                args.output, dataset_id=ds_id
            )
            total_size, would_download = _print_info_list(info_list)
            grand_total_size += total_size
            grand_would_download += would_download
            grand_count += len(info_list)

        print("\n" + "#" * 80)
        print(f"Grand total resources: {grand_count}")
        print(f"Grand would download: {grand_would_download}")
        mb = grand_total_size / (1024 * 1024)
        print(
            f"Grand total size: {grand_total_size:,} bytes ({mb:.2f} MB)"
        )
        return

    dataset_id = DATASET_MAP[args.dataset]
    info_list = await downloader.get_download_info(
        args.output, dataset_id=dataset_id
    )
    _print_info_list(info_list)


def cmd_sync(args) -> None:
    if args.dry_run:
        try:
            asyncio.run(_run_dry_run(args))
        except KeyboardInterrupt:
            logger.warning("Cancelado.")
        except Exception as exc:
            logger.error(f"Error fetching download info: {exc}")
        return

    try:
        asyncio.run(_run_download(args, show_progress=not args.verbose))
    except KeyboardInterrupt:
        logger.warning("Download cancelled.")


def cmd_convert(args) -> int:
    try:
        from . import converter
    except ImportError:
        logger.error("Convert feature requires analysis extras.")
        logger.error(
            "Install with: pip install tesouro-direto-fetcher[analysis]"
        )
        return 1

    data_dir: Path = args.data_dir
    if not data_dir.is_dir():
        logger.error(f"Directory '{data_dir}' does not exist.")
        return 1

    repo = DataRepository(data_dir)
    datasets = repo.list_datasets()
    if not datasets:
        logger.warning(f"No datasets found under '{data_dir}'.")
        return 0

    converted = 0
    failed = 0
    for dataset_id in datasets:
        latest_files = repo.get_all_latest_files(dataset_id)
        if not latest_files:
            continue
        logger.info(
            f"Converting {len(latest_files)} files from {dataset_id}..."
        )
        for fp in latest_files:
            try:
                output_path = converter.convert_to_parquet(fp)
                logger.info(f"  {fp.name} -> {output_path.name}")
                converted += 1
            except Exception as exc:
                logger.error(f"Error converting {fp.name}: {exc}")
                failed += 1

    logger.info(f"Converted {converted} files ({failed} failures).")
    return 0 if failed == 0 else 1


def cmd_pipeline(args) -> int:
    logger.info("=== Passo 1/2: sincronização ===")
    try:
        asyncio.run(_run_download(args, show_progress=not args.verbose))
    except KeyboardInterrupt:
        logger.warning("Download cancelled.")
        return 1
    logger.info("=== Passo 2/2: conversão ===")
    args.data_dir = args.output
    return cmd_convert(args)


def set_parser():
    parser = argparse.ArgumentParser(
        prog="tesouro-direto-fetcher",
        description="Tesouro Direto Data Downloader & Converter",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Exibir logs detalhados em vez de barra de progresso",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # sync
    sync_parser = subparsers.add_parser(
        "sync", help="Sincronizar datasets do Tesouro Direto"
    )
    sync_parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default=_DEFAULT_OUTPUT,
        type=Path,
        help="Output directory (default: /data/tesouro-direto)",
    )
    sync_parser.add_argument(
        "--dataset",
        choices=DATASET_CHOICES,
        default="all",
        help="Dataset to download (default: all)",
    )
    sync_parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=False,
        help="List files that would be downloaded without downloading them",
    )
    sync_parser.set_defaults(func=cmd_sync)

    # convert (only available with analysis extras)
    try:
        from . import converter  # noqa: F401

        convert_parser = subparsers.add_parser(
            "convert", help="Convert all latest CSVs to Parquet"
        )
        convert_parser.add_argument(
            "data_dir",
            type=Path,
            help="Data directory (root of <dataset_id>/ tree)",
        )
        convert_parser.set_defaults(func=cmd_convert)

        pipeline_parser = subparsers.add_parser(
            "pipeline", help="Pipeline completo (sync -> convert)"
        )
        pipeline_parser.add_argument(
            "-o",
            "--output",
            dest="output",
            default=_DEFAULT_OUTPUT,
            type=Path,
            help="Output directory (default: /data/tesouro-direto)",
        )
        pipeline_parser.add_argument(
            "--dataset",
            choices=DATASET_CHOICES,
            default="all",
            help="Dataset to download (default: all)",
        )
        pipeline_parser.set_defaults(func=cmd_pipeline)
    except ImportError:
        pass

    return parser


def main():
    parser = set_parser()
    args = parser.parse_args()
    configure_cli_logging(verbose=args.verbose)

    if not args.verbose:
        logging.getLogger("tesouro_direto_fetcher").setLevel(logging.WARNING)

    return args.func(args)


if __name__ == "__main__":
    main()
