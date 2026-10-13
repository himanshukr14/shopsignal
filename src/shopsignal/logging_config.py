"""Logging configuration for ShopSignal."""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure consistent timestamped application logs."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
