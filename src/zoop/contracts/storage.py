from typing import Protocol

import pyarrow as pa

from zoop.contracts.model import Reading


class EmptyReadings(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class StorageBackend(Protocol):

    def write(self, *, readings: list[Reading]) -> str:
        """Writes a list of Reading, and returns the batch's location as a string"""
        pass

    def read (self, *, location: str) -> pa.Table:
        """Reads a batch from a location string.
        Keep returns columnar - DO NOT TRANSFORM TO list[Reading].
        This is done in case the user intends to use the data.
        """
        pass

    def kind(self) -> str:
        """returns the name of the backend."""
        pass
