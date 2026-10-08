from pathlib import Path
from typing import Any, ClassVar

import pytest

from zoop.config import BridgeConfig, ConfigError
from zoop.contracts.handoff import LogProducer
from zoop.bridges.registry import BridgeRegistry


class FakeBridge:
    type: ClassVar[str] = "fake"

    def __init__(self, producer: LogProducer, **options: Any) -> None:
        self.producer = producer
        self.options = options

    async def run(self) -> None:  # pragma: no cover - not exercised
        return None


class OtherBridge:
    type: ClassVar[str] = "other"

    def __init__(self, producer: LogProducer, **options: Any) -> None:
        self.producer = producer
        self.options = options

    async def run(self) -> None:  # pragma: no cover
        return None


@pytest.mark.unit
def test_register_and_all():
    reg = BridgeRegistry()
    reg.register(FakeBridge)
    assert reg.all() == {"fake": FakeBridge}


@pytest.mark.unit
def test_duplicate_register_raises():
    reg = BridgeRegistry()
    reg.register(FakeBridge)
    with pytest.raises(ValueError):
        reg.register(FakeBridge)


@pytest.mark.integration
def test_create_builds_bridge_instances(tmp_path: Path, monkeypatch):
    # create() writes per-bridge logs under ./logs; run from tmp_path.
    monkeypatch.chdir(tmp_path)
    reg = BridgeRegistry()
    reg.register(FakeBridge)
    reg.register(OtherBridge)

    configs = [
        BridgeConfig(type="fake", id="a", options={"k": "v"}),
        BridgeConfig(type="other", id="b"),
    ]
    bridges, logs = reg.create(configs)

    assert len(bridges) == 2
    assert isinstance(bridges[0], FakeBridge)
    assert bridges[0].options == {"k": "v"}
    assert isinstance(bridges[1], OtherBridge)
    # create() also returns the per-bridge append-logs, wired into each bridge.
    assert len(logs) == 2
    assert bridges[0].producer is logs[0]
    assert bridges[1].producer is logs[1]
    # producer was wired in and a per-bridge log dir was created.
    assert (tmp_path / "logs" / "fake-a").is_dir()
    assert (tmp_path / "logs" / "other-b").is_dir()


@pytest.mark.integration
def test_create_unknown_type_raises_config_error(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reg = BridgeRegistry()
    reg.register(FakeBridge)
    with pytest.raises(ConfigError):
        reg.create([BridgeConfig(type="ghost", id="x")])
