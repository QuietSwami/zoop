# Append Log


import itertools
import os
import struct
import threading
import zlib
from collections.abc import Iterator
from pathlib import Path

from zoop.utils.clock import now_micros

# 8 byte record header format -> written in fron of every payload
# Identifies where the record ends.
HEADER = struct.Struct(">II")
_seq = itertools.count()


def iter_records(path: Path) -> Iterator[bytes]:
    """Framed-record reader; stops at EOF or a torn/corrupt tail."""
    with open(path, "rb") as f:
        while True:
            head = f.read(8)
            if len(head) < 8:
                break
            length, crc = HEADER.unpack(head)
            payload = f.read(length)
            if len(payload) < length or zlib.crc32(payload) & 0xFFFFFFFF != crc:
                break
            yield payload

class AppendLog:

    def __init__(
        self,
        dir: Path,
        max_bytes: int | None = None,
        timeout: int = 300 # 5 minutes
    ):
        self.dir = Path(dir)
        self.max_bytes = max_bytes

        # create directory if it doesn't exit
        self.dir.mkdir(parents=True, exist_ok=True)

        # current active file
        self._active = self.dir / "active.log"

        # check if there's an exisiting file -
        existing = [int(p.stem) for p in self.dir.glob("*.sealed") if p.stem.isdigit()]

        # start sequence from last file, if it exists.
        self._seq = itertools.count(max(existing, default=0) + 1)

        # recover the last file, if it exists.
        self._recover()

        # lock to be used by write and seal operations
        self._lock = threading.Lock()

        # start the append log
        # O_WRONLY = write only
        # O_CREAT = create file if it doesn't exist
        # O_APPEND = every write automatically goes to the end of file.
        # 0o644 = Unix permisions if the file is created.
        self._fd = os.open(self._active, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        self._timeout = timeout
        self._last_seal = now_micros()

    def _recover(self) -> None:
        """Recovers any file if the process stops."""
        if not self._active.exists() or self._active.stat().st_size == 0:
            return

        good = sum(8 + len(r) for r in iter_records(self._active)) # bytes of valid records
        if good < self._active.stat().st_size:
            os.truncate(self._active, good) # drop tail of bad records.
        if good > 0:
            self._active.rename(self.dir / f"{next(self._seq):08d}.sealed")

    def append(
        self,
        payload: bytes
    ) -> None:
        """Appends a payload to the end of the file."""
        rec = HEADER.pack(len(payload), zlib.crc32(payload) & 0xFFFFFFFF) + payload
        with self._lock:
            os.write(self._fd, rec)
            size = os.fstat(self._fd).st_size
        # Size-based rotation runs OUTSIDE the lock: seal() takes the same
        # non-reentrant lock, so calling it while holding the lock would deadlock.
        if self.max_bytes is not None and size >= self.max_bytes:
            self.seal()

    def commit(self) -> None:
        """Forces the OS to flush the file to the physical disk"""
        with self._lock:
            os.fsync(self._fd)

    def seal(self) -> Path | None:
        """Atomically rotate the active file into an immutable sealed segment.
        Returns the sealed path (safe to read), or None if there was nothing"""

        with self._lock:
            os.fsync(self._fd)
            if os.fstat(self._fd).st_size == 0:
                return None

            os.close(self._fd)
            sealed = self.dir / f"{next(self._seq):08d}.sealed"
            self._active.rename(sealed)
            self._fd = os.open(self._active, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)  # fresh active
            self._last_seal = now_micros()
            return sealed

    def seal_if_stale(self, timeout: int) -> None:
        if now_micros() - self._last_seal >= timeout:
            self.seal()

    def close(self) -> None:
        os.fsync(self._fd)
