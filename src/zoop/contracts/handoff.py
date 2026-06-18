# Handoff contract: the record shape and the producer/consumer protocols.

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from collections.abc import Iterator


@dataclass(frozen=True)
class HandoffRecord:
    source: str
    payload: bytes
    received_at: int  # microsecs since epoch


class LogProducer(Protocol):
    """Write-side of the handoff log."""

    def append(self, payload: bytes) -> None: ...

    def commit(self) -> None: ...

    def seal(self) -> Path | None: ...

    def close(self) -> None: ...


class LogConsumer(Protocol):
    """Read-side of the handoff log."""

    def sealed(self) -> list[Path]: ...

    def read(self, segment: Path) -> Iterator[bytes]: ...

    def discard(self, segment: Path) -> None: ...
