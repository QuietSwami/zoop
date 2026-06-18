import zlib
from pathlib import Path

import pytest

from zoop.handoff.append_log import HEADER
from zoop.handoff.drainer import SegmentDrainer


def _frame(payload: bytes) -> bytes:
    return HEADER.pack(len(payload), zlib.crc32(payload) & 0xFFFFFFFF) + payload


def _seg(path: Path, *payloads: bytes) -> None:
    path.write_bytes(b"".join(_frame(p) for p in payloads))


@pytest.mark.integration
def test_sealed_finds_across_bridge_subdirs(tmp_path: Path):
    (tmp_path / "mqtt-1").mkdir()
    (tmp_path / "http-2").mkdir()
    _seg(tmp_path / "mqtt-1" / "00000001.sealed", b"a")
    _seg(tmp_path / "http-2" / "00000001.sealed", b"b")
    # active logs (not sealed) must be ignored
    (tmp_path / "mqtt-1" / "active.log").write_bytes(_frame(b"x"))

    drainer = SegmentDrainer(tmp_path)
    found = drainer.sealed()
    assert len(found) == 2
    assert all(p.suffix == ".sealed" for p in found)


@pytest.mark.integration
def test_sealed_empty_when_no_segments(tmp_path: Path):
    (tmp_path / "mqtt-1").mkdir()
    assert SegmentDrainer(tmp_path).sealed() == []


@pytest.mark.integration
def test_read_yields_records_in_order(tmp_path: Path):
    (tmp_path / "b").mkdir()
    seg = tmp_path / "b" / "00000001.sealed"
    _seg(seg, b"one", b"two", b"three")

    drainer = SegmentDrainer(tmp_path)
    assert list(drainer.read(seg)) == [b"one", b"two", b"three"]


@pytest.mark.integration
def test_discard_removes_file(tmp_path: Path):
    (tmp_path / "b").mkdir()
    seg = tmp_path / "b" / "00000001.sealed"
    _seg(seg, b"x")

    drainer = SegmentDrainer(tmp_path)
    assert seg.exists()
    drainer.discard(seg)
    assert not seg.exists()
    assert drainer.sealed() == []
