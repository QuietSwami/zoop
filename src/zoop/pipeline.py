# Ingestion pipeline:
#   Data -> coerce(raw) -> fan_out → write_parquet(path) -> summarize(readings, path, now) -> store.store(entry)

from datatime import datetime
from utils import to_microsecs

from zoop.contracts.reading import Sample, Reading, fan_out
from zoop.metadata import Metadata

class Pipeline:

    def __init__(
        self,
        *,
        storage: StorageBackend,
        metadata_store: MetadataStore,
        processors: tuple[Processor, ..],
        batch_size: int = 250
    ):
        self.metadata_store = metadata_store
        self.storage = storage
        self.processors = processors
        self._buffer: list[Reading] = [] # Ingest buffer
        self.batch_size = batch_size

    def _coerce(
        self,
        data: dict,
        observation_id: str,
        created_at: int
    ) -> Sample:
        """Transforms data into Sample."""
        pass

    def ingest(
        self,
        data: dict,
        observation_id: str,
        created_at: int
    ) -> Sample:
        sample = self._coerce(data)
        self._buffer.extend(sample)
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        """Executes the pipeline in the following order:
            3. Process
            4. Write
            5. Summarize (extract metadata)
            6. Catalog
        """
        created_at = to_micrsecs(datetime.now())

        # Coerced
        sample = self._coerce(data, observation_id, created_at)

        self._buffer.extend(fan_out(sample))

        # TODO: This will need to be revamped. The order of the processors should be explicitly set.
        for p in self.processors:
            self._buffer = p.run(self._buffer)

        self.storage.write(readings=readings)

        # Summarize the baatch
        summary = Metadata().summarize(self._buffer)
        self.metadata_store.store(summary)
