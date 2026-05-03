"""Functions to download Tesouro Direto's historical data"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from tqdm.asyncio import tqdm

from .constants import CKAN_API_URL, HTTP_HEADERS
from .storage import generate_filename, get_latest_file


async def get_dataset_resources(
    client: httpx.AsyncClient, dataset_id: str
) -> List[Dict]:
    """Fetch resources metadata from CKAN dataset asynchronously."""
    params = {"id": dataset_id}
    response = await client.get(CKAN_API_URL, params=params, headers=HTTP_HEADERS)
    response.raise_for_status()
    data = response.json()
    if not data["success"]:
        raise ValueError(f"CKAN API failed: {data.get('error')}")
    return data["result"]["resources"]


async def get_download_info(dest_dir: Path, dataset_id: str) -> List[Dict]:
    """Get metadata about files that would be downloaded without downloading them.

    Args:
        dest_dir: The directory path where files would be saved
        dataset_id: The CKAN dataset ID or name

    Returns:
        List[Dict]: List of metadata dictionaries containing:
            - resource_name: Name of the resource from CKAN
            - url: Download URL
            - filename: Generated filename with timestamp
            - destination: Full path where file would be saved
            - size: File size in bytes (if available)
            - last_modified: Last modification date (if available)
            - format: File format
            - would_download: Whether file would be downloaded (based on size check)
            - latest_local: Path to latest local version (if exists)
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:
        try:
            resources = await get_dataset_resources(client, dataset_id)
        except Exception as e:
            raise ValueError(f"Error fetching resources for {dataset_id}: {e}")

        info_list = []
        for resource in resources:
            if resource.get("format", "").upper() != "CSV":
                continue

            url = resource["url"]
            last_modified_str = resource.get("last_modified") or resource.get("created")
            filename = generate_filename(resource["name"], last_modified_str)
            dest_filepath = dest_dir / filename

            # Check for existing latest file
            slug = filename.split("@")[0]
            latest_file = get_latest_file(dest_dir, f"{slug}*.csv")

            # Try to get file size and ensure it's an integer
            file_size = resource.get("size", 0)
            if file_size:
                try:
                    file_size = int(file_size)
                except (ValueError, TypeError):
                    file_size = 0
            would_download = True

            # Check if we would skip this download
            if latest_file and file_size and latest_file.stat().st_size == file_size:
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


async def download_resource(
    client: httpx.AsyncClient,
    resource: Dict,
    dest_dir: Path,
    semaphore: asyncio.Semaphore,
) -> Optional[Dict]:
    """Download a single resource asynchronously with a semaphore."""
    url = resource["url"]
    last_modified_str = resource.get("last_modified") or resource.get("created")
    filename = generate_filename(resource["name"], last_modified_str)
    dest_filepath = dest_dir / filename

    # Get expected size via HEAD request
    total_size = 0
    try:
        async with semaphore:
            head_response = await client.head(url, headers=HTTP_HEADERS, timeout=10.0)
            head_response.raise_for_status()
            total_size = int(head_response.headers.get("Content-Length", 0))
            if total_size == 0 and resource.get("size"):
                total_size = int(resource["size"])
    except Exception as e:
        print(f"Failed to get size for {url}: {e}")
        # Proceed with download anyway

    # Check if latest file for this resource has the same size
    slug = filename.split("@")[0]
    latest_file = get_latest_file(dest_dir, f"{slug}*.csv")
    if latest_file and latest_file.stat().st_size == total_size and total_size > 0:
        return None

    try:
        async with semaphore:
            async with client.stream("GET", url, headers=HTTP_HEADERS, timeout=60.0) as response:
                response.raise_for_status()
                if total_size == 0:
                    total_size = int(response.headers.get("Content-Length", 0))
                    if total_size == 0 and resource.get("size"):
                        total_size = int(resource["size"])

                desc = f"Downloading {filename[:30]}..."
                with open(dest_filepath, "wb") as f:
                    with tqdm(total=total_size, unit="B", unit_scale=True, desc=desc, leave=False) as pbar:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))

        return {
            "url": url,
            "filename": filename,
            "destination": dest_filepath,
            "file_size": total_size,
        }

    except Exception as e:
        print(f"Failed to download {url}: {e}")
        if dest_filepath.exists():
            dest_filepath.unlink()
        return None


async def download(dest_dir: Path, dataset_id: str, max_concurrency: int = 3) -> List[Dict]:
    """Download data files concurrently.

    Args:
        dest_dir: The directory path to save the file
        dataset_id: The CKAN dataset ID or name.
        max_concurrency: Maximum number of concurrent downloads.

    Returns:
        List[Dict]: metadata for downloaded files
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(max_concurrency)

    async with httpx.AsyncClient() as client:
        print(f"Fetching metadata for {dataset_id}...")
        try:
            resources = await get_dataset_resources(client, dataset_id)
        except Exception as e:
            print(f"Error fetching resources for {dataset_id}: {e}")
            return []

        tasks = []
        for resource in resources:
            if resource.get("format", "").upper() != "CSV":
                continue
            tasks.append(download_resource(client, resource, dest_dir, semaphore))

        if not tasks:
            print("No CSV resources found.")
            return []

        print(f"Found {len(tasks)} files. Starting download...")
        results = await asyncio.gather(*tasks)

    # Filter out None values (skipped or failed)
    downloaded = [r for r in results if r is not None]
    print(f"Successfully downloaded {len(downloaded)} files.")
    return downloaded
