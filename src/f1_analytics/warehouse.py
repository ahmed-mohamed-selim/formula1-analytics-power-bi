import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PRIMARY_KEYS: dict[str, list[str]] = {
    "dim_date": ["date_key"],
    "dim_race": ["race_id"],
    "dim_circuit": ["circuit_id"],
    "dim_driver": ["driver_id"],
    "dim_constructor": ["constructor_id"],
    "dim_status": ["status_id"],
    "fact_results": ["result_id"],
    "fact_sprint_results": ["result_id"],
    "fact_race_performance": ["race_id", "driver_id"],
    "fact_pit_stops": ["race_id", "driver_id", "stop"],
    "fact_lap_times": ["race_id", "driver_id", "lap"],
    "fact_practice_sessions": ["race_id", "driver_id", "session"],
    "fact_driver_standings": ["race_id", "driver_id"],
    "fact_constructor_standings": ["race_id", "constructor_id"],
}

_RACE_FACTS = (
    "fact_results",
    "fact_sprint_results",
    "fact_race_performance",
    "fact_pit_stops",
    "fact_lap_times",
    "fact_practice_sessions",
    "fact_driver_standings",
    "fact_constructor_standings",
)
_DRIVER_FACTS = (
    "fact_results",
    "fact_sprint_results",
    "fact_race_performance",
    "fact_pit_stops",
    "fact_lap_times",
    "fact_practice_sessions",
    "fact_driver_standings",
)
_CONSTRUCTOR_FACTS = (
    "fact_results",
    "fact_sprint_results",
    "fact_practice_sessions",
    "fact_constructor_standings",
)

RELATIONSHIPS: list[tuple[str, str, str, str]] = [
    ("dim_race", "date_key", "dim_date", "date_key"),
    ("dim_race", "circuit_id", "dim_circuit", "circuit_id"),
    *((t, "race_id", "dim_race", "race_id") for t in _RACE_FACTS),
    *((t, "driver_id", "dim_driver", "driver_id") for t in _DRIVER_FACTS),
    *((t, "constructor_id", "dim_constructor", "constructor_id") for t in _CONSTRUCTOR_FACTS),
    ("fact_results", "status_id", "dim_status", "status_id"),
    ("fact_sprint_results", "status_id", "dim_status", "status_id"),
]


def _date_key(dates: pd.Series) -> pd.Series:
    return (dates.dt.year * 10000 + dates.dt.month * 100 + dates.dt.day).astype("int32")


def build_dim_date(races: pd.DataFrame) -> pd.DataFrame:
    dates = pd.Series(pd.date_range(races["date"].min(), races["date"].max(), freq="D"))
    return pd.DataFrame(
        {
            "date_key": _date_key(dates),
            "date": dates,
            "year": dates.dt.year.astype("int16"),
            "quarter": dates.dt.quarter.astype("int8"),
            "month": dates.dt.month.astype("int8"),
            "month_name": dates.dt.month_name(),
            "day": dates.dt.day.astype("int8"),
            "day_of_week": (dates.dt.dayofweek + 1).astype("int8"),
            "day_name": dates.dt.day_name(),
            "is_weekend": dates.dt.dayofweek >= 5,
        }
    )


def build_dim_race(tables: dict[str, pd.DataFrame], facts: dict[str, pd.DataFrame]) -> pd.DataFrame:
    races = tables["races"]
    df = races.copy()
    df["date_key"] = _date_key(df["date"])
    df["race_label"] = df["year"].astype("string") + " " + df["race_name"]
    df["rounds_in_season"] = df.groupby("year")["round"].transform("max").astype("int8")
    race_laps = facts["fact_results"].groupby("race_id")["race_laps"].first()
    df["race_laps"] = df["race_id"].map(race_laps).astype("Int16")
    performance = facts["fact_race_performance"]
    df["has_qualifying_data"] = df["race_id"].isin(tables["qualifying"]["race_id"])
    df["has_lap_data"] = df["race_id"].isin(performance.loc[performance["has_lap_data"], "race_id"])
    df["has_pit_data"] = df["race_id"].isin(performance.loc[performance["has_pit_data"], "race_id"])
    return df[
        [
            "race_id",
            "race_label",
            "race_name",
            "year",
            "round",
            "rounds_in_season",
            "date_key",
            "date",
            "circuit_id",
            "era",
            "decade",
            "race_laps",
            "has_sprint",
            "has_qualifying_data",
            "has_lap_data",
            "has_pit_data",
        ]
    ]


def build_dimensions(
    tables: dict[str, pd.DataFrame], facts: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    return {
        "dim_date": build_dim_date(tables["races"]),
        "dim_race": build_dim_race(tables, facts),
        "dim_circuit": tables["circuits"][
            [
                "circuit_id",
                "circuit_ref",
                "circuit_name",
                "location",
                "country",
                "latitude",
                "longitude",
                "altitude_m",
            ]
        ],
        "dim_driver": tables["drivers"][
            [
                "driver_id",
                "driver_ref",
                "driver_name",
                "driver_code",
                "driver_number",
                "birth_date",
                "nationality",
            ]
        ],
        "dim_constructor": tables["constructors"][
            ["constructor_id", "constructor_ref", "constructor_name", "nationality"]
        ],
        "dim_status": tables["status"][["status_id", "status", "status_group", "is_finished"]],
    }


def build_warehouse(
    tables: dict[str, pd.DataFrame], facts: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    warehouse = {**build_dimensions(tables, facts), **facts}
    return {name: warehouse[name].reset_index(drop=True) for name in PRIMARY_KEYS}


def write_warehouse(warehouse: dict[str, pd.DataFrame], out_dir: Path, formats: list[str]) -> None:
    for fmt in formats:
        target = out_dir / fmt
        target.mkdir(parents=True, exist_ok=True)
        for name, df in warehouse.items():
            if fmt == "parquet":
                df.to_parquet(target / f"{name}.parquet", index=False)
            else:
                df.to_csv(target / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    logger.info("Wrote %d tables to %s (%s)", len(warehouse), out_dir, ", ".join(formats))


def read_warehouse(directory: Path) -> dict[str, pd.DataFrame]:
    missing = [n for n in PRIMARY_KEYS if not (directory / f"{n}.parquet").exists()]
    if missing:
        raise FileNotFoundError(f"Missing warehouse tables in {directory}: {', '.join(missing)}")
    return {name: pd.read_parquet(directory / f"{name}.parquet") for name in PRIMARY_KEYS}
