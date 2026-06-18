import pytest

from zoop.catalog.sqlite import SQLiteCatalog
from zoop.contracts.catalog import CatalogEntry


def _entry(location: str, ts_min: int, ts_max: int) -> CatalogEntry:
    return CatalogEntry(
        location=location,
        backend="parquet",
        row_count=1,
        ts_min=ts_min,
        ts_max=ts_max,
        devices=("d1",),
        metrics=("temp",),
        created_at=0,
    )


@pytest.mark.integration
def test_store_and_list_round_trip(tmp_path):
    cat = SQLiteCatalog(str(tmp_path / "c.db"))
    try:
        cat.store(_entry("file:///a.parquet", 100, 200))
        entries = cat.list_entries()
        assert len(entries) == 1
        assert entries[0].location == "file:///a.parquet"
        assert entries[0].devices == ("d1",)
        assert entries[0].metrics == ("temp",)
    finally:
        cat.close()


@pytest.mark.xfail(
    reason="BUG: SQLiteCatalog.find builds invalid SQL: missing space before "
    "WHERE produces 'metadataWHERE', and 'ORDER_BY' should be 'ORDER BY' "
    "(sqlite.py:79-80)",
    strict=False,
)
@pytest.mark.integration
def test_find_filters_by_ts(tmp_path):
    cat = SQLiteCatalog(str(tmp_path / "c.db"))
    try:
        cat.store(_entry("file:///a.parquet", 100, 200))
        cat.store(_entry("file:///b.parquet", 300, 400))
        results = list(cat.find(ts_from=250))
        assert [e.location for e in results] == ["file:///a.parquet"]
    finally:
        cat.close()


@pytest.mark.xfail(
    reason="BUG: SQLiteCatalog.find SQL is malformed even with no filters "
    "('ORDER_BY' is not valid SQL) (sqlite.py:80)",
    strict=False,
)
@pytest.mark.integration
def test_find_no_filters_returns_all(tmp_path):
    cat = SQLiteCatalog(str(tmp_path / "c.db"))
    try:
        cat.store(_entry("file:///a.parquet", 100, 200))
        results = list(cat.find())
        assert len(results) == 1
    finally:
        cat.close()
