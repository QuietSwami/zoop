# MappingSpec

from typing import Literal, Mapping

import msgspec


class SpecError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class FieldSpec(msgspec.Struct, frozen=True):
    key: str
    type: Literal["double", "int", "bool", "str"]
    unit: str | None = None

class MappingSpec(msgspec.Struct, frozen=True):
    version: str
    source: str
    device_key: str # which key defines the device ID
    ts_key: str # which key defines the timestamp columns
    ts_unit: Literal["s", "ms", "us", "iso"] # ms | s | iso | microsecs | other
    fields: list[FieldSpec]
    tags: Mapping[str, str]
    idem_key: str | None # does the device provide its own idem key? (OPTIONAL)
