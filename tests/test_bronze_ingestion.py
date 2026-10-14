"""Tests for Bronze CSV-to-Parquet ingestion."""

from datetime import date

import duckdb
import pytest

from shopsignal.config import Settings
from shopsignal.ingestion.ingestion import ingest_table


@pytest.fixture
def test_settings(tmp_path):
    """Create isolated raw and Bronze directories for testing."""
    raw_dir = tmp_path / "raw"
    bronze_dir = tmp_path / "bronze"
    raw_dir.mkdir()

    return Settings(
        project_root=tmp_path,
        raw_data_dir=raw_dir,
        bronze_data_dir=bronze_dir,
    )


def test_ingest_writes_parquet_and_preserves_source_values(test_settings):
    source = test_settings.raw_data_dir / "orders.csv"
    source.write_text(
        'order_id,customer_note\no1,"Café order"\no2,"First line\nsecond line"\n',
        encoding="utf-8",
    )

    output = ingest_table(
        "orders",
        config=test_settings,
        ingest_date=date(2026, 10, 14),
        batch_id="test-batch",
    )

    assert output.is_file()
    assert output.parent == (test_settings.bronze_data_dir / "orders" / "ingest_date=2026-10-14")

    connection = duckdb.connect()
    try:
        rows = connection.execute(
            "SELECT order_id, customer_note, _ingested_at, "
            "_source_file, _batch_id FROM read_parquet(?) ORDER BY order_id",
            [str(output)],
        ).fetchall()
    finally:
        connection.close()

    assert len(rows) == 2
    assert rows[0][0:2] == ("o1", "Café order")
    assert rows[1][0:2] == ("o2", "First line\nsecond line")

    for row in rows:
        assert row[2] is not None
        assert row[3] == "orders.csv"
        assert row[4] == "test-batch"


def test_rerun_replaces_output_without_duplicate_rows(test_settings):
    source = test_settings.raw_data_dir / "orders.csv"
    source.write_text("order_id\no1\no2\n", encoding="utf-8")

    first_output = ingest_table("orders", config=test_settings, ingest_date=date(2026, 10, 14))
    second_output = ingest_table("orders", config=test_settings, ingest_date=date(2026, 10, 14))

    assert first_output == second_output

    connection = duckdb.connect()
    try:
        row_count = connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(second_output)],
        ).fetchone()[0]
    finally:
        connection.close()

    assert row_count == 2


def test_missing_source_file_raises_clear_error(test_settings):
    with pytest.raises(FileNotFoundError, match="orders.csv"):
        ingest_table("orders", config=test_settings)


def test_unsupported_table_is_rejected(test_settings):
    with pytest.raises(ValueError, match="Unsupported source table"):
        ingest_table("unknown_table", config=test_settings)
