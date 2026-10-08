
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
    # Optional "module:Class" path for a custom/third-party bridge. When set,
    # the registry imports this class instead of looking `type` up in the
    # built-ins. Lets users add bridges without packaging/entry points.
    import_path: str | None = None

class StorageConfig(msgspec.Struct, kw_only=True):
    type: str
    path: str
    options: dict[str, Any] = {}
    import_path: str | None = None


class Config(msgspec.Struct):
    bridges: list[BridgeConfig]
    storage: StorageConfig | None = None
    # Plugin modules or .py files to import at startup. Each must expose
    # `def register(registry): ...` which registers its bridge class(es).
    plugins: list[str] = []

    # --- Runtime / path settings (all defaulted so existing configs keep working) ---
    data_dir: str = "data"          # where Parquet batches land
    log_dir: str = "logs"           # root for per-bridge durable append-logs
    specs_dir: str = "specs"        # directory of MappingSpec JSON files
    db_path: str = "catalog.db"     # SQLite catalog path
    poll_interval: float = 1        # seconds the core sleeps when no sealed segments
    segment_bytes: int = 65536      # size-based auto-seal threshold for append-logs
    parquet_batch_rows: int = 65536 # readings buffered before a Parquet file is written
    timeout: int = 5              # minutes to automatically seal the log files.
    interval: int = 600
