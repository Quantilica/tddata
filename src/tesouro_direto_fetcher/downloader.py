"""Functions to download Tesouro Direto's historical data"""

from pathlib import Path

import quantilica_core.metadata as core_meta
from quantilica_core.exceptions import FetchError
from quantilica_core.fetcher import RemoteResource, download_resources
from quantilica_core.http import BROWSER_HEADERS, AsyncHttpClient
from quantilica_core.logging import log_step
from quantilica_core.progress import batch_progress

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

        slug = filename.partition("@")[0]
        latest_file = repo.get_latest_stamped_file(dataset_id, slug)

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


def _to_remote_resources(
    ckan_resources: list[dict], repo: DataRepository
) -> list[RemoteResource]:
    result = []
    for r in ckan_resources:
        if r.get("format", "").upper() != "CSV":
            continue
        last_modified = r.get("last_modified") or r.get("created")
        filename = repo.generate_filename(r["name"], last_modified)
        try:
            size = int(r.get("size") or 0)
        except (ValueError, TypeError):
            size = 0
        result.append(
            RemoteResource(
                name=r["name"],
                url=r["url"],
                filename=filename,
                size=size,
                format="CSV",
            )
        )
    return result


async def download(
    dest_dir: Path,
    dataset_id: str,
    max_concurrency: int = 3,
    show_progress: bool = True,
) -> list[dict]:
    """Download data files concurrently."""
    repo = DataRepository(dest_dir)

    if show_progress:
        try:
            resources = await get_dataset_resources(dataset_id)
        except Exception as e:
            logger.error(f"Error fetching resources for {dataset_id}: {e}")
            return []

        remote = _to_remote_resources(resources, repo)
        if not remote:
            return []

        with batch_progress(dataset_id, total=len(remote)) as pbar:
            def _on_file_done(result: dict | None) -> None:
                pbar.update(1)

            return await download_resources(
                remote,
                repo,
                dataset_id,
                client,
                source_id=SOURCE_ID,
                producer="tesouro-direto-fetcher",
                max_concurrency=max_concurrency,
                logger=logger,
                on_file_done=_on_file_done,
            )

    with log_step(logger, "download-dataset", dataset_id=dataset_id):
        logger.info(f"Fetching metadata for {dataset_id}...")
        try:
            resources = await get_dataset_resources(dataset_id)
        except Exception as e:
            logger.error(f"Error fetching resources for {dataset_id}: {e}")
            return []

        remote = _to_remote_resources(resources, repo)
        if not remote:
            logger.info("No CSV resources found.")
            return []

        logger.info(f"Found {len(remote)} files. Starting download...")
        return await download_resources(
            remote,
            repo,
            dataset_id,
            client,
            source_id=SOURCE_ID,
            producer="tesouro-direto-fetcher",
            max_concurrency=max_concurrency,
            logger=logger,
        )


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
