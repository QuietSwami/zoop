# zoop 

A small, fast, IoT-focused ingestion engine. zoop takes heterogenous device data, coerces it into one canonical format,
lands it as columnar files, and extracts metadata into a database of your choice - all from a single embedded process with no required external services.

> *Status*: early design phase. The architecture below is the target; the code is being built up one vertical slice at a time. **Expect breaking changes.**

## Why

The modern lakehouse stack (Icebert + a catalog + an engine + a broker) is powerful but heavy, which is wrong for an IoT gateway to work in resource constricted environements.
zoop is the opposite: do *less*. for IoT specifically, in the smallest footprint that still gives you durable, queryable, well-described data.

Zoop grew out of a problem I kept running into during my PhD: there was no easy, performant, and adaptable way to ingest the messy variety of IoT data — in settings where performance genuinely matters. The need became concrete while I was building a data cooperative framework aimed at helping farmers in resource-constrained settings create and share data with one another. The hardest part wasn't the cooperative model itself; it was the plumbing. Every kind of device demanded its own stack of services just to ingest the data, coerce it into a common format, extract its metadata, and store it. Zoop is my attempt to collapse that sprawl into a single, small, fast engine.

It's inspired by DuckLake's "metadata in a SQL database, data in columnar files" insight, but zoop is **not** a table format - it's the ingestion platform around one:
protocol bridges, a canonical IoT data model, and metadata extraction. The storage is deliberately boring; the value is the pipeline and the model.

## How it works

```ascii
Device (MQTT/HTTP/Other) -> Bridge -> Coerce -> Canonical reading (device_id, ts, metric, value, unit, quality, tags) -> write -> Parquet (local)
                                |
                                -> metadata store (SQLite as default)
```

A bridge speaks a device protocol, and emits canonical `readings`. The core batches them into Parquet (append-only, partitioned by time + device) 
and records both the file catalog and extracted semantic metadata (devices, metricts, units, time ranges) into the metadata store.


## Principles

- **Embedded first.** One process, one SQLite file, a directory of Parquet. No Kafka, no Postgress, no object-store server required to run.
- **Distribute by replication.** A node is self-contained and works offline. "Distrbuted" means running many nodes - not a cluster.
- **Pluggable by contract**: Everyting swappable sits behind a small interface:
    - `SourceAdapter` - protocol bridges (HTTP, MQTT, ...; third-party welcome)
    - `MetadataStore` - SQLite (default), Postgres, DuckDB, OpenMetadata, etc.
    - `StorageBacked` - local parque now; object store/Iceberg later
- **Canonical model.** Heterogeneous paylodas become one `Reading` shape - the thing that makes pooled IoT data uniform and queryable.
- **Append-only hot path.** IoT is append-heavy; corrections and compaction happen out of band.
- **Small by omission**. Add a broker, a central tier, or richer catalog only when a real need shows up.

## *Optional* Central tier

Nodes can sync their Parque and push catalog rows to a central store exposed as Apache Icebert, so the broader analytics ecosystem can query
pooled data. This additive - a node never depends on it.

## Non-goals

- Not a general-purpose lakehouse or table format (use DuckLake/Iceberg for that).
- Not a stream-processing engine.
- No update-heavy OLTP workloads.

## Stack

Python 

## License

TBD
