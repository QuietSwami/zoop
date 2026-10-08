import asyncio
import json
import signal
from pathlib import Path

import pytest

from zoop.app import App, build_bridge_registry, build_storage_registry, validate
from zoop.bridges.dummy import DummyBridge
from zoop.catalog.sqlite import SQLiteCatalog
from zoop.config import BridgeConfig, Config, StorageConfig
from zoop.storage.parquet import ParquetBackend

DUMMY_SPEC = {
    "version": "1",
    "source": "dummy",
    "device_key": "device",
    "ts_key": "ts",
    "ts_unit": "ms",
    "fields": [
        {"key": "temperature", "type": "double", "unit": "Cel"},
        {"key": "humidity", "type": "double", "unit": "%"},
    ],
    "tags": {},
    "idem_key": None,
}


def _make_config(tmp_path: Path, *, storage: StorageConfig | None) -> Config:
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "dummy.json").write_text(json.dumps(DUMMY_SPEC))
    return Config(
        bridges=[
            BridgeConfig(
                type="dummy",
                id="1",
                options={"source": "dummy", "interval": 0.02, "devices": 3},
            )
        ],
        storage=storage,
        log_dir=str(tmp_path / "logs"),
        specs_dir=str(specs_dir),
        db_path=str(tmp_path / "catalog.db"),
        poll_interval=0.05,
        segment_bytes=256,
    )


# --- registry builders -------------------------------------------------------


@pytest.mark.unit
def test_build_bridge_registry_has_builtins(tmp_path: Path):
    config = _make_config(tmp_path, storage=None)
    registry = build_bridge_registry(config)
    assert registry.resolve(BridgeConfig(type="dummy", id="x")) is DummyBridge


@pytest.mark.unit
def test_build_storage_registry_has_parquet(tmp_path: Path):
    config = _make_config(tmp_path, storage=None)
    registry = build_storage_registry(config)
    assert registry.resolve(StorageConfig(type="parquet", path="/x")) is ParquetBackend


# --- validate() --------------------------------------------------------------


@pytest.mark.unit
def test_validate_ok(tmp_path: Path):
    config = _make_config(tmp_path, storage=None)
    assert validate(config) == 0


@pytest.mark.unit
def test_validate_unknown_bridge_type(tmp_path: Path):
    config = _make_config(tmp_path, storage=None)
    config = Config(bridges=[BridgeConfig(type="ghost", id="x")], storage=None)
    assert validate(config) == 1


@pytest.mark.unit
def test_validate_bad_bridge_options(tmp_path: Path):
    config = Config(
        bridges=[BridgeConfig(type="dummy", id="x", options={"bogus": 1})],
        storage=None,
    )
    assert validate(config) == 1


@pytest.mark.unit
def test_validate_plugin_error(tmp_path: Path):
    config = Config(
        bridges=[BridgeConfig(type="dummy", id="x")],
        storage=None,
        plugins=["does.not.exist"],
    )
    assert validate(config) == 1


# --- App.serve() -------------------------------------------------------------


@pytest.mark.integration
def test_serve_requires_storage(tmp_path: Path):
    from zoop.config import ConfigError

    config = _make_config(tmp_path, storage=None)
    with pytest.raises(ConfigError):
        asyncio.run(App(config).serve())


@pytest.mark.integration
def test_serve_end_to_end_and_stops_on_signal(tmp_path: Path):
    data_dir = tmp_path / "data"
    storage = StorageConfig(type="parquet", path=str(data_dir))
    config = _make_config(tmp_path, storage=storage)
    app = App(config)

    async def drive() -> None:
        task = asyncio.ensure_future(app.serve())
        await asyncio.sleep(0.5)  # let data flow through the full path
        signal.raise_signal(signal.SIGINT)  # same path as Ctrl+C -> stop.set
        await asyncio.wait_for(task, timeout=5)  # must exit promptly, not hang

    asyncio.run(drive())

    parquet_files = list(data_dir.glob("*.parquet"))
    assert parquet_files, "expected at least one Parquet file"

    catalog = SQLiteCatalog(config.db_path)
    try:
        entries = catalog.list_entries()
        assert len(entries) >= 1
        assert all(e.row_count > 0 for e in entries)
    finally:
        catalog.close()
