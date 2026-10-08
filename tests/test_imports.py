from pathlib import Path

import pytest

from zoop.config import ConfigError
from zoop.storage.parquet import ParquetBackend
from zoop.utils.imports import import_module_or_file, load_class


@pytest.mark.unit
def test_load_class_resolves_dotted_path():
    assert load_class("zoop.storage.parquet:ParquetBackend", "storage") is ParquetBackend


@pytest.mark.unit
def test_load_class_without_colon_raises():
    with pytest.raises(ConfigError):
        load_class("zoop.storage.parquet", "storage")


@pytest.mark.unit
def test_load_class_bad_module_raises():
    with pytest.raises(ConfigError):
        load_class("zoop.does_not_exist:Thing", "storage")


@pytest.mark.unit
def test_load_class_missing_attribute_raises():
    with pytest.raises(ConfigError):
        load_class("zoop.storage.parquet:Nope", "storage")


@pytest.mark.unit
def test_import_module_or_file_dotted_module():
    module = import_module_or_file("zoop.storage.parquet")
    assert hasattr(module, "ParquetBackend")


@pytest.mark.unit
def test_import_module_or_file_bad_dotted_module_raises():
    with pytest.raises(ConfigError):
        import_module_or_file("zoop.definitely_not_here")


@pytest.mark.integration
def test_import_module_or_file_from_py_file(tmp_path: Path):
    plugin = tmp_path / "myplugin.py"
    plugin.write_text("MARKER = 42\n\ndef register(registry):\n    return None\n")
    module = import_module_or_file(str(plugin))
    assert module.MARKER == 42
    assert callable(module.register)
