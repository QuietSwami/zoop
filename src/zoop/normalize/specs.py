from pathlib import Path

import msgspec

from zoop.contracts.mapping import MappingSpec, SpecError


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
