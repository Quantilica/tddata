"""Storage layout and naming conventions for Tesouro Direto files.

Files are stored under the standard ``raw/<dataset_id>/`` layout from
``quantilica_core.storage.BaseDataRepository``. Filenames embed the upstream
``last_modified`` timestamp using the pattern ``<slug>@<YYYYMMDDTHHMMSS>.csv``
so multiple snapshots of the same resource coexist.
"""

import datetime as dt
import fnmatch
import re
import unicodedata
from pathlib import Path

from quantilica_core.storage import BaseDataRepository


def slugify(value: str) -> str:
    """Normalize a string to a URL-friendly slug."""
    value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


class DataRepository(BaseDataRepository):
    """Tesouro Direto data store using the ``raw/<dataset_id>/`` layout."""

    def file_path(self, dataset_id: str, filename: str) -> Path:
        """Return the absolute path of ``filename`` under ``dataset_id``."""
        return self.raw_path(dataset_id, filename)

    @staticmethod
    def generate_filename(
        name: str, last_modified: str | None = None
    ) -> str:
        """Return ``<slug>@<YYYYMMDDTHHMMSS>.csv`` for a CKAN resource."""
        name_slug = slugify(name)
        timestamp: dt.datetime
        if last_modified:
            try:
                timestamp = dt.datetime.fromisoformat(last_modified)
            except ValueError:
                timestamp = dt.datetime.now()
        else:
            timestamp = dt.datetime.now()
        return f"{name_slug}@{timestamp:%Y%m%dT%H%M%S}.csv"

    def get_latest_file(
        self, dataset_id: str, pattern: str
    ) -> Path | None:
        """Return the latest file matching ``pattern`` in the dataset dir."""
        dataset_dir = self.raw_path(dataset_id)
        if not dataset_dir.exists():
            return None

        candidates = (
            f
            for f in dataset_dir.iterdir()
            if f.is_file() and fnmatch.fnmatch(f.name, pattern)
        )
        latest_file: Path | None = None
        latest_ts = ""
        for f in candidates:
            if "@" not in f.name:
                continue
            ts = f.name.rsplit("@", 1)[-1].removesuffix(".csv")
            if ts > latest_ts:
                latest_ts = ts
                latest_file = f
        return latest_file

    def get_all_latest_files(self, dataset_id: str) -> list[Path]:
        """Return one Path per slug — the latest @timestamp variant of each."""
        dataset_dir = self.raw_path(dataset_id)
        if not dataset_dir.exists():
            return []

        by_slug: dict[str, tuple[Path, str]] = {}
        for f in dataset_dir.glob("*.csv"):
            if "@" not in f.name:
                continue
            slug, _, rest = f.name.partition("@")
            ts = rest.removesuffix(".csv")
            current = by_slug.get(slug)
            if current is None or ts > current[1]:
                by_slug[slug] = (f, ts)
        return [pair[0] for pair in by_slug.values()]

    def list_datasets(self) -> list[str]:
        """Return all ``dataset_id`` directories present under ``raw/``."""
        raw_root = self.storage.path_for("raw")
        if not raw_root.exists():
            return []
        return sorted(
            entry.name for entry in raw_root.iterdir() if entry.is_dir()
        )
