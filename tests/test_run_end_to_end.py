import asyncio
import json
from pathlib import Path

import pytest

from zoop.bridges.dummy import DummyBridge
from zoop.catalog.sqlite import SQLiteCatalog
from zoop.core.pipeline import Core, Pipeline
from zoop.handoff.append_log import AppendLog
from zoop.handoff.drainer import SegmentDrainer
from zoop.normalize.specs import SpecRegistry
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


def _write_spec(specs_dir: Path) -> None:
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "dummy.json").write_text(json.dumps(DUMMY_SPEC))


@pytest.mark.integration
def test_run_end_to_end(tmp_path: Path):
    log_dir = tmp_path / "logs"
    data_dir = tmp_path / "data"
    specs_dir = tmp_path / "specs"
    db_path = str(tmp_path / "catalog.db")
    _write_spec(specs_dir)

    producer = AppendLog(log_dir / "dummy-1", max_bytes=256)
    bridge = DummyBridge(producer, source="dummy", interval=0.02, devices=5)

    storage = ParquetBackend("parquet", data_dir)
    catalog = SQLiteCatalog(db_path)
    specs = SpecRegistry(specs_dir)
    pipeline = Pipeline(storage=storage, metadata_store=catalog, processors=())
    core = Core(
        drainer=SegmentDrainer(log_dir),
        specs=specs,
        pipeline=pipeline,
        poll_interval=0.05,
    )

    async def drive() -> None:
        stop = asyncio.Event()
        bridge_task = asyncio.ensure_future(bridge.run())
        core_task = asyncio.ensure_future(core.run(stop))

        await asyncio.sleep(0.5)  # let data flow through the full path

        stop.set()
        bridge_task.cancel()
        try:
            await bridge_task
        except asyncio.CancelledError:
            pass
        # Seal in-flight active log, then let the core finish its final drain.
        AppendLog(log_dir / "dummy-1").close()
        core._drain_once()
        await core_task

    try:
        asyncio.run(drive())

        parquet_files = list(data_dir.glob("*.parquet"))
        assert parquet_files, "expected at least one Parquet file"

        entries = catalog.list_entries()
        assert len(entries) >= 1
        assert all(e.row_count > 0 for e in entries)
        assert all("dummy-" in d for e in entries for d in e.devices)
    finally:
        catalog.close()
