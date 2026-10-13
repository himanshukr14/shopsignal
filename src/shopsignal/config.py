"""Project settings and paths for ShopSignal."""

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Centralized filesystem paths and source-table configuration."""

    project_root: Path = PROJECT_ROOT
    raw_data_dir: Path = PROJECT_ROOT / "data" / "raw"
    bronze_data_dir: Path = PROJECT_ROOT / "data" / "bronze"
    source_tables: tuple[str, ...] = (
        "orders",
        "order_items",
        "order_payments",
        "order_reviews",
        "customers",
        "sellers",
        "products",
        "geolocation",
        "product_category_name_translation",
    )


settings = Settings()
