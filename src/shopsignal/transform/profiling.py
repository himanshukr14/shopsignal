
"""Profile raw Olist CSV datasets with DuckDB."""

import json
from pathlib import Path

import duckdb

from shopsignal.config import settings

# Candidate business keys to investigate.
# Profiling reports duplicate counts; it does not assume duplicates
# should automatically be removed.
CANDIDATE_KEYS = {
    "orders": [("order_id",)],
    "order_items": [("order_id", "order_item_id")],
    "order_payments": [("order_id", "payment_sequential")],
    "order_reviews": [("review_id",)],
    "customers": [("customer_id",), ("customer_unique_id",)],
    "sellers": [("seller_id",)],
    "products": [("product_id",)],
    "geolocation": [],
    "product_category_name_translation": [("product_category_name",)],
}


DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "order_reviews": [
        "review_creation_date",
        "review_answer_timestamp",
    ],
}


NUMERIC_COLUMNS = {
    "order_items": ["price", "freight_value"],
    "order_payments": [
        "payment_sequential",
        "payment_installments",
        "payment_value",
    ],
    "order_reviews": ["review_score"],
    "products": [
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
    "geolocation": ["geolocation_lat", "geolocation_lng"],
}


def quote_identifier(identifier: str) -> str:
    """Safely quote a DuckDB identifier."""
    return '"' + identifier.replace('"', '""') + '"'


def profile_table(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    csv_path: Path,
) -> dict:
    """Return row, null, duplicate-key, date, and numeric profiles."""

    # Create a temporary view over the source CSV.
    # Escape single quotes in the path before embedding it in SQL.
    csv_path_sql = "'" + str(csv_path).replace("'", "''") + "'"

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW source_data AS
        SELECT *
        FROM read_csv_auto(
            {csv_path_sql},
            header = true,
            sample_size = -1
        )
        """
    )

    columns = [
        row[0]
        for row in connection.execute(
            "DESCRIBE source_data"
        ).fetchall()
    ]

    row_count = connection.execute(
        "SELECT COUNT(*) FROM source_data"
    ).fetchone()[0]

    # Profile null and blank values for every column.
    null_counts = {}

    for column in columns:
        quoted = quote_identifier(column)

        null_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM source_data
            WHERE {quoted} IS NULL
               OR TRIM(CAST({quoted} AS VARCHAR)) = ''
            """
        ).fetchone()[0]

        null_counts[column] = {
            "null_or_blank_count": null_count,
            "null_or_blank_rate_pct": round(
                null_count * 100 / row_count, 4
            )
            if row_count
            else 0,
        }

    # Profile candidate keys, including composite keys.
    duplicate_keys = {}

    for key_columns in CANDIDATE_KEYS.get(table, []):
        key_name = " + ".join(key_columns)

        missing_columns = [
            column
            for column in key_columns
            if column not in columns
        ]

        if missing_columns:
            duplicate_keys[key_name] = {
                "status": "column_missing",
                "missing_columns": missing_columns,
            }
            continue

        quoted_columns = [
            quote_identifier(column)
            for column in key_columns
        ]

        key_expression = ", ".join(quoted_columns)

        # A key is incomplete if any component is null or blank.
        null_condition = " OR ".join(
            f"""
            {quoted} IS NULL
            OR TRIM(CAST({quoted} AS VARCHAR)) = ''
            """
            for quoted in quoted_columns
        )

        null_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM source_data
            WHERE {null_condition}
            """
        ).fetchone()[0]

        # Count duplicate groups and the excess rows within those groups.
        # Incomplete keys are excluded from this calculation.
        duplicate_result = connection.execute(
            f"""
            SELECT
                COALESCE(SUM(group_count - 1), 0),
                COUNT(*)
            FROM (
                SELECT COUNT(*) AS group_count
                FROM source_data
                WHERE NOT ({null_condition})
                GROUP BY {key_expression}
                HAVING COUNT(*) > 1
            ) AS duplicate_groups
            """
        ).fetchone()

        duplicate_keys[key_name] = {
            "duplicate_excess_rows": duplicate_result[0],
            "duplicate_groups": duplicate_result[1],
            "null_or_blank_keys": null_count,
        }

    # Profile date ranges and values that cannot be parsed as timestamps.
    date_ranges = {}

    for column in DATE_COLUMNS.get(table, []):
        if column not in columns:
            continue

        quoted = quote_identifier(column)

        result = connection.execute(
            f"""
            SELECT
                MIN(
                    TRY_CAST(
                        NULLIF(TRIM(CAST({quoted} AS VARCHAR)), '')
                        AS TIMESTAMP
                    )
                ),
                MAX(
                    TRY_CAST(
                        NULLIF(TRIM(CAST({quoted} AS VARCHAR)), '')
                        AS TIMESTAMP
                    )
                ),
                COUNT(*) FILTER (
                    WHERE NULLIF(
                        TRIM(CAST({quoted} AS VARCHAR)), ''
                    ) IS NOT NULL
                    AND TRY_CAST(
                        NULLIF(
                            TRIM(CAST({quoted} AS VARCHAR)), ''
                        ) AS TIMESTAMP
                    ) IS NULL
                )
            FROM source_data
            """
        ).fetchone()

        date_ranges[column] = {
            "min": str(result[0]) if result[0] is not None else None,
            "max": str(result[1]) if result[1] is not None else None,
            "unparseable_nonblank_values": result[2],
        }

    # Profile numeric ranges and unparseable nonblank values.
    numeric_ranges = {}

    for column in NUMERIC_COLUMNS.get(table, []):
        if column not in columns:
            continue

        quoted = quote_identifier(column)

        result = connection.execute(
            f"""
            SELECT
                MIN(
                    TRY_CAST(
                        NULLIF(TRIM(CAST({quoted} AS VARCHAR)), '')
                        AS DOUBLE
                    )
                ),
                MAX(
                    TRY_CAST(
                        NULLIF(TRIM(CAST({quoted} AS VARCHAR)), '')
                        AS DOUBLE
                    )
                ),
                COUNT(*) FILTER (
                    WHERE NULLIF(
                        TRIM(CAST({quoted} AS VARCHAR)), ''
                    ) IS NOT NULL
                    AND TRY_CAST(
                        NULLIF(
                            TRIM(CAST({quoted} AS VARCHAR)), ''
                        ) AS DOUBLE
                    ) IS NULL
                )
            FROM source_data
            """
        ).fetchone()

        numeric_ranges[column] = {
            "min": result[0],
            "max": result[1],
            "unparseable_nonblank_values": result[2],
        }

    return {
        "table": table,
        "file": csv_path.name,
        "row_count": row_count,
        "columns": columns,
        "column_count": len(columns),
        "nulls": null_counts,
        "candidate_key_profiles": duplicate_keys,
        "date_ranges": date_ranges,
        "numeric_ranges": numeric_ranges,
    }


def profile_all(raw_dir: Path | None = None) -> dict:
    """Profile all configured source tables and return a JSON report."""

    input_dir = raw_dir if raw_dir is not None else settings.raw_data_dir
    report = {}

    with duckdb.connect() as connection:
        for table in settings.source_tables:
            csv_path = input_dir / f"{table}.csv"

            if not csv_path.is_file():
                raise FileNotFoundError(
                    f"Required source file not found: {csv_path}"
                )

            report[table] = profile_table(
                connection,
                table,
                csv_path,
            )

    return report


def main() -> None:
    """Print a JSON profile of all configured raw tables."""
    print(
        json.dumps(
            profile_all(),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
