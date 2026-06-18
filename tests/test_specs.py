import json
from pathlib import Path

import pytest

from zoop.contracts.mapping import SpecError
from zoop.normalize.specs import SpecRegistry


def _spec_dict(source: str) -> dict:
    return {
        "version": "1",
        "source": source,
        "device_key": "dev",
        "ts_key": "t",
        "ts_unit": "s",
        "fields": [{"key": "temperature", "type": "double", "unit": "Cel"}],
        "tags": {"location": "barn-3"},
        "idem_key": None,
    }


def _write(dir: Path, name: str, source: str) -> None:
    (dir / name).write_text(json.dumps(_spec_dict(source)))


@pytest.mark.integration
def test_loads_specs_from_dir(tmp_path: Path):
    _write(tmp_path, "weather.json", "weather")
    _write(tmp_path, "soil.json", "soil")

    reg = SpecRegistry(tmp_path)
    assert set(reg.list()) == {"weather", "soil"}
    assert reg.get("weather").source == "weather"


@pytest.mark.integration
def test_duplicate_source_raises(tmp_path: Path):
    _write(tmp_path, "a.json", "weather")
    _write(tmp_path, "b.json", "weather")
    with pytest.raises(SpecError):
        SpecRegistry(tmp_path)


@pytest.mark.integration
def test_unknown_spec_lookup_raises(tmp_path: Path):
    _write(tmp_path, "weather.json", "weather")
    reg = SpecRegistry(tmp_path)
    with pytest.raises(SpecError):
        reg.get("does-not-exist")


@pytest.mark.integration
def test_empty_dir_raises(tmp_path: Path):
    with pytest.raises(SpecError):
        SpecRegistry(tmp_path)


@pytest.mark.integration
def test_missing_dir_raises(tmp_path: Path):
    with pytest.raises(SpecError):
        SpecRegistry(tmp_path / "nope")


@pytest.mark.integration
def test_invalid_spec_json_raises(tmp_path: Path):
    (tmp_path / "bad.json").write_text("{ not valid json")
    with pytest.raises(SpecError):
        SpecRegistry(tmp_path)


@pytest.mark.integration
def test_invalid_spec_schema_raises(tmp_path: Path):
    # Valid JSON but missing required fields.
    (tmp_path / "bad.json").write_text(json.dumps({"version": "1"}))
    with pytest.raises(SpecError):
        SpecRegistry(tmp_path)
