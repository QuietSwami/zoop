from datetime import datetime, timezone

import pytest

from zoop.contracts.mapping import FieldSpec, MappingSpec
from zoop.normalize.coerce import apply_spec


def _spec(ts_unit: str = "s", idem_key: str | None = None) -> MappingSpec:
    return MappingSpec(
        version="1",
        source="weather",
        device_key="dev",
        ts_key="t",
        ts_unit=ts_unit,  # type: ignore[arg-type]
        fields=[
            FieldSpec(key="temperature", type="double", unit="Cel"),
            FieldSpec(key="humidity", type="int"),
        ],
        tags={"location": "barn-3"},
        idem_key=idem_key,
    )


@pytest.mark.unit
def test_apply_spec_builds_sample_core_fields():
    data = {"dev": "ws-1", "t": 1, "temperature": 21.5, "humidity": 60}
    sample = apply_spec(data, _spec(ts_unit="s"))

    assert sample.device_id == "ws-1"
    assert sample.ts == datetime(1970, 1, 1, 0, 0, 1, tzinfo=timezone.utc)


@pytest.mark.unit
def test_apply_spec_fields_use_field_key_as_metric():
    data = {"dev": "ws-1", "t": 1, "temperature": 21.5, "humidity": 60}
    sample = apply_spec(data, _spec())

    metrics = {f.metric: f for f in sample.fields}
    assert set(metrics) == {"temperature", "humidity"}
    assert metrics["temperature"].value == 21.5
    assert metrics["temperature"].value_type == "double"
    assert metrics["temperature"].unit == "Cel"
    assert metrics["humidity"].value == 60
    assert metrics["humidity"].unit is None


@pytest.mark.unit
def test_apply_spec_tags_copied_from_spec():
    data = {"dev": "ws-1", "t": 1, "temperature": 21.5, "humidity": 60}
    sample = apply_spec(data, _spec())
    assert sample.tags == {"location": "barn-3"}


@pytest.mark.unit
def test_apply_spec_no_idem_key_yields_none():
    data = {"dev": "ws-1", "t": 1, "temperature": 21.5, "humidity": 60}
    sample = apply_spec(data, _spec(idem_key=None))
    assert sample.idempotency_key is None


@pytest.mark.unit
def test_apply_spec_idem_key_extracted():
    data = {
        "dev": "ws-1",
        "t": 1,
        "temperature": 21.5,
        "humidity": 60,
        "mid": "abc-123",
    }
    sample = apply_spec(data, _spec(idem_key="mid"))
    assert sample.idempotency_key == "abc-123"


@pytest.mark.unit
def test_ts_unit_milliseconds():
    data = {"dev": "d", "t": 1_500, "temperature": 1.0, "humidity": 1}
    sample = apply_spec(data, _spec(ts_unit="ms"))
    assert sample.ts == datetime(1970, 1, 1, 0, 0, 1, 500_000, tzinfo=timezone.utc)


@pytest.mark.unit
def test_ts_unit_microseconds():
    data = {"dev": "d", "t": 1_500_000, "temperature": 1.0, "humidity": 1}
    sample = apply_spec(data, _spec(ts_unit="us"))
    assert sample.ts == datetime(1970, 1, 1, 0, 0, 1, 500_000, tzinfo=timezone.utc)


@pytest.mark.unit
def test_ts_unit_iso_with_offset():
    data = {
        "dev": "d",
        "t": "2026-06-14T12:00:00+00:00",
        "temperature": 1.0,
        "humidity": 1,
    }
    sample = apply_spec(data, _spec(ts_unit="iso"))
    assert sample.ts == datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)


@pytest.mark.unit
def test_ts_unit_iso_naive_assumed_utc():
    # A naive ISO string (no offset) is treated as UTC by coerce.
    data = {"dev": "d", "t": "2026-06-14T12:00:00", "temperature": 1.0, "humidity": 1}
    sample = apply_spec(data, _spec(ts_unit="iso"))
    assert sample.ts == datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)
    assert sample.ts.tzinfo is not None
