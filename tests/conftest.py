import pandas as pd
import pytest

from f1_analytics.cleaning import clean_all
from f1_analytics.features import build_features
from f1_analytics.schema import SCHEMAS
from f1_analytics.warehouse import build_warehouse

INTEGER_TYPES = {"int8", "int16", "int32"}


def make_table(name: str, rows: list[dict]) -> pd.DataFrame:
    schema = SCHEMAS[name]
    df = pd.DataFrame(rows, columns=list(schema))
    for column, dtype in schema.items():
        if dtype in INTEGER_TYPES:
            df[column] = df[column].fillna(0)
        df[column] = df[column].astype(dtype)
    return df


def result(rid, race, driver, team, grid, pos, order, points, laps, status, **extra):
    return {
        "result_id": rid,
        "race_id": race,
        "driver_id": driver,
        "constructor_id": team,
        "grid": grid,
        "position": pos,
        "position_order": order,
        "points": points,
        "laps": laps,
        "status_id": status,
        **extra,
    }


@pytest.fixture
def raw_tables() -> dict[str, pd.DataFrame]:
    races = [
        {
            "race_id": 1,
            "year": 2020,
            "round": 1,
            "circuit_id": 1,
            "name": "Alpha GP",
            "date": "2020-03-01",
        },
        {
            "race_id": 2,
            "year": 2020,
            "round": 2,
            "circuit_id": 1,
            "name": "Beta GP",
            "date": "2020-03-08",
            "sprint_date": "2020-03-07",
        },
        {
            "race_id": 3,
            "year": 2021,
            "round": 1,
            "circuit_id": 1,
            "name": "Gamma GP",
            "date": "2021-03-07",
        },
    ]
    results = [
        result(1, 1, 1, 1, 1, 1, 1, 25, 50, 1, fastest_lap_time="1:30.000", rank=1),
        result(2, 1, 2, 2, 3, 2, 2, 18, 50, 1),
        result(3, 1, 4, 2, 0, 3, 3, 15, 49, 2),
        result(4, 1, 3, 1, 2, None, 4, 0, 20, 3),
        result(5, 2, 2, 2, 1, 1, 1, 25, 40, 1),
        result(6, 2, 1, 1, 2, 2, 2, 18, 40, 1),
        result(7, 2, 3, 1, 3, None, 3, 0, 0, 5),
        result(8, 3, 1, 1, 1, 1, 1, 25, 30, 1),
        result(9, 3, 1, 2, 5, None, 2, 0, 10, 3),
    ]
    sprints = [
        {
            "result_id": 101,
            "race_id": 2,
            "driver_id": 2,
            "constructor_id": 2,
            "grid": 2,
            "position": 1,
            "position_order": 1,
            "points": 3,
            "laps": 17,
            "status_id": 1,
        },
        {
            "result_id": 102,
            "race_id": 2,
            "driver_id": 1,
            "constructor_id": 1,
            "grid": 1,
            "position": 2,
            "position_order": 2,
            "points": 2,
            "laps": 17,
            "status_id": 1,
        },
    ]
    tables = {
        "circuits": [
            {
                "circuit_id": 1,
                "circuit_ref": "alpha",
                "name": "Alpha Ring",
                "location": "Alpha",
                "country": "UK",
            }
        ],
        "constructors": [
            {
                "constructor_id": 1,
                "constructor_ref": "red",
                "name": "Red",
                "nationality": "British",
            },
            {
                "constructor_id": 2,
                "constructor_ref": "blue",
                "name": "Blue",
                "nationality": "Italian",
            },
        ],
        "drivers": [
            {
                "driver_id": 1,
                "driver_ref": "alpha",
                "forename": "Ann",
                "surname": "Alpha",
                "dob": "1990-03-01",
                "nationality": "British",
            },
            {
                "driver_id": 2,
                "driver_ref": "beta",
                "code": "BBB",
                "forename": "Bob",
                "surname": "Beta",
                "dob": "1991-01-01",
                "nationality": "Italian",
            },
            {"driver_id": 3, "driver_ref": "gamma", "forename": "Cy", "surname": "Gamma"},
            {
                "driver_id": 4,
                "driver_ref": "delta",
                "forename": "Di",
                "surname": "Delta",
                "dob": "1992-01-01",
                "nationality": "French",
            },
        ],
        "seasons": [{"year": 2020}, {"year": 2021}],
        "status": [
            {"status_id": 1, "status": "Finished"},
            {"status_id": 2, "status": "+1 Lap"},
            {"status_id": 3, "status": "Engine"},
            {"status_id": 4, "status": "Disqualified"},
            {"status_id": 5, "status": "Did not start"},
        ],
        "races": races,
        "results": results,
        "sprint_results": sprints,
        "qualifying": [
            {
                "qualify_id": 1,
                "race_id": 1,
                "driver_id": 1,
                "constructor_id": 1,
                "position": 1,
                "q1": "1:31.000",
                "q2": "1:30.500",
                "q3": "1:30.100",
            },
            {
                "qualify_id": 2,
                "race_id": 1,
                "driver_id": 2,
                "constructor_id": 2,
                "position": 3,
                "q1": "1:32.000",
            },
        ],
        "lap_times": [
            {
                "race_id": 1,
                "driver_id": 1,
                "lap": 1,
                "position": 1,
                "time": "1:30.000",
                "milliseconds": 90000,
            },
            {
                "race_id": 1,
                "driver_id": 1,
                "lap": 2,
                "position": 1,
                "time": "1:31.000",
                "milliseconds": 91000,
            },
            {
                "race_id": 1,
                "driver_id": 1,
                "lap": 3,
                "position": 1,
                "time": "3:20.000",
                "milliseconds": 200000,
            },
            {
                "race_id": 1,
                "driver_id": 2,
                "lap": 1,
                "position": 2,
                "time": "1:32.000",
                "milliseconds": 92000,
            },
            {
                "race_id": 1,
                "driver_id": 2,
                "lap": 2,
                "position": 2,
                "time": "1:33.000",
                "milliseconds": 93000,
            },
            {
                "race_id": 1,
                "driver_id": 2,
                "lap": 3,
                "position": 2,
                "time": "1:32.500",
                "milliseconds": 92500,
            },
        ],
        "pit_stops": [
            {
                "race_id": 1,
                "driver_id": 1,
                "stop": 1,
                "lap": 20,
                "time": "14:10:00",
                "duration": "24.500",
                "milliseconds": 24500,
            },
            {
                "race_id": 1,
                "driver_id": 1,
                "stop": 2,
                "lap": 40,
                "time": "14:50:00",
                "duration": "5:00.000",
                "milliseconds": 300000,
            },
            {
                "race_id": 1,
                "driver_id": 3,
                "stop": 1,
                "lap": 10,
                "time": "14:05:00",
                "duration": "5:00.000",
                "milliseconds": 300000,
            },
        ],
        "practice_sessions": [
            {
                "race_id": 2,
                "driver_id": 1,
                "constructor_id": 1,
                "session": "FP1",
                "position": 1,
                "time": "1:20.000",
                "milliseconds": 80000,
                "laps": 20,
            },
        ],
        "driver_standings": [
            {
                "driver_standings_id": 1,
                "race_id": 1,
                "driver_id": 1,
                "points": 25,
                "position": 1,
                "wins": 1,
            },
            {
                "driver_standings_id": 2,
                "race_id": 2,
                "driver_id": 2,
                "points": 43,
                "position": 1,
                "wins": 1,
            },
            {
                "driver_standings_id": 3,
                "race_id": 2,
                "driver_id": 1,
                "points": 42,
                "position": 2,
                "wins": 1,
            },
            {
                "driver_standings_id": 4,
                "race_id": 3,
                "driver_id": 1,
                "points": 25,
                "position": 1,
                "wins": 1,
            },
        ],
        "constructor_standings": [
            {
                "constructor_standings_id": 1,
                "race_id": 2,
                "constructor_id": 2,
                "points": 43,
                "position": 1,
                "wins": 1,
            },
            {
                "constructor_standings_id": 2,
                "race_id": 2,
                "constructor_id": 1,
                "points": 42,
                "position": 2,
                "wins": 1,
            },
        ],
        "constructor_results": [
            {"constructor_results_id": 1, "race_id": 1, "constructor_id": 1, "points": 25},
            {
                "constructor_results_id": 2,
                "race_id": 1,
                "constructor_id": 2,
                "points": 18,
                "status": "D",
            },
        ],
    }
    return {name: make_table(name, rows) for name, rows in tables.items()}


@pytest.fixture
def clean_tables(raw_tables):
    return clean_all(raw_tables)


@pytest.fixture
def facts(clean_tables):
    return build_features(clean_tables)


@pytest.fixture
def warehouse(clean_tables, facts):
    return build_warehouse(clean_tables, facts)
