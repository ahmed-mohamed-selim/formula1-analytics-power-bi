import pandas as pd
import pytest


@pytest.fixture
def fact_results(facts):
    return facts["fact_results"].set_index("result_id")


def test_fact_results_preserves_grain(facts, clean_tables):
    assert len(facts["fact_results"]) == len(clean_tables["results"])
    assert facts["fact_results"]["result_id"].is_unique


def test_win_podium_and_pole_flags(fact_results):
    assert fact_results.loc[1, ["is_win", "is_podium", "started_on_pole"]].all()
    assert fact_results.loc[3, "is_podium"]
    assert not fact_results.loc[3, "is_win"]
    assert not fact_results.loc[4, "is_podium"]


def test_status_flags_are_mutually_consistent(fact_results):
    assert fact_results.loc[3, "is_finished"]
    assert fact_results.loc[4, "is_dnf"]
    assert fact_results.loc[7, "is_dns"]
    assert not fact_results.loc[7, "is_dnf"]
    outcomes = fact_results[["is_finished", "is_dnf", "is_disqualified", "is_dns"]].sum(axis=1)
    assert (outcomes == 1).all()


def test_positions_gained_is_positive_when_places_are_won(fact_results):
    assert fact_results.loc[2, "positions_gained"] == 1
    assert fact_results.loc[6, "positions_gained"] == 0
    assert pd.isna(fact_results.loc[3, "positions_gained"])
    assert pd.isna(fact_results.loc[4, "positions_gained"])


def test_laps_completed_pct_is_relative_to_race_distance(fact_results):
    assert fact_results.loc[1, "laps_completed_pct"] == 1.0
    assert fact_results.loc[3, "laps_completed_pct"] == pytest.approx(0.98)
    assert fact_results.loc[4, "laps_completed_pct"] == pytest.approx(0.4)


def test_qualifying_is_attached_without_duplicating_rows(fact_results):
    assert fact_results.loc[1, "qualifying_position"] == 1
    assert fact_results.loc[1, "reached_q3"]
    assert pd.isna(fact_results.loc[5, "qualifying_position"])
    assert not fact_results.loc[5, "reached_q3"]


def test_age_at_race(fact_results):
    assert fact_results.loc[1, "age_at_race"] == pytest.approx(30.0)
    assert pd.isna(fact_results.loc[7, "age_at_race"])


def test_race_performance_excludes_outliers_from_averages(facts):
    performance = facts["fact_race_performance"].set_index(["race_id", "driver_id"])
    driver = performance.loc[(1, 1)]
    assert driver["laps_recorded"] == 3
    assert driver["outlier_laps"] == 1
    assert driver["best_lap_ms"] == 90000
    assert driver["avg_lap_ms"] == 90500
    assert driver["pit_stops"] == 1
    assert driver["outlier_stops"] == 1
    assert driver["avg_pit_s"] == pytest.approx(24.5)
    assert driver["first_lap_position"] == 1
    assert not performance.loc[(1, 2), "has_pit_data"]
    assert pd.isna(performance.loc[(1, 2), "pit_stops"])


def test_season_final_flag_marks_last_round_only(facts):
    standings = facts["fact_driver_standings"]
    assert standings.groupby("is_season_final")["race_id"].unique().map(sorted).to_dict() == {
        False: [1],
        True: [2, 3],
    }


def test_sprint_positions_gained(facts):
    sprint = facts["fact_sprint_results"].set_index("result_id")
    assert sprint.loc[101, "positions_gained"] == 1
    assert sprint.loc[102, "positions_gained"] == -1


def test_driver_with_only_outlier_stops_has_zero_valid_stops(facts):
    performance = facts["fact_race_performance"].set_index(["race_id", "driver_id"])
    row = performance.loc[(1, 3)]
    assert row["has_pit_data"]
    assert row["pit_stops"] == 0
    assert row["outlier_stops"] == 1
