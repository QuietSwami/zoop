# SQLite metadata store

import json
import sqlite3 as sq
from typing import Iterator

from zoop.contracts.catalog import CatalogEntry


def _row_to_entry(row: dict) -> CatalogEntry:
    """Transforms a list of values, to CatalogEntry."""
    return CatalogEntry(
        location=row["location"],
        backend=row["backend"],
        row_count=row["row_count"],
        ts_min=row["ts_min"],
        ts_max=row["ts_max"],
        devices=tuple(json.loads(row["devices"])),
        metrics=tuple(json.loads(row["metrics"])),
        created_at=row["created_at"]
    )

def dict_factory(cursor, row):
    """Transforms the tuple output from SQLite into a Dict - where the keys are the column names.
    This was done to facilitate with future changes in table formats.
    """
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

class SQLiteCatalog:
    def __init__(self, path: str):
        self.conn = sq.connect(path)
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS metadata(
                location TEXT PRIMARY KEY, backend TEXT,
                row_count INTEGER, ts_min INTEGER,
                ts_max INTEGER, devices TEXT,
                metrics TEXT, created_at INTEGER
            )""")
        self.conn.row_factory = dict_factory


    def store(self, entry: CatalogEntry) -> None:
        """Stores a metadata entry."""
        cur = self.conn.cursor()
        insert = "INSERT INTO metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        cur.execute(insert,
            (
                entry.location,
                entry.backend,
                entry.row_count,
                entry.ts_min,
                entry.ts_max,
                json.dumps(entry.devices), # other approaches won't deal with commas in device IDs - in the very odd case...
                json.dumps(entry.metrics), # Same here ....
                entry.created_at
            )
        )
        self.conn.commit()

    def find(
        self,
        *,
        ts_from: int | None = None,
        ts_to: int | None = None,
        limit: int | None = None,
    ) -> Iterator[CatalogEntry]:
        clauses: list[str] = []
        params: list = []

        if ts_from is not None:
            clauses.append("ts_min <= ?")
            params.append(ts_from)
        if ts_to is not None:
            clauses.append("ts_max >= ?")
            params.append(ts_to)

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM metadata{where} ORDER BY ts_min"

        if limit is not None:
            sql +=" LIMIT ?"
            params.append(limit)

        cur = self.conn.cursor()
        for row in cur.execute(sql, params):
            yield _row_to_entry(row)

    def list_entries(self) -> list[CatalogEntry]:
        """Depreceated - DO NOT USE"""
        list = "SELECT * FROM metadata"
        cur = self.conn.cursor()
        res = cur.execute(list)
        fetched = res.fetchall()
        return [_row_to_entry(row) for row in fetched]

    def close(self) -> None:
        self.conn.close()

    def kind(self) -> str:
        return "sqlite"
