import pandas as pd

from f1_analytics.cleaning import FINISHED_GROUPS

RESULT_COLUMNS = [
    "result_id",
    "race_id",
    "driver_id",
    "constructor_id",
    "status_id",
    "grid_position",
    "starts_from_pit_lane",
    "qualifying_position",
    "best_q_ms",
    "reached_q3",
    "finish_position",
    "position_order",
    "points",
    "laps",
    "race_laps",
    "laps_completed_pct",
    "race_time_ms",
    "fastest_lap_ms",
    "fastest_lap_rank",
    "fastest_lap_speed",
    "positions_gained",
    "age_at_race",
    "is_classified",
    "is_finished",
    "is_dnf",
    "is_disqualified",
    "is_dns",
    "is_win",
    "is_podium",
    "is_points_finish",
    "has_fastest_lap",
    "started_on_pole",
    "is_shared_drive",
]


def _flag(series: pd.Series) -> pd.Series:
    return series.astype("boolean").fillna(False).astype(bool)


def _positions_gained(df: pd.DataFrame) -> pd.Series:
    gained = df["grid_position"].astype("float64") - df["position_order"]
    return gained.where(df["is_classified"] & df["grid_position"].notna()).astype("Int16")


def build_fact_results(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    qualifying = tables["qualifying"][
        ["race_id", "driver_id", "qualifying_position", "best_q_ms", "reached_q3"]
    ]
    df = (
        tables["results"]
        .merge(tables["status"][["status_id", "status_group"]], on="status_id", how="left")
        .merge(qualifying, on=["race_id", "driver_id"], how="left", validate="m:1")
        .merge(tables["races"][["race_id", "date"]], on="race_id", how="left")
        .merge(tables["drivers"][["driver_id", "birth_date"]], on="driver_id", how="left")
    )
    group = df["status_group"]
    df["is_finished"] = group.isin(FINISHED_GROUPS)
    df["is_disqualified"] = group.eq("Disqualified")
    df["is_dns"] = group.eq("Did not start")
    df["is_dnf"] = ~(df["is_finished"] | df["is_disqualified"] | df["is_dns"])
    df["is_win"] = _flag(df["finish_position"].eq(1))
    df["is_podium"] = _flag(df["finish_position"].le(3))
    df["is_points_finish"] = df["points"] > 0
    df["has_fastest_lap"] = _flag(df["fastest_lap_rank"].eq(1))
    df["started_on_pole"] = _flag(df["grid_position"].eq(1))
    df["reached_q3"] = _flag(df["reached_q3"])
    df["positions_gained"] = _positions_gained(df)
    df["race_laps"] = df.groupby("race_id")["laps"].transform("max").astype("int16")
    df["laps_completed_pct"] = (df["laps"] / df["race_laps"]).round(4).astype("float32")
    df["age_at_race"] = (
        ((df["date"] - df["birth_date"]).dt.days / 365.25).round(1).astype("float32")
    )
    return df[RESULT_COLUMNS]


def build_fact_sprint_results(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = tables["sprint_results"].merge(
        tables["status"][["status_id", "status_group"]], on="status_id", how="left"
    )
    df["is_finished"] = df["status_group"].isin(FINISHED_GROUPS)
    df["is_win"] = _flag(df["finish_position"].eq(1))
    df["is_podium"] = _flag(df["finish_position"].le(3))
    df["positions_gained"] = _positions_gained(df)
    return df[
        [
            "result_id",
            "race_id",
            "driver_id",
            "constructor_id",
            "status_id",
            "grid_position",
            "finish_position",
            "position_order",
            "points",
            "laps",
            "fastest_lap_ms",
            "positions_gained",
            "is_classified",
            "is_finished",
            "is_win",
            "is_podium",
        ]
    ]


def build_fact_race_performance(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    keys = ["race_id", "driver_id"]
    laps = tables["lap_times"]
    clean_laps = laps[~laps["is_outlier_lap"]].groupby(keys, observed=True)["lap_time_ms"]
    lap_stats = clean_laps.agg(
        best_lap_ms="min",
        avg_lap_ms="mean",
        median_lap_ms="median",
        lap_std_ms="std",
        clean_laps="count",
    ).round(0)
    lap_counts = laps.groupby(keys, observed=True).agg(
        laps_recorded=("lap", "count"), outlier_laps=("is_outlier_lap", "sum")
    )
    first_lap = laps[laps["lap"] == 1].set_index(keys)["race_position"].rename("first_lap_position")
    lap_part = lap_counts.join(lap_stats).join(first_lap).reset_index()

    stops = tables["pit_stops"]
    valid = stops[~stops["is_outlier_stop"]].groupby(keys, observed=True)
    pit_stats = valid.agg(
        pit_stops=("stop", "count"),
        total_pit_s=("duration_s", "sum"),
        avg_pit_s=("duration_s", "mean"),
        first_stop_lap=("lap", "min"),
    )
    outlier_stops = (
        stops.groupby(keys, observed=True)["is_outlier_stop"].sum().rename("outlier_stops")
    )
    pit_part = outlier_stops.to_frame().join(pit_stats).reset_index()
    pit_part["pit_stops"] = pit_part["pit_stops"].fillna(0)

    df = lap_part.merge(pit_part, on=keys, how="outer")
    df["has_lap_data"] = df["laps_recorded"].notna()
    df["has_pit_data"] = df["outlier_stops"].notna()
    for column in ("laps_recorded", "outlier_laps"):
        df[column] = df[column].fillna(0).astype("int16")
    for column in ("outlier_stops", "pit_stops"):
        df[column] = df[column].where(df["has_pit_data"]).astype("Int16")
    df["total_pit_s"] = df["total_pit_s"].round(3)
    df["avg_pit_s"] = df["avg_pit_s"].round(3)
    return df


def build_fact_standings(standings: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
    final_races = races.loc[races.groupby("year")["round"].idxmax(), "race_id"]
    df = standings.copy()
    df["is_season_final"] = df["race_id"].isin(final_races)
    return df


def build_features(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    races = tables["races"]
    return {
        "fact_results": build_fact_results(tables),
        "fact_sprint_results": build_fact_sprint_results(tables),
        "fact_race_performance": build_fact_race_performance(tables),
        "fact_pit_stops": tables["pit_stops"],
        "fact_lap_times": tables["lap_times"],
        "fact_practice_sessions": tables["practice_sessions"],
        "fact_driver_standings": build_fact_standings(tables["driver_standings"], races),
        "fact_constructor_standings": build_fact_standings(tables["constructor_standings"], races),
    }
