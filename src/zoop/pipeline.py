# Ingestion pipeline:
#   Data -> coerce(raw) -> fan_out → write_parquet(path) -> summarize(readings, path, now) -> store.store(entry)

from datetime import datetime

import msgspec

from zoop.contracts.mapping import MappingSpec, apply_spec
from zoop.contracts.metadata import MetadataStore
from zoop.contracts.processor import Processor
from zoop.contracts.reading import Reading, Sample, fan_out
from zoop.contracts.storage import StorageBackend
from zoop.metadata import Metadata
from zoop.utils import generate_id, to_microsecs


class Pipeline:

    def __init__(
        self,
        *,
        storage: StorageBackend,
        metadata_store: MetadataStore,
        processors: tuple[Processor, ...],
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
        spec: MappingSpec
    ) -> Sample:
        """Transforms data into Sample according to a MappingSpec.
            If no MappingSpec is provied, the function attempts to sniff the data.
        """
        raw = msgspec.json.decode(data, type=spec)
        return apply_spec(raw, spec)


    def ingest(
        self,
        data: dict,
        spec: MappingSpec
    ) -> None:

        received_at = to_microsecs(datetime.now())
        sample = self._coerce(data, spec)
        observation_id = generate_id(
            sample.device_id,
            idempotency_key=sample.idempotency_key
        )

        self._buffer.extend(
            fan_out(
                sample,
                observation_id=observation_id,
                received_at=received_at
            )
        )

        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        """Executes the pipeline in the following order:
            3. Process
            4. Write
            5. Summarize (extract metadata)
            6. Catalog
        """

        # TODO: This will need to be revamped. The order of the processors should be explicitly set.
        for p in self.processors:
            self._buffer = p.run(self._buffer)

        location = self.storage.write(readings=self._buffer)

        # Summarize the baatch
        summary = Metadata().extract(self._buffer, str(location), str(self.storage))
        self.metadata_store.store(summary)
