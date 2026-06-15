
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class CatalogEntry:
    """Metadata about a batch entry"""
    # path: str
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

    def list_entries(self) -> list[CatalogEntry]:
        pass

    def close(self) -> None:
        pass
