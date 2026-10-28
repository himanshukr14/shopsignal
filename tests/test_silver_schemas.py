
"""Tests for Silver schema contracts."""

from shopsignal.config import settings
from shopsignal.transform.schemas import SILVER_SCHEMAS


def test_silver_schemas_cover_all_source_tables() -> None:
    """Every configured source table must have a Silver contract."""
    assert set(SILVER_SCHEMAS) == set(settings.source_tables)


def test_schema_names_match_registry_keys() -> None:
    """Each schema name must match its registry key."""
    for name, schema in SILVER_SCHEMAS.items():
        assert schema.name == name


def test_column_names_are_unique() -> None:
    """A table contract must not define a column more than once."""
    for schema in SILVER_SCHEMAS.values():
        assert len(schema.column_names) == len(set(schema.column_names))


def test_primary_keys_reference_declared_columns() -> None:
    """Every declared primary-key column must exist in its schema."""
    for schema in SILVER_SCHEMAS.values():
        assert set(schema.primary_key).issubset(set(schema.column_names))


def test_all_columns_have_explicit_types_and_nullability() -> None:
    """Every column must declare a name, type, and boolean nullability."""
    for schema in SILVER_SCHEMAS.values():
        for column in schema.columns:
            assert column.name
            assert column.data_type
            assert isinstance(column.nullable, bool)


def test_expected_composite_keys() -> None:
    """Order items and payments must use composite keys."""
    assert SILVER_SCHEMAS["order_items"].primary_key == (
        "order_id",
        "order_item_id",
    )
    assert SILVER_SCHEMAS["order_payments"].primary_key == (
        "order_id",
        "payment_sequential",
    )


def test_geolocation_has_no_unverified_primary_key() -> None:
    """Do not assume ZIP prefixes uniquely identify geolocation rows."""
    assert SILVER_SCHEMAS["geolocation"].primary_key == ()


def test_order_reviews_has_no_unverified_primary_key() -> None:
    """Repeated review IDs must not be declared unique without evidence."""
    assert SILVER_SCHEMAS["order_reviews"].primary_key == ()
