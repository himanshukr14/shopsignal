
"""Tests for Bronze CSV-to-Parquet ingestion."""

import csv
from datetime import date
from pathlib import Path

import duckdb
import pytest

from shopsignal.config import Settings
from shopsignal.ingestion.ingestion import ingest_all, ingest_table
from shopsignal.simulation.order_generator import generate_daily_data


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
        source="olist",
    )

    assert output.is_file()
    assert output.parent == (
        test_settings.bronze_data_dir
        / "orders"
        / "source=olist"
        / "ingest_date=2026-10-14"
    )

    with duckdb.connect() as connection:
        rows = connection.execute(
            """
            SELECT
                order_id,
                customer_note,
                _ingested_at,
                _source_file,
                _batch_id,
                _source
            FROM read_parquet(?)
            ORDER BY order_id
            """,
            [str(output)],
        ).fetchall()

    assert len(rows) == 2
    assert rows[0][0:2] == ("o1", "Café order")
    assert rows[1][0:2] == ("o2", "First line\nsecond line")

    for row in rows:
        assert row[2] is not None
        assert row[3] == "orders.csv"
        assert row[4] == "test-batch"
        assert row[5] == "olist"


def test_rerun_replaces_output_without_duplicate_rows(test_settings):
    source = test_settings.raw_data_dir / "orders.csv"
    source.write_text("order_id\no1\no2\n", encoding="utf-8")

    first_output = ingest_table(
        "orders",
        config=test_settings,
        ingest_date=date(2026, 10, 14),
        source="olist",
    )
    second_output = ingest_table(
        "orders",
        config=test_settings,
        ingest_date=date(2026, 10, 14),
        source="olist",
    )

    assert first_output == second_output

    with duckdb.connect() as connection:
        row_count = connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(second_output)],
        ).fetchone()[0]

    assert row_count == 2


def test_missing_source_file_raises_clear_error(test_settings):
    with pytest.raises(FileNotFoundError, match="orders.csv"):
        ingest_table("orders", config=test_settings)


def test_unsupported_table_is_rejected(test_settings):
    with pytest.raises(ValueError, match="Unsupported source table"):
        ingest_table("unknown_table", config=test_settings)


def test_unsupported_source_is_rejected(test_settings):
    source = test_settings.raw_data_dir / "orders.csv"
    source.write_text("order_id\no1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported source"):
        ingest_table(
            "orders",
            config=test_settings,
            source="unknown",
        )


def test_simulated_csvs_ingest_to_bronze_with_metadata(
    test_settings,
    tmp_path,
):
    """Generated daily CSVs ingest into source-specific Bronze partitions."""
    simulation_date = date(2026, 10, 27)

    outputs = generate_daily_data(
        simulation_date=simulation_date,
        seed=42,
        order_count=10,
        output_dir=tmp_path / "simulated",
        customer_ids=["customer-1", "customer-2"],
        product_ids=["product-1", "product-2"],
        seller_ids=["seller-1", "seller-2"],
    )

    for table, source_path in outputs.items():
        with source_path.open(newline="", encoding="utf-8") as file:
            expected_count = sum(1 for _ in csv.DictReader(file))

        output = ingest_table(
            table,
            config=test_settings,
            ingest_date=simulation_date,
            batch_id=f"simulated-{table}",
            source_dir=source_path.parent,
            source="simulated",
        )

        assert output.is_file()
        assert output.parent == (
            test_settings.bronze_data_dir
            / table
            / "source=simulated"
            / f"ingest_date={simulation_date.isoformat()}"
        )

        with duckdb.connect() as connection:
            row_count = connection.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(output)],
            ).fetchone()[0]

            metadata = connection.execute(
                """
                SELECT DISTINCT
                    _source_file,
                    _batch_id,
                    _ingested_at,
                    _source
                FROM read_parquet(?)
                """,
                [str(output)],
            ).fetchall()

        assert row_count == expected_count
        assert len(metadata) == 1
        assert metadata[0][0] == source_path.name
        assert metadata[0][1] == f"simulated-{table}"
        assert metadata[0][2] is not None
        assert metadata[0][3] == "simulated"


