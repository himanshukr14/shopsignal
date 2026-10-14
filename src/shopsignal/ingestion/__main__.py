"""Command-line entry point for Bronze ingestion."""

import logging

from shopsignal.ingestion.ingestion import ingest_all
from shopsignal.logging_config import configure_logging


def main() -> None:
    configure_logging()
    try:
        ingest_all()
    except Exception:
        logging.getLogger(__name__).exception("Bronze ingestion failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
