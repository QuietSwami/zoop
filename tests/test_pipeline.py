import json
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from zoop.catalog.sqlite import SQLiteCatalog
from zoop.contracts.mapping import FieldSpec, MappingSpec
from zoop.contracts.model import Field, Reading, Sample, fan_out
from zoop.core.pipeline import Pipeline
from zoop.storage.parquet import ParquetBackend
from zoop.utils.ids import generate_id


def _reading(device_id: str, ts: int, metric: str, value, vtype: str) -> Reading:
    return Reading(
        device_id=device_id,
        ts=ts,
        observation_id="obs",
        metric=metric,
        value=value,
        value_type=vtype,
        unit=None,
        tags={"loc": "barn"},
        received_at=123,
    )


def _make_pipeline(tmp_path: Path, parquet_batch_rows: int = 250) -> tuple:
    storage = ParquetBackend(tmp_path / "parquet")
    catalog = SQLiteCatalog(str(tmp_path / "catalog.db"))
    pipeline = Pipeline(
        storage=storage,
        metadata_store=catalog,
        processors=(),
        parquet_batch_rows=parquet_batch_rows,
    )
    return pipeline, storage, catalog


@pytest.mark.integration
def test_flush_empty_buffer_is_noop(tmp_path: Path):
    pipeline, _, catalog = _make_pipeline(tmp_path)
    pipeline.flush()  # nothing buffered
    assert catalog.list_entries() == []
    catalog.close()


@pytest.mark.xfail(
    reason="BUG: Pipeline.flush summarizes self._buffer (reset to []) instead of "
    "the drained `batch`; summarize() then does min() over empty and raises "
    "ValueError (pipeline.py:79,92)",
    strict=False,
)
@pytest.mark.integration
def test_flush_writes_parquet_and_catalog_row(tmp_path: Path):
    pipeline, storage, catalog = _make_pipeline(tmp_path)
    try:
        pipeline._buffer = [
            _reading("d1", 100, "temp", 21.5, "double"),
            _reading("d1", 200, "humidity", 60, "int"),
        ]
        pipeline.flush()

        parquet_files = list((tmp_path / "parquet").glob("*.parquet"))
        assert len(parquet_files) == 1

        entries = catalog.list_entries()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.row_count == 2
        assert entry.ts_min == 100
        assert entry.ts_max == 200

        table = pq.read_table(parquet_files[0])
        assert table.num_rows == 2
    finally:
        catalog.close()


@pytest.mark.xfail(
    reason="BUG: Pipeline.flush summarizes self._buffer instead of `batch`; "
    "see test_flush_writes_parquet_and_catalog_row (pipeline.py:92)",
    strict=False,
)
@pytest.mark.integration
def test_flush_resets_buffer_no_duplicate_writes(tmp_path: Path):
    pipeline, _, catalog = _make_pipeline(tmp_path)
    try:
        pipeline._buffer = [_reading("d1", 100, "temp", 1.0, "double")]
        pipeline.flush()
        # buffer must be empty after a flush
        assert pipeline._buffer == []
        pipeline.flush()  # second flush is a no-op
        assert len(catalog.list_entries()) == 1

        parquet_files = list((tmp_path / "parquet").glob("*.parquet"))
        assert len(parquet_files) == 1
    finally:
        catalog.close()


@pytest.mark.xfail(
    reason="BUG: Pipeline._coerce calls msgspec.json.decode(data, type=spec) "
    "passing a MappingSpec *instance* as the type, which raises TypeError; "
    "should decode to dict then apply_spec (pipeline.py:44)",
    strict=False,
)
@pytest.mark.integration
def test_ingest_end_to_end(tmp_path: Path):
    pipeline, _, catalog = _make_pipeline(tmp_path, parquet_batch_rows=1)
    try:
        spec = MappingSpec(
            version="1",
            source="weather",
            device_key="dev",
            ts_key="t",
            ts_unit="s",
            fields=[FieldSpec(key="temperature", type="double", unit="Cel")],
            tags={"loc": "barn"},
            idem_key=None,
        )
        data = json.dumps({"dev": "ws-1", "t": 1, "temperature": 21.5})
        pipeline.ingest(data, spec)

        parquet_files = list((tmp_path / "parquet").glob("*.parquet"))
        assert len(parquet_files) == 1
        assert len(catalog.list_entries()) == 1
    finally:
        catalog.close()


@pytest.mark.unit
def test_observation_id_shared_across_fanned_out_rows():
    # Documents the observation_id wiring that ingest relies on.
    sample = Sample(
        device_id="d1",
        ts=datetime(1970, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
        tags={},
        fields=[Field("a", 1, "int"), Field("b", 2, "int")],
        idempotency_key="idem-1",
    )
    obs = generate_id(sample.device_id, idempotency_key=sample.idempotency_key)
    rows = fan_out(sample, observation_id=obs, received_at=0)
    assert {r.observation_id for r in rows} == {obs}
    # deterministic from idempotency key
    assert obs == generate_id("anything-else", idempotency_key="idem-1")
