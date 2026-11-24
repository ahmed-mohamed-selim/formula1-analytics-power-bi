import logging
import re
from collections.abc import Callable

import pandas as pd

from f1_analytics.config import (
    COUNTRY_ALIASES,
    ERA_BINS,
    ERA_LABELS,
    OUTLIER_LAP_RATIO,
    OUTLIER_PIT_STOP_MS,
)

logger = logging.getLogger(__name__)

TIME_PATTERN = r"^(?:(?:(\d+):)?(\d+):)?(\d+(?:\.\d+)?)$"

FINISHED_GROUPS = ("Finished", "Finished (lapped)")
DISQUALIFIED = {"Disqualified", "Excluded", "Underweight"}
NOT_STARTED = {"Did not start", "Withdrew", "Not classified", "Not restarted"}
COLLISION = {
    "Accident",
    "Collision",
    "Spun off",
    "Collision damage",
    "Fatal accident",
    "Damage",
    "Debris",
}
DRIVER_RELATED = {
    "Driver Seat",
    "Injury",
    "Injured",
    "Eye injury",
    "Physical",
    "Driver unwell",
    "Illness",
    "Safety",
    "Safety concerns",
    "Safety belt",
}
OTHER_RETIREMENT = {
    "Retired",
    "Handling",
    "Stalled",
    "Tyre",
    "Puncture",
    "Tyre puncture",
    "Out of fuel",
    "Fuel",
}


def time_to_ms(series: pd.Series) -> pd.Series:
    parts = series.astype("string").str.strip().str.extract(TIME_PATTERN)
    hours, minutes, seconds = (pd.to_numeric(parts[i]) for i in range(3))
    millis = ((hours.fillna(0) * 60 + minutes.fillna(0)) * 60 + seconds) * 1000
    return millis.round().astype("Int32")


def status_group(status: str) -> str:
    if status == "Finished":
        return "Finished"
    if re.fullmatch(r"\+\d+ Laps?|Lapped", status):
        return "Finished (lapped)"
    if status in DISQUALIFIED:
        return "Disqualified"
    if status in NOT_STARTED:
        return "Did not start"
    if status in COLLISION:
        return "Accident / collision"
    if status in DRIVER_RELATED:
        return "Driver / safety"
    if status in OTHER_RETIREMENT:
        return "Other retirement"
    return "Mechanical / technical"


def _strip_text(df: pd.DataFrame) -> pd.DataFrame:
    for column in df.columns:
        dtype = df[column].dtype
        if pd.api.types.is_string_dtype(dtype) and not isinstance(dtype, pd.CategoricalDtype):
            df[column] = df[column].str.strip().replace("", pd.NA)
    return df


def _warn_on_mismatch(label: str, parsed: pd.Series, reference: pd.Series) -> None:
    mismatches = int(((parsed.astype("float64") - reference).abs() > 1).sum())
    if mismatches:
        logger.warning(
            "%s: %d rows differ between text and numeric time columns", label, mismatches
        )


def clean_circuits(df: pd.DataFrame) -> pd.DataFrame:
    df["country"] = df["country"].astype("string").replace(COUNTRY_ALIASES)
    return df.rename(
        columns={"name": "circuit_name", "lat": "latitude", "lng": "longitude", "alt": "altitude_m"}
    ).drop(columns="url")


def clean_constructors(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"name": "constructor_name"}).drop(columns="url")


def clean_drivers(df: pd.DataFrame) -> pd.DataFrame:
    df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
    df["driver_name"] = (df["forename"].fillna("") + " " + df["surname"].fillna("")).str.strip()
    df["code"] = df["code"].fillna(df["surname"].str[:3].str.upper())
    df["nationality"] = df["nationality"].astype("string").fillna("Unknown")
    return df.rename(
        columns={"dob": "birth_date", "code": "driver_code", "number": "driver_number"}
    ).drop(columns=["forename", "surname", "url"])


def clean_status(df: pd.DataFrame) -> pd.DataFrame:
    df["status_group"] = df["status"].map(status_group)
    df["is_finished"] = df["status_group"].isin(FINISHED_GROUPS)
    return df


def clean_seasons(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns="url")


