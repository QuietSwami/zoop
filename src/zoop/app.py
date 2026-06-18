import asyncio
import signal
import sys
from pathlib import Path

import msgspec

from zoop.bridges.dummy import DummyBridge
from zoop.bridges.mqtt import MQTTBridge
from zoop.bridges.registry import BridgeRegistry
from zoop.catalog.sqlite import SQLiteCatalog
from zoop.cli import load_config, parse_args
from zoop.config import Config, ConfigError
from zoop.contracts.mapping import SpecError
from zoop.core.pipeline import Core, Pipeline
from zoop.handoff.append_log import AppendLog
from zoop.handoff.drainer import SegmentDrainer
from zoop.normalize.specs import SpecRegistry
from zoop.storage.parquet import ParquetBackend


def build_registry(config: Config, extra_plugins: list[str] | None = None) -> BridgeRegistry:
    """Create a registry with the built-in bridges + any config/CLI plugins."""
    registry = BridgeRegistry()
    registry.register(MQTTBridge)   # built-ins
    registry.register(DummyBridge)
    registry.load_plugins(list(config.plugins) + list(extra_plugins or []))
    return registry


def validate(config: Config, extra_plugins: list[str] | None = None) -> int:
    """Validate every bridge: its class resolves and its options are valid."""
    try:
        registry = build_registry(config, extra_plugins)
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
        self.registry = build_registry(config, extra_plugins)

    async def serve(self) -> None:
        config = self.config
        log_dir = Path(config.log_dir)

        storage = ParquetBackend("parquet", Path(config.data_dir))
        catalog = SQLiteCatalog(config.db_path)
        specs = SpecRegistry(Path(config.specs_dir))
        pipeline = Pipeline(
            storage=storage,
            metadata_store=catalog,
            processors=(),
        )

        enabled = [b for b in config.bridges if b.enabled]
        bridges = self.registry.create(
            enabled,
            log_dir=log_dir,
            segment_bytes=config.segment_bytes,
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
                tg.create_task(core.run(stop))
        finally:
            # Seal each bridge's in-flight active log so its tail records aren't
            # stranded, then drain once more so they land before we close.
            for cfg in enabled:
                AppendLog(log_dir / f"{cfg.type}-{cfg.id}").close()
            core._drain_once()
            pipeline.flush()
            catalog.close()


async def _run_bridge(bridge, stop: asyncio.Event) -> None:
    """Run a bridge until the stop event fires, then cancel it cleanly."""
    task = asyncio.ensure_future(bridge.run())
    await stop.wait()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def main() -> None:
    args = parse_args()
    try:
        config = load_config(args.config)
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        raise SystemExit(1)

    plugins = getattr(args, "plugin", []) or []

    if args.command == "check" or getattr(args, "check", False):
        raise SystemExit(validate(config, plugins))

    # args.command == "run"
    try:
        asyncio.run(App(config, plugins).serve())
    except (ConfigError, SpecError) as e:
        print(f"startup error: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
