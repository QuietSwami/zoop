
import importlib
import importlib.util
from typing import Any

from zoop.config import ConfigError


def load_class(import_path: str, label: str) -> type[Any]:
    """Import a bridge class from a 'package.module:Class' path."""
    module_name, sep, cls_name = import_path.partition(":")
    if not sep:
        raise ConfigError(f"invalid import_path (expected 'module:Class'): {import_path}")
    try:
        module = importlib.import_module(module_name)
        return getattr(module, cls_name)
    except (ImportError, AttributeError) as e:
        raise ConfigError(f"cannot import {label} = '{import_path}': {e}") from e


def import_module_or_file(path: str):
    """Import a plugin given a dotted module name or a path to a .py file."""
    if path.endswith(".py"):
        spec = importlib.util.spec_from_file_location("zoop_plugin", path)
        if spec is None or spec.loader is None:
            raise ConfigError(f"cannot load plugin file: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    try:
        return importlib.import_module(path)
    except ImportError as e:
        raise ConfigError(f"cannot import plugin '{path}': {e}") from e
