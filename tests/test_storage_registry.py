from pathlib import Path
from typing import Any, ClassVar

import pytest

from zoop.config import ConfigError, StorageConfig
from zoop.storage.parquet import ParquetBackend
from zoop.storage.registry import StorageRegistry


class FakeStorage:
    type: ClassVar[str] = "fake"

    def __init__(self, path: str, **options: Any) -> None:
        self.path = path
        self.options = options


@pytest.mark.unit
def test_register_and_resolve_builtin():
    reg = StorageRegistry()
    reg.register(FakeStorage)
    assert reg.resolve(StorageConfig(type="fake", path="/tmp/x")) is FakeStorage


@pytest.mark.unit
def test_duplicate_register_raises():
    reg = StorageRegistry()
    reg.register(FakeStorage)
    with pytest.raises(ValueError):
        reg.register(FakeStorage)


@pytest.mark.unit
def test_resolve_unknown_type_raises():
    reg = StorageRegistry()
    with pytest.raises(ConfigError):
        reg.resolve(StorageConfig(type="ghost", path="/tmp/x"))


@pytest.mark.unit
def test_resolve_uses_import_path():
    reg = StorageRegistry()
    cfg = StorageConfig(
        type="ignored",
        path="/tmp/x",
        import_path="zoop.storage.parquet:ParquetBackend",
    )
    assert reg.resolve(cfg) is ParquetBackend


@pytest.mark.unit
def test_create_builds_instance_with_path_and_options():
    reg = StorageRegistry()
    reg.register(FakeStorage)
    backend = reg.create(StorageConfig(type="fake", path="/data", options={"k": "v"}))
    assert isinstance(backend, FakeStorage)
    assert backend.path == "/data"
    assert backend.options == {"k": "v"}


@pytest.mark.integration
def test_load_plugins_registers_storage(tmp_path: Path):
    plugin = tmp_path / "plug.py"
    plugin.write_text(
        "from typing import ClassVar\n"
        "\n"
        "class PluginStorage:\n"
        "    type: ClassVar[str] = 'plugin'\n"
        "    def __init__(self, path, **o):\n"
        "        self.path = path\n"
        "\n"
        "def register(registry):\n"
        "    registry.register(PluginStorage)\n"
    )
    reg = StorageRegistry()
    reg.load_plugins([str(plugin)])
    resolved = reg.resolve(StorageConfig(type="plugin", path="/x"))
    assert resolved.__name__ == "PluginStorage"


@pytest.mark.integration
def test_load_plugins_without_register_raises(tmp_path: Path):
    plugin = tmp_path / "noreg.py"
    plugin.write_text("VALUE = 1\n")
    reg = StorageRegistry()
    with pytest.raises(ConfigError):
        reg.load_plugins([str(plugin)])
