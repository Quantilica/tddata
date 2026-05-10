"""Functions to download Tesouro Direto's historical data"""

import asyncio
from pathlib import Path

import quantilica_core.metadata as core_meta
from quantilica_core.exceptions import FetchError
from quantilica_core.http import BROWSER_HEADERS, AsyncHttpClient
from quantilica_core.logging import log_step
from tqdm import tqdm

from . import logger
from .constants import CKAN_API_URL
from .storage import DataRepository

SOURCE_ID = "tesouro-direto"
CATALOG_DATASET_ID = "tesouro-direto-venda"

client = AsyncHttpClient(timeout=60.0, headers=BROWSER_HEADERS)


async def get_dataset_resources(dataset_id: str) -> list[dict]:
    """Fetch resources metadata from CKAN dataset asynchronously."""
    params = {"id": dataset_id}
    data = await client.get_json(CKAN_API_URL, params=params)
    if not data["success"]:
        raise FetchError(f"CKAN API failed: {data.get('error')}")
    return data["result"]["resources"]


async def get_download_info(dest_dir: Path, dataset_id: str) -> list[dict]:
    """Describe what ``download(dest_dir, dataset_id)`` would do (no IO)."""
    repo = DataRepository(dest_dir)

    try:
        resources = await get_dataset_resources(dataset_id)
    except Exception as e:
        raise FetchError(
            f"Error fetching resources for {dataset_id}: {e}"
        ) from e

    info_list = []
    for resource in resources:
        if resource.get("format", "").upper() != "CSV":
            continue

        url = resource["url"]
        last_modified_str = (
            resource.get("last_modified") or resource.get("created")
        )
        filename = repo.generate_filename(resource["name"], last_modified_str)
        dest_filepath = repo.file_path(dataset_id, filename)

        slug = filename.split("@")[0]
        latest_file = repo.get_latest_file(dataset_id, f"{slug}*.csv")

        try:
            file_size = int(resource.get("size") or 0)
        except (ValueError, TypeError):
            file_size = 0

        would_download = True
        if (
            latest_file
            and file_size
            and latest_file.stat().st_size == file_size
        ):
            would_download = False

        info_list.append(
            {
                "resource_name": resource.get("name", ""),
                "url": url,
                "filename": filename,
                "destination": str(dest_filepath),
                "size": file_size,
                "last_modified": last_modified_str,
                "format": resource.get("format", ""),
                "would_download": would_download,
                "latest_local": str(latest_file) if latest_file else None,
            }
        )

    return info_list


def _expected_size(resource: dict) -> int:
    """Best-effort integer size from CKAN resource metadata."""
    try:
        return int(resource.get("size") or 0)
    except (ValueError, TypeError):
        return 0


async def download_resource(
    repo: DataRepository,
    dataset_id: str,
    resource: dict,
    semaphore: asyncio.Semaphore,
) -> dict | None:
    """Download a single resource asynchronously with a semaphore.

    Skips download when an existing local file with the same slug has a
    matching upstream size (CKAN sometimes republishes identical content
    under a new ``last_modified`` timestamp).
    """
    url = resource["url"]
    last_modified_str = (
        resource.get("last_modified") or resource.get("created")
    )
    filename = repo.generate_filename(resource["name"], last_modified_str)
    dest_filepath = repo.file_path(dataset_id, filename)

    expected_size = _expected_size(resource)
    if expected_size > 0:
        slug = filename.split("@")[0]
        latest_file = repo.get_latest_file(dataset_id, f"{slug}*.csv")
        if latest_file and latest_file.stat().st_size == expected_size:
            logger.debug(
                f"Skipping {filename}: matching local copy {latest_file.name}"
            )
            return None

    desc = f"Downloading {filename[:30]}..."
    pbar = tqdm(
        total=expected_size or None,
        unit="B",
        unit_scale=True,
        desc=desc,
        leave=False,
    )
    last_seen = 0

    def _on_progress(downloaded: int, total: int) -> None:
        nonlocal last_seen
        if total and pbar.total != total:
            pbar.total = total
        pbar.update(downloaded - last_seen)
        last_seen = downloaded

    try:
        async with semaphore:
            await client.download_with_manifest(
                url,
                dest_filepath,
                source_id=SOURCE_ID,
                dataset_id=dataset_id,
                producer="tesouro-direto-fetcher",
                params=None,
                progress=_on_progress,
            )
    except Exception as exc:
        logger.error(f"Failed to download {url}: {exc}")
        if dest_filepath.exists():
            try:
                dest_filepath.unlink()
            except OSError:
                pass
        return None
    finally:
        pbar.close()

    return {
        "url": url,
        "filename": filename,
        "destination": dest_filepath,
        "file_size": dest_filepath.stat().st_size,
    }


async def download(
    dest_dir: Path,
    dataset_id: str,
    max_concurrency: int = 3,
) -> list[dict]:
    """Download data files concurrently."""
    repo = DataRepository(dest_dir)
    semaphore = asyncio.Semaphore(max_concurrency)

    with log_step(logger, "download-dataset", dataset_id=dataset_id):
        logger.info(f"Fetching metadata for {dataset_id}...")
        try:
            resources = await get_dataset_resources(dataset_id)
        except Exception as e:
            logger.error(f"Error fetching resources for {dataset_id}: {e}")
            return []

        tasks = [
            download_resource(repo, dataset_id, resource, semaphore)
            for resource in resources
            if resource.get("format", "").upper() == "CSV"
        ]

        if not tasks:
            logger.info("No CSV resources found.")
            return []

        logger.info(f"Found {len(tasks)} files. Starting download...")
        results = await asyncio.gather(*tasks)

    downloaded = [r for r in results if r is not None]
    logger.info(f"Successfully downloaded {len(downloaded)} files.")
    return downloaded


def generate_catalog(
    downloaded_files: list[dict],
) -> core_meta.MetadataCatalog:
    """Build a validated MetadataCatalog from Tesouro Direto downloads."""
    source = core_meta.Source(
        id=SOURCE_ID,
        name="Tesouro Direto",
        homepage_url="https://www.tesourodireto.com.br",
    )
    dataset = core_meta.Dataset(
        id=CATALOG_DATASET_ID,
        source_id=SOURCE_ID,
        name="Dados Históricos do Tesouro Direto",
    )
    resources = [
        core_meta.Resource(
            id=file["filename"].replace(".", "_").replace("@", "_"),
            dataset_id=CATALOG_DATASET_ID,
            name=file["filename"],
            url=file["url"],
            format="csv",
            path=str(file["destination"].absolute()),
            metadata={"size": file["file_size"]},
        )
        for file in downloaded_files
    ]
    return core_meta.build_simple_catalog(source, dataset, resources)
