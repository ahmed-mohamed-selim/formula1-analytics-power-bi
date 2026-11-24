import logging
from pathlib import Path

import pandas as pd

from f1_analytics.cleaning import clean_all
from f1_analytics.config import Paths
from f1_analytics.features import build_features
from f1_analytics.ingestion import load_source
from f1_analytics.insights import generate_report
from f1_analytics.validation import validate_source, validate_warehouse
from f1_analytics.warehouse import (
    PRIMARY_KEYS,
    RELATIONSHIPS,
    build_warehouse,
    read_warehouse,
    write_warehouse,
)

logger = logging.getLogger(__name__)


def build(source: Path, paths: Paths, formats: list[str]) -> dict[str, pd.DataFrame]:
    tables = clean_all(load_source(source, paths.raw))
    validate_source(tables)
    warehouse = build_warehouse(tables, build_features(tables))
    validate_warehouse(warehouse, PRIMARY_KEYS, RELATIONSHIPS)
    write_warehouse(warehouse, paths.warehouse, formats)
    return warehouse


def report(warehouse: dict[str, pd.DataFrame] | None, paths: Paths) -> Path:
    if warehouse is None:
        warehouse = read_warehouse(paths.warehouse / "parquet")
    return generate_report(warehouse, paths.reports)
