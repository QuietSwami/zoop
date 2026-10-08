from typing import Any, ClassVar, Protocol

import msgspec
import pyarrow as pa

from zoop.contracts.model import Reading


class EmptyReadings(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

OptionsSchema = type[msgspec.Struct]

class StorageBackend(Protocol):
    type: ClassVar[str]
    options_schema: ClassVar[OptionsSchema]

    def __init__(self, path: str, **options: Any) -> None: ...
    def write(self, *, readings: list[Reading]) -> str: ...
    def read (self, *, location: str) -> pa.Table: ...
    def kind(self) -> str: ...
