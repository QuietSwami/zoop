import asyncio
import types

import aiomqtt
import msgspec
import pytest

from zoop.bridges.mqtt import MQTTBridge
from zoop.contracts.handoff import HandoffRecord


class FakeProducer:
    def __init__(self) -> None:
        self.appended: list[bytes] = []
        self.committed = 0

    def append(self, payload: bytes) -> None:
        self.appended.append(payload)

    def commit(self) -> None:
        self.committed += 1

    def seal(self):  # pragma: no cover - not exercised
        return None

    def close(self) -> None:  # pragma: no cover - not exercised
        pass


class FakeMessage:
    def __init__(self, topic_value: str, payload: bytes) -> None:
        self.topic = types.SimpleNamespace(value=topic_value)
        self.payload = payload


class FakeClient:
    def __init__(self, messages: list[FakeMessage]) -> None:
        self._messages = messages

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def subscribe(self, *args, **kwargs) -> None:
        return None

    @property
    def messages(self):
        return self._aiter()

    async def _aiter(self):
        for message in self._messages:
            yield message


@pytest.mark.unit
def test_options_defaults():
    bridge = MQTTBridge(FakeProducer(), host="broker")
    assert bridge._host == "broker"
    assert bridge._port == 1883
    assert bridge._topic == "zoop/#"


@pytest.mark.unit
def test_missing_host_raises():
    with pytest.raises(msgspec.ValidationError):
        MQTTBridge(FakeProducer())


@pytest.mark.integration
def test_run_persists_message_then_reconnects(monkeypatch):
    producer = FakeProducer()
    bridge = MQTTBridge(producer, host="broker")

    calls = {"n": 0}

    def client_factory(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeClient([FakeMessage("zoop/sensorA/temp", b"payload")])
        # Second connect fails -> exercises the reconnect/except branch.
        raise aiomqtt.MqttError("connection refused")

    monkeypatch.setattr(aiomqtt, "Client", client_factory)

    async def drive() -> None:
        task = asyncio.ensure_future(bridge.run())
        await asyncio.sleep(0.05)  # let it consume the message + hit the reconnect sleep
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(drive())

    assert calls["n"] >= 2  # connected once, tried to reconnect once
    assert len(producer.appended) == 1
    record = msgspec.msgpack.decode(producer.appended[0], type=HandoffRecord)
    assert record.source == "sensorA"  # topic.split("/")[1]
    assert record.payload == b"payload"
