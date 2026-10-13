# ShopSignal

ShopSignal is a data engineering project that transforms e-commerce data into validated, analytics-ready datasets and supports dashboarding and LLM-powered question answering.

The project uses a layered data architecture, local analytical storage, automated quality checks, and reproducible development workflows.

## Architecture

```text
Raw sources
  └── Olist CSVs and simulated daily orders
       ↓
Bronze — raw Parquet and ingestion metadata
       ↓
Silver — cleaned, typed, validated data
       ├── LLM enrichment — sentiment, topic, severity
       ↓
Gold — analytics-ready star schema using dbt
       ↓
Consumers — dashboards and LLM Q&A
```

Key components:

- **DuckDB:** Local analytical SQL engine.
- **Parquet:** Columnar analytical storage.
- **dbt:** Gold-layer transformations and star schema.
- **Dagster:** Pipeline orchestration.
- **Ollama:** Local LLM inference behind a replaceable provider interface.
- **GitHub Actions:** Automated CI checks.

See [Architecture](docs/architecture.md) and [ADR 0001](docs/adr/0001-use-duckdb-and-parquet.md).

## Prerequisites

- Git
- A Python version supported by `pyproject.toml`
- uv

Install uv using the [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

## Getting started

Clone the repository:

```bash
git clone https://github.com/himanshukr14/shopsignal.git
cd shopsignal
```

Install the project and development dependencies:

```bash
make setup
```

Run linting and tests:

```bash
make lint
make test
```

Run all checks in sequence:

```bash
make setup && make lint && make test
```

## Project structure

```text
src/shopsignal/
├── config.py
├── ingestion/
├── transform/
└── enrichment/

tests/
data/
├── raw/
├── bronze/
├── silver/
└── gold/

docs/
├── architecture.md
└── adr/
    └── 0001-use-duckdb-and-parquet.md
```

## Development workflow

1. Create a feature branch.
2. Make a focused change and add tests where appropriate.
3. Run linting and tests locally.
4. Open a pull request against `main`.
5. Ensure required CI checks pass before merging.

## Roadmap

- [x] Create the initial project scaffold.
- [x] Add GitHub Actions lint and test checks.
- [x] Protect `main` with pull-request and CI requirements.
- [ ] Document the architecture and storage decision.
- [ ] Implement configuration validation.
- [ ] Build Olist source ingestion.
- [ ] Add simulated daily-order ingestion.
- [ ] Implement Bronze and Silver processing.
- [ ] Add data-quality validations.
- [ ] Implement provider-swappable LLM enrichment.
- [ ] Build Gold star-schema models with dbt.
- [ ] Orchestrate the pipeline with Dagster.
- [ ] Add analytical consumers and LLM Q&A.
- [ ] Add end-to-end tests and operational documentation.

## License

MIT. See [LICENSE](LICENSE).