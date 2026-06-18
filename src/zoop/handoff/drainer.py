# Segment Drainer


import os
from collections.abc import Iterator
from pathlib import Path

from zoop.handoff.append_log import iter_records


class SegmentDrainer:
    """Scans a root dir for sealed segments across ALL bridge subdirs"""

    def __init__(self, root: Path):
        self.root = root

    def sealed(self) -> list[Path]:
        return sorted(self.root.glob("*/*.sealed"))

    @staticmethod
    def read(segment: Path) -> Iterator[bytes]:
        return iter_records(segment)

    @staticmethod
    def discard(segment: Path) -> None:
        os.remove(segment)
