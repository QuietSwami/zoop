# Ingestion pipeline:
#   Data -> coerce(raw) -> fan_out → write_parquet(path) -> summarize(readings, path, now) -> store.store(entry)

from reading import Sample, Reading, fan_out
from datatime import datetime
from utils import to_microsecs


class Pipeline:

    def __init__(
        self,
        *,
        storage: StorageBackend,
        metadata_store: MetadataStore,
        processors: tuple[Processor, ..],
    ):
        self.metadata_store = metadata_store
        self.storage = storage
        self.processors = processors

    def ingest(self,
        sample: Sample,
        *,
        observation_id: str
    ) -> None:
        created_at = to_micrsecs(datetime.now())
        readings = fan_out(sample)

        # TODO: This will need to be revamped. The order of the processors should be explicitly set.
        for p in self.processors:
            readings = p.run(readings)

        self.storage.write(readings=readings)
