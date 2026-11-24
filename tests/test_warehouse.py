import pandas as pd
import pytest

from f1_analytics.validation import validate_warehouse
from f1_analytics.warehouse import (
    PRIMARY_KEYS,
    RELATIONSHIPS,
    read_warehouse,
    write_warehouse,
)


def test_all_tables_are_built_with_unique_keys_and_valid_relationships(warehouse):
    assert set(warehouse) == set(PRIMARY_KEYS)
    validate_warehouse(warehouse, PRIMARY_KEYS, RELATIONSHIPS)


def test_dim_date_is_continuous_and_keys_match_calendar(warehouse):
    dates = warehouse["dim_date"]
    assert dates["date"].is_monotonic_increasing
    assert (dates["date"].diff().dropna() == pd.Timedelta(days=1)).all()
    assert dates["date_key"].iloc[0] == 20200301
    assert dates["date_key"].iloc[-1] == 20210307
    assert dates.set_index("date_key").loc[20200307, "day_name"] == "Saturday"


def test_dim_race_exposes_labels_and_data_coverage(warehouse):
    races = warehouse["dim_race"].set_index("race_id")
    assert races.loc[1, "race_label"] == "2020 Alpha GP"
    assert races.loc[2, "rounds_in_season"] == 2
    assert races.loc[1, "has_lap_data"]
    assert not races.loc[2, "has_lap_data"]
    assert races.loc[2, "has_sprint"]
    assert races.loc[1, "race_laps"] == 50


def test_dimensions_expose_expected_attributes(warehouse):
    assert "driver_name" in warehouse["dim_driver"]
    assert warehouse["dim_status"].set_index("status_id").loc[3, "status_group"] == (
        "Mechanical / technical"
    )
    assert warehouse["dim_constructor"]["constructor_name"].tolist() == ["Red", "Blue"]


def test_write_and_read_round_trip(warehouse, tmp_path):
    write_warehouse(warehouse, tmp_path, ["parquet", "csv"])
    assert len(list((tmp_path / "csv").glob("*.csv"))) == len(PRIMARY_KEYS)
    restored = read_warehouse(tmp_path / "parquet")
    for name, original in warehouse.items():
        pd.testing.assert_frame_equal(restored[name], original, check_dtype=False)


def test_read_warehouse_reports_missing_tables(tmp_path):
    with pytest.raises(FileNotFoundError, match="Missing warehouse tables"):
        read_warehouse(tmp_path)
