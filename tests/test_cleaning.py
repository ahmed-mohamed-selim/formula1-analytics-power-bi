import pandas as pd
import pytest

from f1_analytics.cleaning import status_group, time_to_ms
from f1_analytics.ingestion import SourceDataError, locate_csv_files, read_table, to_snake


@pytest.mark.parametrize(
    ("text", "expected"),
    [("56.481", 56481), ("1:56.481", 116481), ("2:13:23.600", 8003600), ("0:59.999", 59999)],
)
def test_time_to_ms_parses_supported_formats(text, expected):
    assert time_to_ms(pd.Series([text])).iloc[0] == expected


@pytest.mark.parametrize("text", ["+2.600", "", None, "abc"])
def test_time_to_ms_returns_missing_for_unparseable_values(text):
    assert pd.isna(time_to_ms(pd.Series([text])).iloc[0])


@pytest.mark.parametrize(
    ("status", "group"),
    [
        ("Finished", "Finished"),
        ("+3 Laps", "Finished (lapped)"),
        ("Lapped", "Finished (lapped)"),
        ("Disqualified", "Disqualified"),
        ("Did not start", "Did not start"),
        ("Collision", "Accident / collision"),
        ("Illness", "Driver / safety"),
        ("Retired", "Other retirement"),
        ("Gearbox", "Mechanical / technical"),
    ],
)
def test_status_group(status, group):
    assert status_group(status) == group


def test_to_snake():
    assert to_snake("fastestLapSpeed") == "fastest_lap_speed"
    assert to_snake("raceId") == "race_id"
    assert to_snake("fp1_date") == "fp1_date"


def test_driver_cleaning_fills_codes_and_missing_attributes(clean_tables):
    drivers = clean_tables["drivers"].set_index("driver_id")
    assert drivers.loc[1, "driver_code"] == "ALP"
    assert drivers.loc[2, "driver_code"] == "BBB"
    assert drivers.loc[3, "nationality"] == "Unknown"
    assert pd.isna(drivers.loc[3, "birth_date"])
    assert drivers.loc[1, "driver_name"] == "Ann Alpha"


def test_country_aliases_are_standardised(clean_tables):
    assert clean_tables["circuits"]["country"].iloc[0] == "United Kingdom"


def test_pit_stop_and_lap_outliers_are_flagged_not_removed(clean_tables):
    stops = clean_tables["pit_stops"]
    laps = clean_tables["lap_times"]
    assert stops["is_outlier_stop"].tolist() == [False, True, True]
    assert laps["is_outlier_lap"].sum() == 1
    assert len(laps) == 6


def test_results_flags_pit_lane_starts_and_shared_drives(clean_tables):
    results = clean_tables["results"].set_index("result_id")
    assert results.loc[3, "starts_from_pit_lane"]
    assert pd.isna(results.loc[3, "grid_position"])
    assert results.loc[8, "is_shared_drive"]
    assert not results.loc[1, "is_shared_drive"]


def test_qualifying_best_time_uses_latest_available_stage(clean_tables):
    qualifying = clean_tables["qualifying"].set_index("driver_id")
    assert qualifying.loc[1, "best_q_ms"] == 90100
    assert qualifying.loc[2, "best_q_ms"] == 92000
    assert qualifying.loc[1, "reached_q3"]
    assert not qualifying.loc[2, "reached_q3"]


def test_locate_csv_files_reports_missing_tables(tmp_path):
    (tmp_path / "circuits.csv").write_text("circuitId\n1\n")
    with pytest.raises(SourceDataError, match="Missing source files"):
        locate_csv_files(tmp_path, tmp_path / "work")


def test_read_table_rejects_unexpected_columns(tmp_path):
    path = tmp_path / "seasons.csv"
    path.write_text("year,link\n2020,x\n")
    with pytest.raises(SourceDataError, match="Unexpected columns"):
        read_table("seasons", path)
