from datetime import datetime, timezone

import pyarrow.parquet as pq
import pytest

from zoop.contracts.reading import Field, Sample, fan_out
from zoop.arrow import SCHEMA, ArrowBackend
from zoop.contracts.storage import EmptyReadings


@pytest.fixture
def readings():
    """One sample with all four value types, fanned out to 4 Readings."""
    sample = Sample(
        device_id="ws-42",
        ts=datetime(1970, 1, 1, 0, 0, 1, tzinfo=timezone.utc),  # = 1_000_000 µs
        tags={"location": "barn-3"},
        fields=[
            Field("temperature", 21.5, "double", unit="Cel"),
            Field("humidity", 60, "int", unit="%"),
            Field("online", True, "bool"),
            Field("status", "ok", "str"),
        ],
    )
    return fan_out(sample, observation_id="obs-1", received_at=42)


@pytest.mark.unit
def test_roundtrip_row_count(readings, tmp_path):
    p = tmp_path / "r.parquet"
    arr = ArrowBackend(p)
    arr.write(readings=readings)
    assert pq.read_table(p).num_rows == len(readings) == 4


@pytest.mark.unit
def test_written_schema_matches(readings, tmp_path):
    p = tmp_path / "r.parquet"
    arr = ArrowBackend(p)
    arr.write(readings=readings)
    assert pq.read_table(p).schema.equals(SCHEMA, check_metadata=False)


@pytest.mark.unit
def test_value_demultiplexed_by_type(readings, tmp_path):
    """Each row fills exactly the column matching its value_type; others are NULL."""
    p = tmp_path / "r.parquet"
    arr = ArrowBackend(p)
    arr.write(readings=readings)
    rows = {row["metric"]: row for row in pq.read_table(p).to_pylist()}

    assert rows["temperature"]["value_double"] == 21.5
    assert rows["temperature"]["value_int"] is None
    assert rows["temperature"]["value_bool"] is None
    assert rows["temperature"]["value_str"] is None

    assert rows["humidity"]["value_int"] == 60
    assert rows["humidity"]["value_double"] is None

    assert rows["online"]["value_bool"] is True
    assert rows["status"]["value_str"] == "ok"


@pytest.mark.unit
def test_tags_roundtrip(readings, tmp_path):
    p = tmp_path / "r.parquet"
    arr = ArrowBackend(p)
    arr.write(readings=readings)
    row = pq.read_table(p).to_pylist()[0]
    assert dict(row["tags"]) == {"location": "barn-3"}


@pytest.mark.unit
def test_shared_context_preserved(readings, tmp_path):
    p = tmp_path / "r.parquet"
    arr = ArrowBackend(p)
    arr.write(readings=readings)
    table = pq.read_table(p)
    assert set(table.column("observation_id").to_pylist()) == {"obs-1"}
    assert set(table.column("device_id").to_pylist()) == {"ws-42"}


@pytest.mark.unit
def test_empty_readings_writes_zero_rows(tmp_path):
    p = tmp_path / "empty.parquet"
    arr = ArrowBackend(p)
    with pytest.raises(EmptyReadings):
        arr.write(readings=[])
