from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from zoop.reading import Field, Sample, Reading, fan_out


@pytest.mark.unit
def test_field_defaults():
    f = Field(metric="temperature", value=21.5, value_type="double")
    assert f.unit is None
    assert f.quality == "good"


@pytest.mark.unit
def test_sample_holds_multiple_fields():
    s = Sample(
        device_id="ws-42",
        ts=datetime(2026, 6, 14, tzinfo=timezone.utc),
        tags={"location": "barn-3"},
        fields=[
            Field("temperature", 21.5, "double", unit="Cel"),
            Field("humidity", 60, "int", unit="%"),
        ],
    )
    assert len(s.fields) == 2
    assert s.tags["location"] == "barn-3"


@pytest.mark.unit
def test_reading_rejects_attribute_reassignment():
    r = Reading(
        device_id="ws-42", ts=0, observation_id="o1", metric="temperature",
        value=21.5, value_type="double", unit="Cel", quality="good",
        tags={}, received_at=0,
    )
    with pytest.raises(FrozenInstanceError):
        r.value = 99  # type: ignore[misc]


@pytest.mark.unit
def test_reading_equality():
    kw = dict(device_id="d", ts=1, observation_id="o", metric="m",
              value=1, value_type="int", unit=None, quality="good",
              tags={}, received_at=2)
    assert Reading(**kw) == Reading(**kw)

@pytest.mark.unit
def test_fan_out_explodes_fields_sharing_context():
    sample = Sample(
        device_id="ws-42",
        ts=datetime(1970, 1, 1, 0, 0, 1, tzinfo=timezone.utc),  # = 1_000_000 µs
        tags={"location": "barn-3"},
        fields=[
            Field("temperature", 21.5, "double", unit="Cel"),
            Field("humidity", 60, "int", unit="%"),
        ],
    )

    readings = fan_out(sample, observation_id="obs-1", received_at=42)

    assert len(readings) == 2
    # shared context across all rows
    assert {r.observation_id for r in readings} == {"obs-1"}
    assert {r.ts for r in readings} == {1_000_000}
    assert all(r.device_id == "ws-42" for r in readings)
    assert all(r.tags == {"location": "barn-3"} for r in readings)
    assert all(r.received_at == 42 for r in readings)
    # per-field values
    assert readings[0].metric == "temperature" and readings[0].value == 21.5
    assert readings[1].metric == "humidity" and readings[1].unit == "%"


@pytest.mark.unit
def test_fan_out_rejects_naive_datetime():
    sample = Sample("d", datetime(2026, 1, 1), {}, [Field("m", 1, "int")])
    with pytest.raises(ValueError):
        fan_out(sample, observation_id="o", received_at=0)


@pytest.mark.unit
def test_fan_out_empty_fields_returns_empty():   # adjust if you decide this is an error
    sample = Sample("d", datetime(1970, 1, 1, tzinfo=timezone.utc), {}, [])
    assert fan_out(sample, observation_id="o", received_at=0) == []
