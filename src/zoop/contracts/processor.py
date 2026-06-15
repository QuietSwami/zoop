from typing import Protocol
from zoop.contract.reading import Reading

class Processor:

    def run(self, input: list[Reading]):
        pass
