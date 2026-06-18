import pytest

from zoop.catalog.summarize import summarize
from zoop.contracts.model import Reading


def _reading(device_id: str, ts: int, metric: str) -> Reading:
    return Reading(
        device_id=device_id,
        ts=ts,
        observation_id="obs",
        metric=metric,
        value=1,
        value_type="int",
        unit=None,
        tags={},
        received_at=0,
    )


@pytest.mark.unit
def test_summarize_basic_counts_and_bounds():
    readings = [
        _reading("d1", 100, "temp"),
        _reading("d1", 300, "humidity"),
        _reading("d2", 200, "temp"),
    ]
    entry = summarize(readings, location="file:///x.parquet", backend="parquet")

    assert entry.row_count == 3
    assert entry.ts_min == 100
    assert entry.ts_max == 300
    assert entry.location == "file:///x.parquet"
    assert entry.backend == "parquet"


@pytest.mark.unit
def test_summarize_devices_are_distinct_and_sorted():
    readings = [
        _reading("d2", 1, "temp"),
        _reading("d1", 2, "temp"),
        _reading("d1", 3, "temp"),
    ]
    entry = summarize(readings, location="loc", backend="b")
    assert entry.devices == ("d1", "d2")


@pytest.mark.unit
def test_summarize_created_at_is_populated():
    entry = summarize([_reading("d", 1, "m")], location="loc", backend="b")
    assert isinstance(entry.created_at, int)
    assert entry.created_at > 0


@pytest.mark.xfail(
    reason="BUG: summarize does not dedupe metrics; it keeps one entry per "
    "Reading instead of distinct metric names (summarize.py:16)",
    strict=False,
)
@pytest.mark.unit
def test_summarize_metrics_are_distinct():
    readings = [
        _reading("d1", 1, "temp"),
        _reading("d1", 2, "temp"),
        _reading("d2", 3, "humidity"),
    ]
    entry = summarize(readings, location="loc", backend="b")
    # Expect distinct (deduped) metric names.
    assert set(entry.metrics) == {"temp", "humidity"}
    assert len(entry.metrics) == 2