def clean_races(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["decade"] = (df["year"] // 10 * 10).astype("int16")
    df["era"] = pd.cut(df["year"], list(ERA_BINS), labels=list(ERA_LABELS)).astype("string")
    df["has_sprint"] = df["sprint_date"].notna()
    df = df.rename(columns={"name": "race_name"})
    return df[
        [
            "race_id",
            "year",
            "round",
            "circuit_id",
            "race_name",
            "date",
            "decade",
            "era",
            "has_sprint",
        ]
    ]


def _clean_classification(df: pd.DataFrame) -> pd.DataFrame:
    df["starts_from_pit_lane"] = df["grid"].eq(0)
    df["grid_position"] = df["grid"].where(df["grid"] > 0).astype("Int8")
    df["is_classified"] = df["position"].notna()
    df["fastest_lap_ms"] = time_to_ms(df["fastest_lap_time"])
    df = df.rename(columns={"position": "finish_position", "milliseconds": "race_time_ms"})
    return df.drop(
        columns=["grid", "number", "position_text", "time", "fastest_lap_time", "fastest_lap"]
    )


def clean_results(df: pd.DataFrame) -> pd.DataFrame:
    df["is_shared_drive"] = df.duplicated(["race_id", "driver_id"], keep=False)
    return _clean_classification(df).rename(columns={"rank": "fastest_lap_rank"})


def clean_sprint_results(df: pd.DataFrame) -> pd.DataFrame:
    return _clean_classification(df)


def clean_qualifying(df: pd.DataFrame) -> pd.DataFrame:
    stages = ["q1", "q2", "q3"]
    for stage in stages:
        df[f"{stage}_ms"] = time_to_ms(df[stage])
    stage_ms = [f"{stage}_ms" for stage in stages]
    df["best_q_ms"] = df[stage_ms].astype("float64").min(axis=1).astype("Int32")
    df["reached_q3"] = df["q3_ms"].notna()
    df = df.rename(columns={"position": "qualifying_position"})
    return df.drop(columns=["qualify_id", "number", *stages])


def clean_pit_stops(df: pd.DataFrame) -> pd.DataFrame:
    _warn_on_mismatch("pit_stops", time_to_ms(df["duration"]), df["milliseconds"])
    df["duration_s"] = (df["milliseconds"] / 1000).round(3)
    df["is_outlier_stop"] = df["milliseconds"] > OUTLIER_PIT_STOP_MS
    return df.drop(columns=["time", "duration", "milliseconds"])


def clean_lap_times(df: pd.DataFrame) -> pd.DataFrame:
    _warn_on_mismatch("lap_times", time_to_ms(df["time"]), df["milliseconds"])
    race_median = df.groupby("race_id")["milliseconds"].transform("median")
    df["is_outlier_lap"] = df["milliseconds"] > OUTLIER_LAP_RATIO * race_median
    df = df.rename(columns={"milliseconds": "lap_time_ms", "position": "race_position"})
    return df.drop(columns="time")


def clean_practice_sessions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={"milliseconds": "lap_time_ms", "position": "session_position"})
    return df.drop(columns="time")


def clean_driver_standings(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=["driver_standings_id", "position_text"])


def clean_constructor_standings(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=["constructor_standings_id", "position_text"])


def clean_constructor_results(df: pd.DataFrame) -> pd.DataFrame:
    df["is_disqualified"] = df["status"].eq("D")
    return df.drop(columns=["constructor_results_id", "status"])


CLEANERS: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "circuits": clean_circuits,
    "constructors": clean_constructors,
    "drivers": clean_drivers,
    "seasons": clean_seasons,
    "status": clean_status,
    "races": clean_races,
    "results": clean_results,
    "sprint_results": clean_sprint_results,
    "qualifying": clean_qualifying,
    "lap_times": clean_lap_times,
    "pit_stops": clean_pit_stops,
    "practice_sessions": clean_practice_sessions,
    "driver_standings": clean_driver_standings,
    "constructor_standings": clean_constructor_standings,
    "constructor_results": clean_constructor_results,
}


def clean_all(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    cleaned = {name: CLEANERS[name](_strip_text(raw[name].copy())) for name in CLEANERS}
    logger.info("Cleaned %d tables", len(cleaned))
    return cleaned
