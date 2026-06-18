from datetime import datetime, timezone

from zoop.contracts.catalog import CatalogEntry
from zoop.contracts.model import Reading
from zoop.utils.clock import to_microsecs


def summarize(
    input: list[Reading],
    location: str,
    backend: str,
) -> CatalogEntry:
    """Based on a list of Reading, returns a CatalogEntry for the ingest batch"""
    devices = tuple(sorted({r.device_id for r in input}))
    metrics = tuple(sorted({r.metric for r in input}))
    row_count = len(input)
    ts_min = min(r.ts for r in input)
    ts_max = max(r.ts for r in input)
    created_at = to_microsecs(datetime.now(timezone.utc))

    return CatalogEntry(
        location=location,
        backend=backend,
        row_count=row_count,
        ts_min=ts_min,
        ts_max=ts_max,
        devices=devices,
        metrics=metrics,
        created_at=created_at,
    )
