from typing import Protocol
from zoop.reading import Reading

class EmptyReadings(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class StorageBackend(Protocol):

    def write(self, *, readings: list[Reading]) -> str:
        pass

    def read (self, *, query: str) -> list[Reading]:
        pass
