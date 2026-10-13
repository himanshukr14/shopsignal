"""Tests for ShopSignal configuration."""

from pathlib import Path

from shopsignal.config import PROJECT_ROOT, settings


def test_project_root_resolves_to_repository_root() -> None:
    assert PROJECT_ROOT == Path(__file__).resolve().parents[1]


def test_data_directories_resolve_from_project_root() -> None:
    assert settings.raw_data_dir == PROJECT_ROOT / "data" / "raw"
    assert settings.bronze_data_dir == PROJECT_ROOT / "data" / "bronze"


def test_expected_source_tables_are_configured() -> None:
    assert len(settings.source_tables) == 9
    assert "orders" in settings.source_tables
    assert "order_reviews" in settings.source_tables
    assert "product_category_name_translation" in settings.source_tables
