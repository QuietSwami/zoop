import asyncio

import msgspec
import pytest

from zoop.bridges.http import HTTPBridge
from zoop.contracts.handoff import HandoffRecord


class FakeProducer:
    def __init__(self, fail: bool = False) -> None:
        self.appended: list[bytes] = []
        self.committed = 0
        self.fail = fail

    def append(self, payload: bytes) -> None:
        if self.fail:
            raise OSError("disk full")
        self.appended.append(payload)

    def commit(self) -> None:
        self.committed += 1

    def seal(self):  # pragma: no cover - not exercised
        return None

    def close(self) -> None:  # pragma: no cover - not exercised
        pass


class FakeRequest:
    def __init__(self, source: str, body: bytes) -> None:
        self.match_info = {"source": source}
        self._body = body

    async def read(self) -> bytes:
        return self._body


@pytest.mark.unit
def test_options_defaults():
    bridge = HTTPBridge(FakeProducer(), host="127.0.0.1")
    assert bridge.opts.host == "127.0.0.1"
    assert bridge.opts.port == 8080
    assert bridge.opts.path == "/ingest"


@pytest.mark.unit
def test_missing_host_raises():
    with pytest.raises(msgspec.ValidationError):
        HTTPBridge(FakeProducer())


@pytest.mark.unit
def test_handle_empty_body_returns_400():
    bridge = HTTPBridge(FakeProducer(), host="h")
    resp = asyncio.run(bridge._handle(FakeRequest("devA", b"")))
    assert resp.status == 400


@pytest.mark.unit
def test_handle_persists_record_and_returns_204():
    producer = FakeProducer()
    bridge = HTTPBridge(producer, host="h")
    resp = asyncio.run(bridge._handle(FakeRequest("devA", b'{"x":1}')))

    assert resp.status == 204
    assert producer.committed == 1
    assert len(producer.appended) == 1
    record = msgspec.msgpack.decode(producer.appended[0], type=HandoffRecord)
    assert record.source == "devA"
    assert record.payload == b'{"x":1}'


@pytest.mark.unit
def test_handle_storage_error_returns_503():
    bridge = HTTPBridge(FakeProducer(fail=True), host="h")
    resp = asyncio.run(bridge._handle(FakeRequest("devA", b'{"x":1}')))
    assert resp.status == 503
    assert resp.headers["Retry-After"] == "5"
