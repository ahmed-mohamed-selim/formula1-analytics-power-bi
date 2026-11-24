import logging

import pandas as pd

from f1_analytics.schema import PRIMARY_KEYS, REFERENCES

logger = logging.getLogger(__name__)

Reference = tuple[str, str, str, str]


class DataQualityError(RuntimeError):
    pass


def duplicate_keys(tables: dict[str, pd.DataFrame], keys: dict[str, list[str]]) -> pd.DataFrame:
    rows = [
        {
            "table": name,
            "key": ", ".join(cols),
            "duplicates": int(tables[name].duplicated(cols).sum()),
        }
        for name, cols in keys.items()
    ]
    return pd.DataFrame(rows)


def orphan_rows(tables: dict[str, pd.DataFrame], references: list[Reference]) -> pd.DataFrame:
    rows = [
        {
            "child": child,
            "column": column,
            "parent": parent,
            "orphans": int((~tables[child][column].isin(tables[parent][parent_column])).sum()),
        }
        for child, column, parent, parent_column in references
    ]
    return pd.DataFrame(rows)


def _raise_on_failures(keys: pd.DataFrame, references: pd.DataFrame) -> None:
    failures = []
    failures += [
        f"{r.table}: {r.duplicates} duplicate rows for key ({r.key})"
        for r in keys.itertuples()
        if r.duplicates
    ]
    failures += [
        f"{r.child}.{r.column}: {r.orphans} rows without a matching {r.parent} record"
        for r in references.itertuples()
        if r.orphans
    ]
    if failures:
        raise DataQualityError("Data quality checks failed:\n- " + "\n- ".join(failures))


def validate_source(tables: dict[str, pd.DataFrame]) -> None:
    _raise_on_failures(duplicate_keys(tables, PRIMARY_KEYS), orphan_rows(tables, REFERENCES))
    winners = tables["results"].query("position_order == 1").groupby("race_id").size()
    missing = set(tables["races"]["race_id"]) - set(winners.index)
    if missing:
        raise DataQualityError(f"{len(missing)} races have no winner recorded")
    logger.info("Source validation passed")


def validate_warehouse(
    tables: dict[str, pd.DataFrame],
    keys: dict[str, list[str]],
    references: list[Reference],
) -> None:
    _raise_on_failures(duplicate_keys(tables, keys), orphan_rows(tables, references))
    logger.info("Warehouse validation passed")
