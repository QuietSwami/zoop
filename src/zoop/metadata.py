from zoop.contracts.reading import Sample
from zoop.contracts.metadata import CatalogEntry

class Metadata:

    def __init__(self):
        pass

    def extract(self, input: list[Reading], created_at: int) -> CatalogEntry:
        """Based on a Sample, returns a CatalogEntry for the ingest batch"""

        devices = [r.device_id for r in input]
        metrics = [r.metric for r in input]
        row_count = len(input)
        ts_min = min(r.ts for r in input)
        ts_max = max(r.ts for r in input)

        return CatalogEntry(
            row_count=row_count,
            ts_min=ts_min,
            ts_max=ts_max,
            devices=devices,
            metrics=metrics,
            created_at=created_at
        )
