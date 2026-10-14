"""Bronze ingestion from raw CSV files to Parquet."""

import logging
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import duckdb

from shopsignal.config import Settings, settings

logger = logging.getLogger(__name__)


def ingest_table(
    table: str,
    config: Settings = settings,
    ingest_date: date | None = None,
    batch_id: str | None = None,
) -> Path:
    """Ingest one CSV table into a date-partitioned Bronze Parquet directory."""
    if table not in config.source_tables:
        raise ValueError(f"Unsupported source table: {table}")

    source_file = config.raw_data_dir / f"{table}.csv"
    if not source_file.is_file():
        raise FileNotFoundError(f"Required source file not found: {source_file}")

    partition_date = ingest_date or date.today()
    batch_id = batch_id or str(uuid4())
    ingested_at = datetime.now(UTC).replace(tzinfo=None)

    output_dir = config.bronze_data_dir / table / f"ingest_date={partition_date.isoformat()}"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "data.parquet"
    connection = duckdb.connect()

    try:
        logger.info("Ingesting table=%s source=%s", table, source_file)

        connection.execute(
            """
            CREATE OR REPLACE TABLE bronze_data AS
            SELECT
                *,
                ? AS _ingested_at,
                ? AS _source_file,
                ? AS _batch_id
            FROM read_csv(
                ?,
                all_varchar = true,
                header = true,
                strict_mode = true
            )
            """,
            [
                ingested_at,
                source_file.name,
                batch_id,
                str(source_file),
            ],
        )

        connection.execute(
            "COPY bronze_data TO ? (FORMAT PARQUET)",
            [str(output_file)],
        )

        row_count = connection.execute("SELECT COUNT(*) FROM bronze_data").fetchone()[0]

        logger.info(
            "Ingested table=%s rows=%d output=%s",
            table,
            row_count,
            output_file,
        )
    finally:
        connection.close()

    return output_file


def ingest_all(
    config: Settings = settings,
    ingest_date: date | None = None,
) -> list[Path]:
    """Ingest all configured source tables."""
    outputs = []
    for table in config.source_tables:
        outputs.append(ingest_table(table, config, ingest_date))
    return outputs
