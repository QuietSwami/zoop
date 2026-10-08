# Bridge Registry
from __future__ import annotations

from pathlib import Path

from zoop.config import BridgeConfig, ConfigError
from zoop.contracts.bridge import TransportBridge
from zoop.handoff.append_log import AppendLog
from zoop.utils.imports import import_module_or_file, load_class


class BridgeRegistry:

    def __init__(self):
        self._registry: dict[str, type[TransportBridge]] = {}

    def all(self) -> dict[str, type[TransportBridge]]:
        return self._registry

    def register(self, cls: type[TransportBridge]) -> None:
        """Register a bridge class by its `type`. Duplicate type → error.

        The registry maps type -> class (one class per type). Multiple bridge
        *instances* of the same type come from config (different ids) and are
        built in create(), not registered here.
        """
        if cls.type in self._registry:
            raise ValueError(f"bridge type already registered: {cls.type}")
        self._registry[cls.type] = cls

    def load_plugins(self, paths: list[str]) -> None:
        """Import plugin modules/files; each must expose register(registry)."""
        for path in paths:
            module = import_module_or_file(path)
            register = getattr(module, "register", None)
            if register is None:
                raise ConfigError(
                    f"plugin '{path}' has no register(registry) function"
                )
            register(self)

    def resolve(self, cfg: BridgeConfig) -> type[TransportBridge]:
        """Resolve a config entry to a bridge class.

        Uses cfg.import_path when set (custom/third-party bridge); otherwise
        looks `type` up in the registered built-ins.
        """
        if cfg.import_path:
            return load_class(cfg.import_path, "bridge")
        try:
            return self._registry[cfg.type]
        except KeyError:
            raise ConfigError(f"unknown bridge type: {cfg.type}")

    def create(
        self,
        configs: list[BridgeConfig],
        *,
        log_dir: Path = Path("logs"),
        segment_bytes: int | None = None,
    ) -> tuple[list[TransportBridge], list[AppendLog]]:
        """Build a bridge instance per config, each wired to its own append-log.

        `log_dir` is the root under which per-bridge log dirs live; `segment_bytes`
        (when set) turns on size-based auto-sealing of each bridge's active log.
        """
        bridges: list[TransportBridge] = []
        logs: list[AppendLog] = []
        for cfg in configs:
            cls = self.resolve(cfg)
            producer = AppendLog(
                log_dir / f"{cfg.type}-{cfg.id}",  # per-bridge log dir
                max_bytes=segment_bytes,
            )

            logs.append(producer)

            bridges.append(
                cls(
                    producer,
                    **cfg.options
                )
            )
        return bridges, logs
