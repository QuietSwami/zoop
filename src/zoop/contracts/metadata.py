
from dataclasses import dataclass
from typing import Iterator, Protocol

from typing_extensions import Iterator


@dataclass(frozen=True)
class CatalogEntry:
    """Metadata about a batch entry"""
    location: str # URI type location identifier
    # Examples:
    # Parquet (local) :  file:///data/2026/06/0001.parquet
    # Parquet (S3)    :  s3://my-bucket/zoop/0001.parquet
    # DuckDB table    :  duckdb://metrics?batch=1234
    # Postgres        :  pg://readings?batch=1234
    backend: str            # which backend wrote the batch, in case of multiple backends.
    row_count: int
    ts_min: int
    ts_max: int
    devices: tuple[str, ...]   # tuples, not lists → hashable/immutable (same lesson as Reading.tags)
    metrics: tuple[str, ...]
    created_at: int


class MetadataStore(Protocol):
    """Base class for all metadata stores."""

    def store(self, entry: CatalogEntry) -> None:
        pass

    def find(
        self,
        *,
        ts_from: int | None = None,
        ts_to: int | None = None,
        limit: int | None = None,
    ) -> Iterator[CatalogEntry]:
        pass

    def list_entries(self) -> list[CatalogEntry]:
        pass

    def close(self) -> None:
        pass
