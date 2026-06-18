import struct
import zlib
from pathlib import Path

import pytest

from zoop.handoff.append_log import HEADER, AppendLog, iter_records


def _frame(payload: bytes) -> bytes:
    return HEADER.pack(len(payload), zlib.crc32(payload) & 0xFFFFFFFF) + payload


@pytest.mark.integration
def test_round_trip_append_seal_read(tmp_path: Path):
    log = AppendLog(tmp_path)
    payloads = [b"alpha", b"beta", b"gamma"]
    for p in payloads:
        log.append(p)
    log.commit()
    sealed = log.seal()
    log.close()

    assert sealed is not None
    assert sealed.exists()
    assert list(iter_records(sealed)) == payloads


@pytest.mark.integration
def test_seal_empty_returns_none(tmp_path: Path):
    log = AppendLog(tmp_path)
    assert log.seal() is None
    log.close()


@pytest.mark.integration
def test_sealed_segments_get_increasing_sequence(tmp_path: Path):
    log = AppendLog(tmp_path)
    log.append(b"one")
    first = log.seal()
    log.append(b"two")
    second = log.seal()
    log.close()

    assert first is not None and second is not None
    assert first.name == "00000001.sealed"
    assert second.name == "00000002.sealed"


@pytest.mark.integration
def test_recovery_seals_leftover_active_log(tmp_path: Path):
    # Simulate a crash: an active.log left behind with valid records,
    # never sealed. A new AppendLog over the same dir must recover it.
    active = tmp_path / "active.log"
    active.write_bytes(_frame(b"r1") + _frame(b"r2"))

    log = AppendLog(tmp_path)
    log.close()

    sealed = sorted(tmp_path.glob("*.sealed"))
    assert len(sealed) == 1
    assert list(iter_records(sealed[0])) == [b"r1", b"r2"]
    # active.log was rotated away (a fresh empty one is created).
    assert (tmp_path / "active.log").stat().st_size == 0


@pytest.mark.integration
def test_recovery_trims_torn_tail(tmp_path: Path):
    # Two good records followed by a truncated/torn third record.
    active = tmp_path / "active.log"
    good = _frame(b"r1") + _frame(b"r2")
    torn = struct.pack(">II", 100, 12345) + b"short"  # claims 100 bytes, has 5
    active.write_bytes(good + torn)

    log = AppendLog(tmp_path)
    log.close()

    sealed = sorted(tmp_path.glob("*.sealed"))
    assert len(sealed) == 1
    # Only the two intact records survive; torn tail dropped.
    assert list(iter_records(sealed[0])) == [b"r1", b"r2"]


@pytest.mark.integration
def test_recovery_trims_bad_crc_tail(tmp_path: Path):
    active = tmp_path / "active.log"
    good = _frame(b"r1")
    payload = b"corrupt"
    bad_crc = struct.pack(">II", len(payload), 0) + payload  # crc=0, wrong
    active.write_bytes(good + bad_crc)

    log = AppendLog(tmp_path)
    log.close()

    sealed = sorted(tmp_path.glob("*.sealed"))
    assert list(iter_records(sealed[0])) == [b"r1"]


@pytest.mark.integration
def test_recovery_continues_sequence_after_existing_sealed(tmp_path: Path):
    # An existing sealed segment plus a leftover active log: the recovered
    # segment must get the next sequence number, not collide.
    (tmp_path / "00000005.sealed").write_bytes(_frame(b"old"))
    (tmp_path / "active.log").write_bytes(_frame(b"new"))

    log = AppendLog(tmp_path)
    log.close()

    names = sorted(p.name for p in tmp_path.glob("*.sealed"))
    assert names == ["00000005.sealed", "00000006.sealed"]


@pytest.mark.integration
def test_iter_records_stops_at_short_header(tmp_path: Path):
    f = tmp_path / "seg"
    f.write_bytes(_frame(b"ok") + b"\x00\x00\x00")  # trailing partial header
    assert list(iter_records(f)) == [b"ok"]


@pytest.mark.integration
def test_append_after_seal_writes_to_fresh_active(tmp_path: Path):
    log = AppendLog(tmp_path)
    log.append(b"first")
    log.seal()
    log.append(b"second")
    second = log.seal()
    log.close()

    assert second is not None
    assert list(iter_records(second)) == [b"second"]
