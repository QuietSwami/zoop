
from typing import Any

import msgspec


class ConfigError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class BridgeConfig(msgspec.Struct, kw_only=True):
    type: str
    id: str
    enabled: bool = True
    options: dict[str, Any] = {}


class Config(msgspec.Struct):
    bridges: list[BridgeConfig]
