# ADR 0001: Use DuckDB and Parquet

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

ShopSignal needs a practical storage and query foundation for a local data engineering pipeline. The pipeline processes Olist CSVs and simulated daily orders through Bronze, Silver, and Gold layers, with dbt transformations and downstream analytical consumers.

The initial project prioritizes reproducibility, simplicity, low operational overhead, and the ability to work locally.

## Decision

Use Parquet as the primary storage format for analytical datasets and DuckDB as the local analytical query engine.

Parquet provides columnar storage with schema and compression support. DuckDB supports analytical SQL queries over Parquet without requiring a continuously running database server.

Python will coordinate ingestion and processing. dbt will manage Gold-layer analytical transformations. Dagster will orchestrate pipeline execution as that functionality is implemented.

## Alternatives considered

### Apache Spark

Spark is a strong choice for distributed processing and workloads that exceed the practical limits of a single machine.

It was not selected initially because the project's current requirements do not justify the additional cluster and execution complexity. DuckDB is simpler for local analytical workloads, but it does not replace Spark when distributed processing becomes necessary.

### PostgreSQL

PostgreSQL is well suited to transactional workloads, concurrent application access, and frequently updated records.

It was not selected as the primary analytical storage foundation because the initial project is centered on file-based analytical processing rather than transactional application data. PostgreSQL could still be introduced later if the application needs transactional persistence or a shared database service.

### CSV as the primary storage format

CSV is easy to inspect and exchange, but it provides weaker type handling and is generally less efficient for analytical scans than columnar storage.

CSV remains appropriate for source inputs and small test fixtures.

## Consequences

### Benefits

- Local analytical queries without managing a database server.
- Portable Parquet datasets.
- SQL-based analytical transformations.
- Low initial infrastructure and operational overhead.

### Tradeoffs

- DuckDB is not a general-purpose replacement for a transactional, multi-user database.
- Local execution is constrained by machine resources.
- File-based pipelines need explicit conventions for schema evolution, partitioning, and safe writes.
- Very large workloads or distributed processing requirements may justify Spark or another execution engine later.
- Parquet does not itself provide the transactional and concurrency guarantees of a database.

## Revisit conditions

Reconsider this decision if workloads exceed local resource limits, concurrent writers become a significant requirement, transactional updates become central, or production deployment requires distributed processing.