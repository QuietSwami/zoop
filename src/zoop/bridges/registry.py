# Bridge Registry
from __future__ import annotations

from pathlib import Path

from zoop.config import BridgeConfig, ConfigError
from zoop.contracts.bridge import TransportBridge
from zoop.handoff.append_log import AppendLog


class BridgeRegistry:

    def __init__(self):
        self._registry: dict[str, type[TransportBridge]] = {}

    def all(self) -> dict[str, type[TransportBridge]]:
        return self._registry

    def register(self, cls: type[TransportBridge]) -> None:
        """Register the bridges at runtime."""
        if cls.type in self._registry:
            raise ValueError(f"bridge is already registered: {cls.type}")
        self._registry[cls.type] = cls

    def create(self, configs: list[BridgeConfig]) -> list[TransportBridge]:
        """Starts a list of bridges"""
        bridges: list[TransportBridge] = []
        for cfg in configs:
            try:
                cls = self._registry[cfg.type]
            except KeyError:
                raise ConfigError(f"unknown bridge type: {cfg.type}")

            producer = AppendLog(Path("logs") / f"{cfg.type}-{cfg.id}")  # per-bridge log dir

            bridges.append(
                cls(
                    producer,
                    **cfg.options
                )
            )
        return bridges
