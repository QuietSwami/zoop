
from typing import Any

import msgspec


class BridgeConfig(msgspec.Struct, kw_only=True):
    type: str
    id: str
    enabled: bool = True
    options: dict[str, Any] = {}


class Config(msgspec.Struct):
    bridges: list[BridgeConfig]
