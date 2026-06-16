# MappingSpec

from datetime import datetime
from pathlib import Path
from typing import Literal, Mapping

import msgspec

from zoop.contracts.reading import Field, Sample


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

class SpecRegistry:
    def __init__(
        self,
        path: Path
    ) -> None:
        self.path = path
        self._registry: dict[str, MappingSpec] = self.load()

    def load(self) -> dict[str, MappingSpec]:
        """Loads all the spec mappings into memory."""
        if not self.path.is_dir():
            raise SpecError(f"Spec directory not found: {self.path}")

        files = sorted(self.path.glob("*.json"))
        if not files:
            raise SpecError(
                """No Mapping Spec has been found,
                please create one before ingesting data"""
            )

        specs: dict[str, MappingSpec] = {}
        for spec in sorted(self.path.glob("*.json")):
            try:
                sp = msgspec.json.decode(spec.read_bytes(), type=MappingSpec)
            except (msgspec.ValidationError, msgspec.DecodeError) as e:
                raise SpecError(f"{spec}: invalid mapping spec: {e}") from e
            if sp.source in specs:
                raise SpecError(f"Duplicate Mapping Specs: {sp.source}: {spec}")
            specs[sp.source] = sp
        return specs

    def get(self, name: str) -> MappingSpec:
        """Returns a spec mapping from the registry."""
        if name in self._registry:
            return self._registry[name]
        else:
            raise SpecError(f"No spec with name {name} has been found")

    def list(self) -> dict[str, MappingSpec]:
        return self._registry

def apply_spec(
    data: dict,
    spec: MappingSpec
) -> Sample:
    return Sample(
        device_id=data[spec.device_key],
        ts=datetime.strptime(data[spec.ts_key], spec.ts_unit),
        tags={tag_key:data[tag_key] for tag_key in spec.tags},
        fields=[Field(
            field.key,
            data[field],
            field.type,
            field.unit,
        ) for field in spec.fields],
        idempotency_key=data[spec.idem_key] if spec.idem_key else None,
    )
