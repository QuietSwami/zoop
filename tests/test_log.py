import logging

import pytest

from zoop.log import setup_logging


@pytest.fixture
def captured_basic_config(monkeypatch):
    captured: dict = {}

    def fake_basic_config(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)
    return captured


@pytest.mark.unit
@pytest.mark.parametrize(
    "level,expected",
    [
        ("info", logging.INFO),
        ("warn", logging.WARNING),
        ("error", logging.ERROR),
    ],
)
def test_setup_logging_maps_levels(captured_basic_config, level, expected):
    setup_logging(level)
    assert captured_basic_config["level"] == expected


@pytest.mark.unit
def test_setup_logging_unknown_level_defaults_to_info(captured_basic_config):
    setup_logging("nonsense")
    assert captured_basic_config["level"] == logging.INFO


@pytest.mark.unit
def test_setup_logging_sets_format(captured_basic_config):
    setup_logging("info")
    assert "%(levelname)" in captured_basic_config["format"]
