# Contract used to implement new transport bridges.

from typing import Any, ClassVar, Protocol

from zoop.contracts.handoff import LogProducer


class TransportBridge(Protocol):
    type: ClassVar[str]

    def __init__(self, producer: LogProducer, **options: Any) -> None: ...
    async def run(self) -> None: ...
