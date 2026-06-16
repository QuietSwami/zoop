import sqlite3

import pytest

from zoop.contracts.metadata import CatalogEntry
from zoop.sqlite import SQLiteMetadata


def _entry(
    location: str = "file:///data/0001.parquet",
    backend: str = "parquet",
    devices: tuple[str, ...] = ("ws-42",),
    metrics: tuple[str, ...] = ("temperature",),
) -> CatalogEntry:
    return CatalogEntry(
        location=location,
        backend=backend,
        row_count=10,
        ts_min=1_000_000,
        ts_max=2_000_000,
        devices=devices,
        metrics=metrics,
        created_at=1_700_000_000_000_000,
    )


@pytest.fixture
def store(tmp_path):
    s = SQLiteMetadata(str(tmp_path / "meta.db"))
    yield s
    s.close()


@pytest.mark.unit
def test_list_empty_returns_empty(store):
    assert store.list_entries() == []


@pytest.mark.unit
def test_store_and_list_roundtrip(store):
    entry = _entry()
    store.store(entry)
    assert store.list_entries() == [entry]


@pytest.mark.unit
def test_devices_and_metrics_roundtrip_as_tuples(store):
    entry = _entry(devices=("a", "b", "c"), metrics=("temp", "humidity"))
    store.store(entry)
    [got] = store.list_entries()
    assert got.devices == ("a", "b", "c")        # order preserved
    assert isinstance(got.devices, tuple)         # reconstructed as tuple, not list
    assert got.metrics == ("temp", "humidity")


@pytest.mark.unit
def test_values_with_commas_survive(store):
    # the whole reason devices/metrics are JSON-encoded instead of comma-joined
    entry = _entry(devices=("rack-1,row-2",))
    store.store(entry)
    [got] = store.list_entries()
    assert got.devices == ("rack-1,row-2",)


@pytest.mark.unit
def test_empty_devices_and_metrics(store):
    entry = _entry(devices=(), metrics=())
    store.store(entry)
    [got] = store.list_entries()
    assert got.devices == ()
    assert got.metrics == ()


@pytest.mark.unit
def test_multiple_entries(store):
    store.store(_entry(location="file:///a.parquet"))
    store.store(_entry(location="file:///b.parquet"))
    got = store.list_entries()
    assert len(got) == 2
    assert {e.location for e in got} == {"file:///a.parquet", "file:///b.parquet"}


@pytest.mark.unit
def test_persists_across_reopen(tmp_path):
    path = str(tmp_path / "meta.db")
    s1 = SQLiteMetadata(path)
    s1.store(_entry(location="file:///a.parquet"))
    s1.close()

    s2 = SQLiteMetadata(path)
    try:
        assert [e.location for e in s2.list_entries()] == ["file:///a.parquet"]
    finally:
        s2.close()


@pytest.mark.unit
def test_duplicate_location_rejected(store):
    store.store(_entry(location="file:///dup.parquet"))
    with pytest.raises(sqlite3.IntegrityError):   # location is PRIMARY KEY
        store.store(_entry(location="file:///dup.parquet"))
