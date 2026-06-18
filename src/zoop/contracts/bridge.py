# Contract used to implement new transport bridges.

from typing import Any, ClassVar, Protocol

import msgspec

from zoop.contracts.handoff import LogProducer

# Defined here (module scope) where `type` is the builtin — inside the class the
# `type` attribute below would shadow it.
OptionsSchema = type[msgspec.Struct]


class TransportBridge(Protocol):
    type: ClassVar[str]
    options_schema: ClassVar[OptionsSchema]

    def __init__(self, producer: LogProducer, **options: Any) -> None: ...
    async def run(self) -> None: ...