def test_simulated_ingestion_rerun_preserves_row_counts(
    test_settings,
    tmp_path,
):
    """Rerunning simulated ingestion replaces its own partition only."""
    simulation_date = date(2026, 10, 27)

    outputs = generate_daily_data(
        simulation_date=simulation_date,
        seed=99,
        order_count=10,
        output_dir=tmp_path / "simulated",
        customer_ids=["customer-1", "customer-2"],
        product_ids=["product-1", "product-2"],
        seller_ids=["seller-1", "seller-2"],
    )

    for table, source_path in outputs.items():
        first_output = ingest_table(
            table,
            config=test_settings,
            ingest_date=simulation_date,
            batch_id=f"simulated-{table}",
            source_dir=source_path.parent,
            source="simulated",
        )
        second_output = ingest_table(
            table,
            config=test_settings,
            ingest_date=simulation_date,
            batch_id=f"simulated-{table}",
            source_dir=source_path.parent,
            source="simulated",
        )

        assert first_output == second_output

        with duckdb.connect() as connection:
            row_count = connection.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(second_output)],
            ).fetchone()[0]

        with source_path.open(newline="", encoding="utf-8") as file:
            expected_count = sum(1 for _ in csv.DictReader(file))

        assert row_count == expected_count


def test_olist_and_simulated_sources_have_separate_partitions(
    test_settings,
    tmp_path,
):
    """Ingesting simulated orders must not replace Olist orders."""
    simulation_date = date(2026, 10, 27)

    # A small Olist fixture makes this test deterministic and CI-friendly.
    olist_csv = test_settings.raw_data_dir / "orders.csv"
    olist_csv.write_text(
        "order_id\nolist-1\nolist-2\nolist-3\n",
        encoding="utf-8",
    )

    simulated = generate_daily_data(
        simulation_date=simulation_date,
        seed=42,
        order_count=10,
        output_dir=tmp_path / "simulated",
        customer_ids=["customer-1"],
        product_ids=["product-1"],
        seller_ids=["seller-1"],
    )

    olist_path = ingest_table(
        "orders",
        config=test_settings,
        ingest_date=simulation_date,
        batch_id="olist-test",
        source="olist",
    )

    simulated_path = ingest_table(
        "orders",
        config=test_settings,
        ingest_date=simulation_date,
        batch_id="simulated-test",
        source_dir=simulated["orders"].parent,
        source="simulated",
    )

    assert olist_path != simulated_path
    assert "source=olist" in str(olist_path)
    assert "source=simulated" in str(simulated_path)

    with duckdb.connect() as connection:
        olist_count = connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(olist_path)],
        ).fetchone()[0]

        simulated_count = connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(simulated_path)],
        ).fetchone()[0]

    assert olist_count == 3
    assert simulated_count == 10

    # Re-ingest simulated orders and confirm Olist is still untouched.
    repeated_simulated_path = ingest_table(
        "orders",
        config=test_settings,
        ingest_date=simulation_date,
        batch_id="simulated-test",
        source_dir=simulated["orders"].parent,
        source="simulated",
    )

    assert repeated_simulated_path == simulated_path

    with duckdb.connect() as connection:
        olist_count_after_rerun = connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(olist_path)],
        ).fetchone()[0]

        simulated_count_after_rerun = connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(simulated_path)],
        ).fetchone()[0]

    assert olist_count_after_rerun == 3
    assert simulated_count_after_rerun == 10


def test_ingest_all_supports_selected_simulated_tables(
    tmp_path: Path,
    test_settings: Settings,
) -> None:
    simulation_date = date(2026, 10, 27)

    generated = generate_daily_data(
        simulation_date=simulation_date,
        seed=42,
        order_count=10,
        output_dir=tmp_path / "simulated",
        customer_ids=["customer-1", "customer-2"],
        product_ids=["product-1", "product-2"],
        seller_ids=["seller-1", "seller-2"],
    )

    source_dir = next(iter(generated.values())).parent
    tables = list(generated)

    output_paths = ingest_all(
        config=test_settings,
        ingest_date=simulation_date,
        source_dir=source_dir,
        tables=tables,
        source="simulated",
    )

    assert len(output_paths) == len(tables)

    for table, output_path in zip(tables, output_paths, strict=True):
        with generated[table].open(newline="", encoding="utf-8") as file:
            expected_count = sum(1 for _ in csv.DictReader(file))

        assert output_path.parent == (
            test_settings.bronze_data_dir
            / table
            / "source=simulated"
            / f"ingest_date={simulation_date.isoformat()}"
        )

        with duckdb.connect() as connection:
            actual_count = connection.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(output_path)],
            ).fetchone()[0]

        assert actual_count == expected_count
