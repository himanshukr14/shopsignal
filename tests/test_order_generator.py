
"""Tests for reproducible simulated order data."""

import csv
from datetime import date
from pathlib import Path

import pytest

from shopsignal.simulation.order_generator import (
    ITEM_COLUMNS,
    ORDER_COLUMNS,
    REVIEW_COLUMNS,
    generate_daily_data,
)

CUSTOMER_IDS = ["customer-1", "customer-2"]
PRODUCT_IDS = ["product-1", "product-2"]
SELLER_IDS = ["seller-1", "seller-2"]


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a generated CSV file."""
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def test_generator_preserves_schemas_and_relationships(
    tmp_path: Path,
) -> None:
    outputs = generate_daily_data(
        simulation_date=date(2026, 10, 27),
        seed=42,
        order_count=20,
        output_dir=tmp_path,
        customer_ids=CUSTOMER_IDS,
        product_ids=PRODUCT_IDS,
        seller_ids=SELLER_IDS,
    )

    orders = read_csv(outputs["orders"])
    items = read_csv(outputs["order_items"])
    reviews = read_csv(outputs["order_reviews"])

    assert list(orders[0]) == ORDER_COLUMNS
    assert list(items[0]) == ITEM_COLUMNS
    assert list(reviews[0]) == REVIEW_COLUMNS

    order_ids = {order["order_id"] for order in orders}
    assert len(order_ids) == 20
    assert all(item["order_id"] in order_ids for item in items)
    assert all(review["order_id"] in order_ids for review in reviews)

    assert all(
        order["order_purchase_timestamp"].startswith("2026-10-27")
        for order in orders
    )


def test_generator_is_reproducible(tmp_path: Path) -> None:
    simulation_date = date(2026, 10, 27)

    first = generate_daily_data(
        simulation_date,
        seed=123,
        order_count=10,
        output_dir=tmp_path / "first",
        customer_ids=CUSTOMER_IDS,
        product_ids=PRODUCT_IDS,
        seller_ids=SELLER_IDS,
    )
    second = generate_daily_data(
        simulation_date,
        seed=123,
        order_count=10,
        output_dir=tmp_path / "second",
        customer_ids=CUSTOMER_IDS,
        product_ids=PRODUCT_IDS,
        seller_ids=SELLER_IDS,
    )

    for table in first:
        assert first[table].read_bytes() == second[table].read_bytes()


def test_review_text_preserves_utf8_accents(tmp_path: Path) -> None:
    outputs = generate_daily_data(
        simulation_date=date(2026, 10, 27),
        seed=42,
        order_count=100,
        output_dir=tmp_path,
        customer_ids=CUSTOMER_IDS,
        product_ids=PRODUCT_IDS,
        seller_ids=SELLER_IDS,
    )

    reviews = read_csv(outputs["order_reviews"])
    assert reviews
    assert any(
        any(character in review["review_comment_message"] for character in "áéíóúãõç")
        for review in reviews
    )


def test_generator_rejects_non_positive_order_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="order_count must be at least 1"):
        generate_daily_data(
            simulation_date=date(2026, 10, 27),
            seed=42,
            order_count=0,
            output_dir=tmp_path,
            customer_ids=CUSTOMER_IDS,
            product_ids=PRODUCT_IDS,
            seller_ids=SELLER_IDS,
        )

def test_generator_rejects_empty_id_lists(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ID lists must not be empty"):
        generate_daily_data(
            simulation_date=date(2026, 10, 27),
            seed=42,
            order_count=1,
            output_dir=tmp_path,
            customer_ids=[],
            product_ids=PRODUCT_IDS,
            seller_ids=SELLER_IDS,
        )


def test_undelivered_orders_have_blank_delivery_timestamps(
    tmp_path: Path,
) -> None:
    outputs = generate_daily_data(
        simulation_date=date(2026, 10, 27),
        seed=42,
        order_count=100,
        output_dir=tmp_path,
        customer_ids=CUSTOMER_IDS,
        product_ids=PRODUCT_IDS,
        seller_ids=SELLER_IDS,
    )

    orders = read_csv(outputs["orders"])

    for order in orders:
        if order["order_status"] == "processing":
            assert order["order_approved_at"] == ""
            assert order["order_delivered_carrier_date"] == ""
            assert order["order_delivered_customer_date"] == ""

        elif order["order_status"] == "shipped":
            assert order["order_approved_at"] != ""
            assert order["order_delivered_carrier_date"] != ""
            assert order["order_delivered_customer_date"] == ""

        elif order["order_status"] == "delivered":
            assert order["order_approved_at"] != ""
            assert order["order_delivered_carrier_date"] != ""
            assert order["order_delivered_customer_date"] != ""
