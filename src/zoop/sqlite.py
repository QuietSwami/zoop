# SQLite metadata store

from zoop.contracts.metadata import CatalogEntry
import sqlite3 as sq
import json


def _row_to_entry(row: list) -> CatalogEntry:
    """Transforms a list of values, to CatalogEntry."""
    return CatalogEntry(
        path=row["path"],
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

class SQLiteMetadata:
    def __init__(self, path: str):
        try:
            self.conn = sq.connect(path)
            cur = self.conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS metadata(
                    path TEXT PRIMARY KEY, row_count INTEGER,
                    ts_min INTEGER, ts_max INTEGER, devices TEXT,
                    metrics TEXT, created_at INTEGER
                )""")
            self.conn.row_factory = dict_factory

        except e:
            log.error(f"SQLiteMetadata - Error: {e}")

    def store(self, entry: CatalogEntry) -> None:
        """Stores a metadata entry."""
        cur = self.conn.cursor()
        insert = "INSERT INTO metadata VALUES (?, ?, ?, ?, ?, ?, ?)"
        cur.execute(insert,
            (
                entry.path,
                entry.row_count,
                entry.ts_min,
                entry.ts_max,
                json.dumps(entry.devices), # other approaches won't deal with commas in device IDs - in the very odd case...
                json.dumps(entry.metrics), # Same here ....
                entry.created_at
            )
        )
        self.conn.commit()

    def list_entries(self) -> list[CatalogEntry]:
        list = "SELECT * FROM metadata"
        cur = self.conn.cursor()
        res = cur.execute(list)
        res = res.fetchall()
        return [_row_to_entry(row) for row in res]

    def close(self) -> None:
        self.conn.close()
