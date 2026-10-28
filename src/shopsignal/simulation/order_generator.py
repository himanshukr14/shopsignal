
"""Generate reproducible daily Olist-compatible order data."""

import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path
from uuid import UUID, uuid5

from shopsignal.config import PROJECT_ROOT

NAMESPACE = UUID("8b2c4f16-6f2d-4d42-9c0b-7e8f4c1a2d30")

ORDER_COLUMNS = [
    "order_id",
    "customer_id",
    "order_status",
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

ITEM_COLUMNS = [
    "order_id",
    "order_item_id",
    "product_id",
    "seller_id",
    "shipping_limit_date",
    "price",
    "freight_value",
]

REVIEW_COLUMNS = [
    "review_id",
    "order_id",
    "review_score",
    "review_comment_title",
    "review_comment_message",
    "review_creation_date",
    "review_answer_timestamp",
]

REVIEW_MESSAGES = [
    "Produto excelente, entrega rápida!",
    "Ótima qualidade, gostei muito.",
    "Muito bom, chegou tudo certo.",
    "O produto não correspondeu à descrição.",
    "Entrega atrasada, mas atendimento ótimo.",
    "Excelente custo-benefício.",
]

ORDER_STATUSES = ["delivered", "delivered", "shipped", "processing"]


def _load_ids(path: Path, column: str) -> list[str]:
    """Load non-empty identifiers from a source CSV."""
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames or column not in reader.fieldnames:
            raise ValueError(f"Column {column!r} not found in {path}")

        identifiers = [
            row[column]
            for row in reader
            if row.get(column)
        ]

    if not identifiers:
        raise ValueError(f"No identifiers found in {path} for column {column}")

    return identifiers


def generate_daily_data(
    simulation_date: date,
    seed: int,
    order_count: int = 20,
    output_dir: Path | None = None,
    customer_ids: list[str] | None = None,
    product_ids: list[str] | None = None,
    seller_ids: list[str] | None = None,
) -> dict[str, Path]:
    """Generate reproducible orders, items, and reviews for one simulated day."""
    if order_count < 1:
        raise ValueError("order_count must be at least 1")

    rng = random.Random(seed)
    raw_dir = PROJECT_ROOT / "data" / "raw"

    customers = (
        customer_ids
        if customer_ids is not None
        else _load_ids(raw_dir / "customers.csv", "customer_id")
    )
    products = (
        product_ids
        if product_ids is not None
        else _load_ids(raw_dir / "products.csv", "product_id")
    )
    sellers = (
        seller_ids
        if seller_ids is not None
        else _load_ids(raw_dir / "sellers.csv", "seller_id")
    )

    if not customers or not products or not sellers:
        raise ValueError("Customer, product, and seller ID lists must not be empty")

    destination = output_dir if output_dir is not None else raw_dir / "simulated"
    destination = destination / simulation_date.isoformat()
    destination.mkdir(parents=True, exist_ok=True)

    orders = []
    items = []
    reviews = []

    for index in range(order_count):
        order_id = str(
            uuid5(
                NAMESPACE,
                f"{simulation_date.isoformat()}:{seed}:order:{index}",
            )
        )
        customer_id = rng.choice(customers)
        status = rng.choice(ORDER_STATUSES)

        purchase = datetime.combine(
            simulation_date,
            time(hour=rng.randrange(24), minute=rng.randrange(60)),
        )

        # Processing orders are not approved yet.
        approved = (
            purchase + timedelta(minutes=rng.randint(1, 60))
            if status != "processing"
            else None
        )

        # Only shipped and delivered orders have reached the carrier.
        carrier = (
            approved + timedelta(days=rng.randint(1, 3))
            if approved is not None and status in ("shipped", "delivered")
            else None
        )

        # Only delivered orders have a customer delivery timestamp.
        delivered = (
            carrier + timedelta(days=rng.randint(1, 8))
            if carrier is not None and status == "delivered"
            else None
        )

        estimated_base = delivered or carrier or approved or purchase
        estimated = estimated_base + timedelta(days=rng.randint(2, 7))

        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_status": status,
                "order_purchase_timestamp": purchase.isoformat(sep=" "),
                "order_approved_at": (
                    approved.isoformat(sep=" ") if approved is not None else ""
                ),
                "order_delivered_carrier_date": (
                    carrier.isoformat(sep=" ") if carrier is not None else ""
                ),
                "order_delivered_customer_date": (
                    delivered.isoformat(sep=" ") if delivered is not None else ""
                ),
                "order_estimated_delivery_date": estimated.isoformat(sep=" "),
            }
        )

        # Generate two to four items per order.
        item_count = rng.randint(2, 4)

        for item_number in range(1, item_count + 1):
            shipping_base = approved if approved is not None else purchase

            items.append(
                {
                    "order_id": order_id,
                    "order_item_id": item_number,
                    "product_id": rng.choice(products),
                    "seller_id": rng.choice(sellers),
                    "shipping_limit_date": (
                        shipping_base + timedelta(days=rng.randint(1, 5))
                    ).isoformat(sep=" "),
                    "price": f"{rng.uniform(10, 500):.2f}",
                    "freight_value": f"{rng.uniform(5, 40):.2f}",
                }
            )

        if status == "delivered" and delivered is not None:
            review_date = delivered.date() + timedelta(days=1)

            reviews.append(
                {
                    "review_id": str(
                        uuid5(
                            NAMESPACE,
                            f"{simulation_date.isoformat()}:{seed}:review:{index}",
                        )
                    ),
                    "order_id": order_id,
                    "review_score": rng.randint(1, 5),
                    "review_comment_title": "",
                    "review_comment_message": rng.choice(REVIEW_MESSAGES),
                    "review_creation_date": f"{review_date.isoformat()} 00:00:00",
                    "review_answer_timestamp": (
                        f"{(review_date + timedelta(days=1)).isoformat()} 12:00:00"
                    ),
                }
            )

    datasets = {
        "orders": (ORDER_COLUMNS, orders),
        "order_items": (ITEM_COLUMNS, items),
        "order_reviews": (REVIEW_COLUMNS, reviews),
    }

    outputs: dict[str, Path] = {}

    for table, (columns, rows) in datasets.items():
        path = destination / f"{table}.csv"

        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

        outputs[table] = path

    return outputs
