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


"""Functions to download Tesouro Direto's historical data"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from tqdm.asyncio import tqdm

from .constants import CKAN_API_URL, HTTP_HEADERS
from .storage import generate_filename


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

    if dest_filepath.exists():
        # Ideally we check for size/content, but for now assuming name uniqueness via timestamp
        return None

    try:
        async with semaphore:
            # Get total size for progress bar
            # We use a HEAD request or just start streaming
            # Let's stream directly
            async with client.stream(
                "GET", url, headers=HTTP_HEADERS, timeout=60.0
            ) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("Content-Length", 0))
                if total_size == 0 and resource.get("size"):
                    total_size = int(resource["size"])

                desc = f"Downloading {filename[:30]}..."
                with open(dest_filepath, "wb") as f:
                    with tqdm(
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        desc=desc,
                        leave=False,
                    ) as pbar:
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


async def download(
    dest_dir: Path, dataset_id: str, max_concurrency: int = 3
) -> List[Dict]:
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
