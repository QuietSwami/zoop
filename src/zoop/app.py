import asyncio
import logging
import signal
import sys
from pathlib import Path

import msgspec

from zoop.bridges.dummy import DummyBridge
from zoop.bridges.http import HTTPBridge
from zoop.bridges.mqtt import MQTTBridge
from zoop.bridges.registry import BridgeRegistry
from zoop.catalog.sqlite import SQLiteCatalog
from zoop.cli import load_config, parse_args
from zoop.config import Config, ConfigError
from zoop.contracts.mapping import SpecError
from zoop.core.pipeline import Core, Pipeline
from zoop.handoff.append_log import AppendLog
from zoop.handoff.drainer import SegmentDrainer
from zoop.log import setup_logging
from zoop.normalize.specs import SpecRegistry
from zoop.storage.parquet import ParquetBackend
from zoop.storage.registry import StorageRegistry

log = logging.getLogger(__name__)


def build_bridge_registry(config: Config, extra_plugins: list[str] | None = None) -> BridgeRegistry:
    """Create a registry with the built-in bridges + any config/CLI plugins."""
    registry = BridgeRegistry()
    registry.register(MQTTBridge)   # built-ins
    registry.register(DummyBridge)
    registry.register(HTTPBridge)
    registry.load_plugins(list(config.plugins) + list(extra_plugins or []))
    return registry

def build_storage_registry( config: Config, extra_plugins: list[str] | None = None ) -> StorageRegistry:
    """Create a Storage Registry with the built-in storages + any config/CLI plugins"""
    registry = StorageRegistry()
    registry.register(ParquetBackend)
    return registry


def validate(config: Config, extra_plugins: list[str] | None = None) -> int:
    """Validate every bridge: its class resolves and its options are valid."""
    try:
        registry = build_bridge_registry(config, extra_plugins)
    except ConfigError as e:
        print(f"plugin error: {e}", file=sys.stderr)
        return 1

    errors: list[str] = []

    for bridge in config.bridges:
        try:
            cls = registry.resolve(bridge)            # built-in type OR import_path
        except ConfigError as e:
            errors.append(f"bridge '{bridge.id}': {e}")
            continue
        try:
            msgspec.convert(bridge.options, cls.options_schema)
        except msgspec.ValidationError as e:
            errors.append(f"bridge '{bridge.id}' bad options: {e}")

    # Validate StorageBackends and their configs

    # What's storage valdation?
    # Checking if there's connection to the backend,
    # Validate that the use can write and read on the backend,
    #

    # Validate MetadataStorage and their configs

    if errors:
        for err in errors:
            print(f" - {err}", file=sys.stderr)
        return 1

    print(f"OK: {len(config.bridges)} bridges configured")
    return 0



class App:
    """Wires the bridges (producers) to the core drainer (consumer) and runs them.

    Bridges append to durable per-bridge logs; the core drains sealed segments,
    coerces them via the spec registry, and lands them as Parquet + catalog rows.
    """

    def __init__(self, config: Config, extra_plugins: list[str] | None = None) -> None:
        self.config = config
        self.bridge_registry = build_bridge_registry(config, extra_plugins)
        self.storage_registry = build_storage_registry(config, extra_plugins)

    async def serve(self) -> None:
        config = self.config
        interval = config.interval * 60                     # minutes between stale-seal checks, must be less than timeout.
        timeout = config.timeout * 60 * 1_000_000           # converting minutes to microseconds
        log_dir = Path(config.log_dir)


        # Storage configuration
        if config.storage is None:
            raise ConfigError("no storage backend configured")

        storage = self.storage_registry.create(config.storage)

        log.info(f"configured storage {storage.type}")

        catalog = SQLiteCatalog(config.db_path)
        specs = SpecRegistry(Path(config.specs_dir))

        pipeline = Pipeline(
            storage=storage,
            metadata_store=catalog,
            processors=(),
            parquet_batch_rows=config.parquet_batch_rows
        )

        enabled = [b for b in config.bridges if b.enabled]
        bridges, logs = self.bridge_registry.create(
            enabled,
            log_dir=log_dir,
            segment_bytes=config.segment_bytes,
        )

        log.info(
            "starting zoop: %d bridge(s) [%s], data=%s logs=%s catalog=%s",
            len(enabled),
            ", ".join(f"{b.type}/{b.id}" for b in enabled),
            config.data_dir,
            config.log_dir,
            config.db_path,
        )

        drainer = SegmentDrainer(log_dir)
        core = Core(
            drainer=drainer,
            specs=specs,
            pipeline=pipeline,
            poll_interval=config.poll_interval,
        )

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)

        try:
            async with asyncio.TaskGroup() as tg:
                for bridge in bridges:
                    tg.create_task(_run_bridge(bridge, stop))

                # task to automatically seal log files for bridges in standby
                tg.create_task(stale_log(logs, timeout, stop, interval))

                tg.create_task(core.run(stop))
        finally:
            # Seal each bridge's in-flight active log so its tail records aren't
            # stranded, then drain once more so they land before we close.
            log.info("shutting down: sealing logs and draining remaining segments")
            for lg in logs:
                lg.seal()

            core._drain_once()
            pipeline.flush()
            catalog.close()

            for lg in logs:
                lg.close()

            log.info("shutdown complete")


async def _run_bridge(bridge, stop: asyncio.Event) -> None:
    """Run a bridge until the stop event fires, then cancel it cleanly."""
    task = asyncio.ensure_future(bridge.run())
    await stop.wait()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

async def stale_log(
    logs: list[AppendLog],
    timeout: int,
    stop: asyncio.Event,
    interval: int
) -> None:
    while not stop.is_set():
        for lg in logs:
            lg.seal_if_stale(timeout)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass

def main() -> None:
    args = parse_args()
    setup_logging(getattr(args, "log_level", "info"))
    try:
        config = load_config(args.config)
    except ConfigError as e:
        log.error("config error: %s", e)
        raise SystemExit(1)

    plugins = getattr(args, "plugin", []) or []

    if args.command == "check" or getattr(args, "check", False):
        raise SystemExit(validate(config, plugins))

    # args.command == "run"
    try:
        asyncio.run(App(config, plugins).serve())
    except (ConfigError, SpecError) as e:
        log.error("startup error: %s", e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
