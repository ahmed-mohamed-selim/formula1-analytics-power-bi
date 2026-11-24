import pandas as pd
import pytest

from f1_analytics.schema import PRIMARY_KEYS, REFERENCES
from f1_analytics.validation import (
    DataQualityError,
    duplicate_keys,
    orphan_rows,
    validate_source,
)


def test_clean_fixture_passes_validation(clean_tables):
    validate_source(clean_tables)
    assert duplicate_keys(clean_tables, PRIMARY_KEYS)["duplicates"].sum() == 0
    assert orphan_rows(clean_tables, REFERENCES)["orphans"].sum() == 0


def test_orphan_rows_are_reported(clean_tables):
    clean_tables["results"].loc[0, "driver_id"] = 99
    report = orphan_rows(clean_tables, REFERENCES)
    flagged = report[report["orphans"] > 0]
    assert flagged[["child", "column"]].to_dict("records") == [
        {"child": "results", "column": "driver_id"}
    ]
    with pytest.raises(DataQualityError, match="results.driver_id"):
        validate_source(clean_tables)


def test_duplicate_primary_keys_fail_validation(clean_tables):
    races = clean_tables["races"]
    clean_tables["races"] = pd.concat([races, races.iloc[[0]]], ignore_index=True)
    with pytest.raises(DataQualityError, match="races"):
        validate_source(clean_tables)


def test_race_without_winner_fails_validation(clean_tables):
    results = clean_tables["results"]
    clean_tables["results"] = results[
        ~((results["race_id"] == 2) & (results["position_order"] == 1))
    ]
    with pytest.raises(DataQualityError, match="no winner"):
        validate_source(clean_tables)
