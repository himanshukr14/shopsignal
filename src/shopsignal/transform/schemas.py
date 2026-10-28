
"""Silver schema contracts for the raw Olist datasets."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnContract:
    """Expected type and nullability for a Silver column."""

    name: str
    data_type: str
    nullable: bool = False


@dataclass(frozen=True)
class TableContract:
    """Expected Silver columns and candidate key for a table."""

    name: str
    columns: tuple[ColumnContract, ...]
    primary_key: tuple[str, ...]

    @property
    def column_names(self) -> tuple[str, ...]:
        """Return the expected column names in contract order."""
        return tuple(column.name for column in self.columns)


def col(name: str, data_type: str, nullable: bool = False) -> ColumnContract:
    """Create a column contract."""
    return ColumnContract(name=name, data_type=data_type, nullable=nullable)


SILVER_SCHEMAS: dict[str, TableContract] = {
    "orders": TableContract(
        name="orders",
        columns=(
            col("order_id", "VARCHAR"),
            col("customer_id", "VARCHAR"),
            col("order_status", "VARCHAR"),
            col("order_purchase_timestamp", "TIMESTAMP"),
            col("order_approved_at", "TIMESTAMP", nullable=True),
            col("order_delivered_carrier_date", "TIMESTAMP", nullable=True),
            col("order_delivered_customer_date", "TIMESTAMP", nullable=True),
            col("order_estimated_delivery_date", "TIMESTAMP"),
        ),
        primary_key=("order_id",),
    ),
    "order_items": TableContract(
        name="order_items",
        columns=(
            col("order_id", "VARCHAR"),
            col("order_item_id", "INTEGER"),
            col("product_id", "VARCHAR"),
            col("seller_id", "VARCHAR"),
            col("shipping_limit_date", "TIMESTAMP"),
            col("price", "DECIMAL(12, 2)"),
            col("freight_value", "DECIMAL(12, 2)"),
        ),
        primary_key=("order_id", "order_item_id"),
    ),
    "order_payments": TableContract(
        name="order_payments",
        columns=(
            col("order_id", "VARCHAR"),
            col("payment_sequential", "INTEGER"),
            col("payment_type", "VARCHAR"),
            col("payment_installments", "INTEGER"),
            col("payment_value", "DECIMAL(12, 2)"),
        ),
        primary_key=("order_id", "payment_sequential"),
    ),
    "order_reviews": TableContract(
        name="order_reviews",
        columns=(
            col("review_id", "VARCHAR"),
            col("order_id", "VARCHAR"),
            col("review_score", "INTEGER"),
            col("review_comment_title", "VARCHAR", nullable=True),
            col("review_comment_message", "VARCHAR", nullable=True),
            col("review_creation_date", "TIMESTAMP"),
            col("review_answer_timestamp", "TIMESTAMP"),
        ),
        # review_id repeats across different orders in the raw dataset.
        # Preserve source rows; a unique row key is not yet established.
        primary_key=(),
    ),
    "customers": TableContract(
        name="customers",
        columns=(
            col("customer_id", "VARCHAR"),
            col("customer_unique_id", "VARCHAR"),
            col("customer_zip_code_prefix", "VARCHAR"),
            col("customer_city", "VARCHAR"),
            col("customer_state", "VARCHAR"),
        ),
        primary_key=("customer_id",),
    ),
    "sellers": TableContract(
        name="sellers",
        columns=(
            col("seller_id", "VARCHAR"),
            col("seller_zip_code_prefix", "VARCHAR"),
            col("seller_city", "VARCHAR"),
            col("seller_state", "VARCHAR"),
        ),
        primary_key=("seller_id",),
    ),
    "products": TableContract(
        name="products",
        columns=(
            col("product_id", "VARCHAR"),
            col("product_category_name", "VARCHAR", nullable=True),
            col("product_name_lenght", "INTEGER", nullable=True),
            col("product_description_lenght", "INTEGER", nullable=True),
            col("product_photos_qty", "INTEGER", nullable=True),
            col("product_weight_g", "INTEGER", nullable=True),
            col("product_length_cm", "INTEGER", nullable=True),
            col("product_height_cm", "INTEGER", nullable=True),
            col("product_width_cm", "INTEGER", nullable=True),
        ),
        primary_key=("product_id",),
    ),
    "geolocation": TableContract(
        name="geolocation",
        columns=(
            col("geolocation_zip_code_prefix", "VARCHAR"),
            col("geolocation_lat", "DOUBLE"),
            col("geolocation_lng", "DOUBLE"),
            col("geolocation_city", "VARCHAR"),
            col("geolocation_state", "VARCHAR"),
        ),
        # The ZIP prefix is not unique. A stable row key has not yet
        # been established for this source dataset.
        primary_key=(),
    ),
    "product_category_name_translation": TableContract(
        name="product_category_name_translation",
        columns=(
            col("product_category_name", "VARCHAR"),
            col("product_category_name_english", "VARCHAR"),
        ),
        primary_key=("product_category_name",),
    ),
}
