# Ingestion pipeline:
#   Data -> coerce(raw) -> fan_out → write_parquet(path) -> summarize(readings, path, now) -> store.store(entry)

import asyncio
import sys
from datetime import datetime, timezone

import msgspec

from zoop.catalog.summarize import summarize
from zoop.contracts.catalog import CatalogStore
from zoop.contracts.handoff import HandoffRecord, LogConsumer
from zoop.contracts.mapping import MappingSpec, SpecError
from zoop.contracts.model import Reading, Sample, fan_out
from zoop.contracts.processor import Processor
from zoop.contracts.storage import StorageBackend
from zoop.normalize.coerce import apply_spec
from zoop.normalize.specs import SpecRegistry
from zoop.utils.clock import to_microsecs
from zoop.utils.ids import generate_id


class Pipeline:

    def __init__(
        self,
        *,
        storage: StorageBackend,
        metadata_store: CatalogStore,
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
        data: str,
        spec: MappingSpec
    ) -> Sample:
        """Transforms data into Sample according to a MappingSpec.
            If no MappingSpec is provied, the function attempts to sniff the data.
        """
        raw = msgspec.json.decode(data)
        return apply_spec(raw, spec)


    def ingest(
        self,
        data: str,
        spec: MappingSpec
    ) -> None:

        received_at = to_microsecs(datetime.now(timezone.utc))
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
        batch, self._buffer = self._buffer, []

        # TODO: This will need to be revamped. The order of the processors should be explicitly set.
        if self.processors:
            for p in self.processors:
                batch = p.run(batch)

        if not batch:
            return

        location = self.storage.write(readings=batch)

        # Summarize the baatch
        summary = summarize(batch, str(location), self.metadata_store.kind())

        self.metadata_store.store(summary)
        self._buffer = []


class Core:
    """Drains sealed handoff segments and feeds them through the pipeline.

    The drain/ingest/flush/discard cycle is checkpoint-after-land: a segment is
    only discarded once its records have been flushed to durable storage (Parquet
    + catalog). If the process dies mid-segment, the segment is replayed on
    restart — at-least-once delivery, never silent loss.
    """

    def __init__(
        self,
        *,
        drainer: LogConsumer,
        specs: SpecRegistry,
        pipeline: Pipeline,
        poll_interval: float = 0.5,
    ) -> None:
        self.drainer = drainer
        self.specs = specs
        self.pipeline = pipeline
        self.poll_interval = poll_interval

    def _ingest_segment(self, segment) -> None:
        for rb in self.drainer.read(segment):
            record = msgspec.msgpack.decode(rb, type=HandoffRecord)
            try:
                spec = self.specs.get(record.source)
            except SpecError as e:
                # dead-letter-lite: skip records we can't type, don't crash.
                print(f"core: skipping record from '{record.source}': {e}", file=sys.stderr)
                continue
            self.pipeline.ingest(record.payload.decode(), spec)

    def _drain_once(self) -> None:
        """One pass over all currently-sealed segments."""
        for segment in self.drainer.sealed():
            self._ingest_segment(segment)
            self.pipeline.flush()         # land the batch...
            self.drainer.discard(segment)  # ...then checkpoint (after flush).

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            segments = self.drainer.sealed()
            if not segments:
                await asyncio.sleep(self.poll_interval)
                continue
            for segment in segments:
                self._ingest_segment(segment)
                self.pipeline.flush()
                self.drainer.discard(segment)
        # Final drain pass after stop, then flush anything still buffered.
        self._drain_once()
        self.pipeline.flush()
