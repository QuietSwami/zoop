


from zoop.config import ConfigError, StorageConfig
from zoop.contracts.storage import StorageBackend
from zoop.utils.imports import import_module_or_file, load_class


class StorageRegistry:
    def __init__(self):
        self._registry: dict[str, type[StorageBackend]] = {}

    def register(self, cls: type[StorageBackend]) -> None:
        """Register a storage class by its `type`. Duplicate type → error.

        The registry maps type -> class (one class per type). Multiple storage
        *instances* of the same type come from config (different ids) and are
        built in create(), not registered here.
        """
        if cls.type in self._registry:
            raise ValueError(f"storage type already registered: {cls.type}")
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

    def resolve(self, cfg: StorageConfig) -> type[StorageBackend]:
        """Resolve a config entry to a storage class.

        Uses cfg.import_path when set (custom/third-party strage); otherwise
        looks `type` up in the registered built-ins.
        """
        if cfg.import_path:
            return load_class(cfg.import_path, "storage")
        try:
            return self._registry[cfg.type]
        except KeyError:
            raise ConfigError(f"unknown storage type: {cfg.type}")

    def create(
        self,
        cfg: StorageConfig
    ) -> StorageBackend:
        return self.resolve(cfg)(
            cfg.path,
            **cfg.options
        )
