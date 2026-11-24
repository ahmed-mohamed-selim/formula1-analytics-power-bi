import logging
import re
import zipfile
from pathlib import Path

import pandas as pd

from f1_analytics.schema import SCHEMAS

logger = logging.getLogger(__name__)

NA_TOKENS = ["", " ", "\\N", "?", "N/A", "NULL", "null", "nan", "NaN"]


class SourceDataError(RuntimeError):
    pass


def to_snake(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()


def locate_csv_files(source: Path, workdir: Path) -> dict[str, Path]:
    source = Path(source)
    if not source.exists():
        raise SourceDataError(f"Source not found: {source}")
    if source.is_file():
        if source.suffix.lower() != ".zip":
            raise SourceDataError(f"Unsupported source type: {source.name}")
        workdir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(source) as archive:
            archive.extractall(workdir)
        root = workdir
    else:
        root = source
    found = {
        p.stem: p
        for p in root.rglob("*.csv")
        if "__MACOSX" not in p.parts and not p.name.startswith("._")
    }
    missing = sorted(set(SCHEMAS) - set(found))
    if missing:
        raise SourceDataError(f"Missing source files: {', '.join(missing)}")
    return {name: found[name] for name in SCHEMAS}


def read_table(name: str, path: Path) -> pd.DataFrame:
    columns = [to_snake(c) for c in pd.read_csv(path, nrows=0).columns]
    schema = SCHEMAS[name]
    if set(columns) != set(schema):
        diff = sorted(set(columns) ^ set(schema))
        raise SourceDataError(f"Unexpected columns in {name}.csv: {', '.join(diff)}")
    return pd.read_csv(
        path, header=0, names=columns, dtype=schema, na_values=NA_TOKENS, keep_default_na=False
    )


def load_source(source: Path, workdir: Path) -> dict[str, pd.DataFrame]:
    files = locate_csv_files(source, workdir)
    tables = {name: read_table(name, path) for name, path in files.items()}
    logger.info("Loaded %d tables (%d rows)", len(tables), sum(len(t) for t in tables.values()))
    return tables
