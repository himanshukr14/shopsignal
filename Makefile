
.PHONY: setup install test lint format check

setup: install

install:
	uv sync --extra dev

test:
	uv run pytest -q

lint:
	uv run ruff check .

format:
	uv run ruff check --fix .
	uv run ruff format .

check: lint test
