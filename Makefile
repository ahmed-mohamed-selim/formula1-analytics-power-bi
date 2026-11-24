SOURCE ?= data/raw/archive.zip

.PHONY: install test lint format run

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src tests
	ruff format --check src tests

format:
	ruff format src tests

run:
	f1-analytics run --source $(SOURCE)
