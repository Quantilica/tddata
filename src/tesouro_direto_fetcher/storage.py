"""Storage layout and naming conventions for Tesouro Direto files.

Files are stored under ``<dataset_id>/`` directly (Padrão B). Filenames embed
the upstream ``last_modified`` timestamp using the pattern
``<slug>@<YYYYMMDDTHHMMSS>.csv`` so multiple snapshots of the same resource
coexist.
"""

import datetime as dt
from pathlib import Path

from quantilica_core.storage import StampedDataRepository, slugify, stamp_filename


class DataRepository(StampedDataRepository):
    """Tesouro Direto data store using the ``<dataset_id>/`` layout."""

    def list_datasets(self) -> list[str]:
        """Alias for ``list_dataset_ids`` to match CLI usage."""
        return self.list_dataset_ids()

    def get_all_latest_files(self, dataset_id: str) -> list[Path]:
        """Alias for ``get_all_latest_stamped_files`` to match CLI usage."""
        return self.get_all_latest_stamped_files(dataset_id)

    def file_path(self, dataset_id: str, filename: str) -> Path:
        """Return the absolute path of ``filename`` under ``dataset_id``."""
        return self.dataset_path(dataset_id, filename)

    @staticmethod
    def generate_filename(
        name: str, last_modified: str | None = None
    ) -> str:
        """Return ``<slug>@<YYYYMMDDTHHMMSS>.csv`` for a CKAN resource.

        Returns ``<slug>.csv`` (no stamp) when ``last_modified`` is absent or
        unparseable, rather than inventing a timestamp.
        """
        name_slug = slugify(name)
        timestamp: dt.datetime | None = None
        if last_modified:
            try:
                timestamp = dt.datetime.fromisoformat(last_modified)
            except ValueError:
                pass
        return stamp_filename(name_slug, "csv", timestamp, precision="datetime")
