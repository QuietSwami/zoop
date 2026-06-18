from typing import Protocol

from zoop.contracts.model import Reading


class Processor(Protocol):

    def run(self, input: list[Reading]):
        pass
