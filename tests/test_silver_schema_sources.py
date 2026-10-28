
"""Validate Silver schema contracts against raw CSV headers."""

import duckdb
import pytest

from shopsignal.config import settings
from shopsignal.transform.schemas import SILVER_SCHEMAS


@pytest.mark.parametrize("table", settings.source_tables)
def test_schema_columns_match_raw_csv_headers(table: str) -> None:
    """Every raw CSV must contain exactly the columns in its contract."""
    csv_path = settings.raw_data_dir / f"{table}.csv"

    if not csv_path.is_file():
        pytest.skip(f"Raw dataset not available: {csv_path.name}")

    with duckdb.connect() as connection:
        actual_columns = [
            row[0]
            for row in connection.execute(
                """
                DESCRIBE
                SELECT *
                FROM read_csv_auto(?, header = true, sample_size = 1000)
                """,
                [str(csv_path)],
            ).fetchall()
        ]

    expected_columns = list(SILVER_SCHEMAS[table].column_names)

    assert actual_columns == expected_columns, (
        f"{table}: expected columns {expected_columns}, "
        f"found {actual_columns}"
    )

@pytest.mark.parametrize("table", settings.source_tables)
def test_non_nullable_columns_have_no_missing_values(table: str) -> None:
    """Non-nullable Silver columns must not contain missing source values."""
    csv_path = settings.raw_data_dir / f"{table}.csv"

    if not csv_path.is_file():
        pytest.skip(f"Raw dataset not available: {csv_path.name}")

    schema = SILVER_SCHEMAS[table]
    required_columns = [column.name for column in schema.columns if not column.nullable]

    with duckdb.connect() as connection:
        for column_name in required_columns:
            quoted_column = '"' + column_name.replace('"', '""') + '"'
            query = f"""
                SELECT COUNT(*)
                FROM read_csv_auto(?, header = true)
                WHERE NULLIF(TRIM(CAST({quoted_column} AS VARCHAR)), '') IS NULL
            """
            missing_count = connection.execute(query, [str(csv_path)]).fetchone()[0]

            assert missing_count == 0, (
                f"{table}.{column_name} is non-nullable but contains "
                f"{missing_count} missing or blank values"
            )


@pytest.mark.parametrize("table", settings.source_tables)
def test_source_values_are_compatible_with_silver_types(table: str) -> None:
    """Nonblank source values must convert to their declared Silver types."""
    csv_path = settings.raw_data_dir / f"{table}.csv"

    if not csv_path.is_file():
        pytest.skip(f"Raw dataset not available: {csv_path.name}")

    schema = SILVER_SCHEMAS[table]

    with duckdb.connect() as connection:
        for column in schema.columns:
            quoted_column = '"' + column.name.replace('"', '""') + '"'
            expression = (
                f"TRY_CAST(NULLIF(TRIM(CAST({quoted_column} AS VARCHAR)), '') "
                f"AS {column.data_type})"
            )
            query = f"""
                SELECT COUNT(*)
                FROM read_csv(
                    ?,
                    header = true,
                    all_varchar = true
                )
                WHERE NULLIF(TRIM(CAST({quoted_column} AS VARCHAR)), '') IS NOT NULL
                  AND {expression} IS NULL
            """
            invalid_count = connection.execute(query, [str(csv_path)]).fetchone()[0]

            assert invalid_count == 0, (
                f"{table}.{column.name}: {invalid_count} nonblank values "
                f"cannot be converted to {column.data_type}"
            )

@pytest.mark.parametrize("table", settings.source_tables)
def test_declared_primary_keys_are_unique_and_non_null(table: str) -> None:
    """Declared Silver keys must contain no nulls or duplicate combinations."""
    csv_path = settings.raw_data_dir / f"{table}.csv"

    if not csv_path.is_file():
        pytest.skip(f"Raw dataset not available: {csv_path.name}")

    primary_key = SILVER_SCHEMAS[table].primary_key

    # Some sources have no verified primary key.
    if not primary_key:
        return

    quoted_keys = [
        '"' + column_name.replace('"', '""') + '"' for column_name in primary_key
    ]
    key_expression = ", ".join(quoted_keys)
    null_condition = " OR ".join(f"{column} IS NULL" for column in quoted_keys)

    with duckdb.connect() as connection:
        null_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM read_csv(?, header = true, all_varchar = true)
            WHERE {null_condition}
            """,
            [str(csv_path)],
        ).fetchone()[0]

        duplicate_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT {key_expression}
                FROM read_csv(?, header = true, all_varchar = true)
                GROUP BY {key_expression}
                HAVING COUNT(*) > 1
            ) AS duplicate_keys
            """,
            [str(csv_path)],
        ).fetchone()[0]

    assert null_count == 0, f"{table}: primary key has {null_count} null rows"
    assert duplicate_count == 0, (
        f"{table}: primary key has {duplicate_count} duplicate key combinations"
    )
