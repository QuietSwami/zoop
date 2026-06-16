from typing import Protocol

from zoop.contracts.reading import Reading


class Processor(Protocol):

    def run(self, input: list[Reading]):
        pass
