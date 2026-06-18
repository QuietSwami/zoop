# Contract used to implement new transport bridges.

from dataclasses import dataclass
from typing import Mapping, Protocol

from zoop.handoff.append_log import AppendLog

class TransportBridge(Protocol):
    type: str
    id: str
    producer: AppendLog

    async def run(self) -> None:
        pass
