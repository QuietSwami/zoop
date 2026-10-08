import sys
from pathlib import Path

import pytest

from zoop.cli import load_config, parse_args
from zoop.config import ConfigError

VALID_TOML = """
[[bridges]]
type = "dummy"
id = "1"

[storage]
type = "parquet"
path = "data"
"""


@pytest.mark.integration
def test_load_config_reads_valid_toml(tmp_path: Path):
    cfg_file = tmp_path / "zoop.toml"
    cfg_file.write_text(VALID_TOML)
    config = load_config(cfg_file)
    assert config.bridges[0].type == "dummy"
    assert config.bridges[0].id == "1"
    assert config.storage is not None
    assert config.storage.type == "parquet"


@pytest.mark.unit
def test_load_config_missing_file_raises(tmp_path: Path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.toml")


@pytest.mark.integration
def test_load_config_malformed_toml_raises(tmp_path: Path):
    cfg_file = tmp_path / "bad.toml"
    cfg_file.write_text("this is = = not toml")
    with pytest.raises(ConfigError):
        load_config(cfg_file)


@pytest.mark.integration
def test_load_config_validation_error_raises(tmp_path: Path):
    cfg_file = tmp_path / "invalid.toml"
    # bridge missing required `id`
    cfg_file.write_text('[[bridges]]\ntype = "dummy"\n')
    with pytest.raises(ConfigError):
        load_config(cfg_file)


@pytest.mark.unit
def test_parse_args_run_subcommand(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["zoop", "run", "--config", "x.toml", "--log-level", "warn"]
    )
    args = parse_args()
    assert args.command == "run"
    assert args.config == Path("x.toml")
    assert args.log_level == "warn"


@pytest.mark.unit
def test_parse_args_check_subcommand_with_plugins(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["zoop", "check", "--config", "y.toml", "--plugin", "pkg.mod"],
    )
    args = parse_args()
    assert args.command == "check"
    assert args.config == Path("y.toml")
    assert args.plugin == ["pkg.mod"]
