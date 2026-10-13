# ShopSignal

ShopSignal is a modular Python data pipeline project for ingesting, transforming, and enriching commerce data.

## Project structure

- `src/shopsignal/ingestion/` — source ingestion (Milestone 2)
- `src/shopsignal/transform/` — data transformation (Milestone 3)
- `src/shopsignal/enrichment/` — enrichment and AI capabilities (Milestone 5)
- `data/bronze/`, `data/silver/`, `data/gold/`, `data/raw/` — local data layers (ignored by Git)
- `tests/` — automated tests

## Development

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
make test
```
