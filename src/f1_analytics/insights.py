import logging
from pathlib import Path

import pandas as pd

from f1_analytics import plotting

logger = logging.getLogger(__name__)

Warehouse = dict[str, pd.DataFrame]

MODERN_START = 2000
MIN_CIRCUIT_RACES = 10
METHOD_NOTES = (
    "- Retirement rate counts starters whose status is a mechanical failure, collision, "
    "driver-related stoppage or other retirement. Disqualifications and non-starters are excluded.",
    "- Pit stop statistics start in 2011, the first season with pit stop data, and exclude "
    "stops longer than two minutes.",
    f"- Circuit rankings require at least {MIN_CIRCUIT_RACES} races since {MODERN_START}.",
    "- Wins are credited to each driver who shared a winning car in the 1950s.",
)


def _results(wh: Warehouse) -> pd.DataFrame:
    race = wh["dim_race"][["race_id", "year", "era", "decade", "circuit_id"]]
    return wh["fact_results"].merge(race, on="race_id", how="left")


def _circuit_names(wh: Warehouse) -> pd.DataFrame:
    return wh["dim_circuit"][["circuit_id", "circuit_name", "country"]]


def driver_leaders(wh: Warehouse, top: int = 15) -> pd.DataFrame:
    results = wh["fact_results"].assign(start=lambda d: ~d["is_dns"])
    totals = results.groupby("driver_id").agg(
        starts=("start", "sum"), wins=("is_win", "sum"), podiums=("is_podium", "sum")
    )
    totals["win_rate"] = totals["wins"] / totals["starts"]
    named = totals.join(wh["dim_driver"].set_index("driver_id")["driver_name"])
    return named.sort_values(["wins", "podiums"], ascending=False).head(top).reset_index()


def constructor_decades(wh: Warehouse, top: int = 10) -> pd.DataFrame:
    wins = _results(wh).query("is_win").groupby(["constructor_id", "decade"]).size()
    pivot = wins.unstack(fill_value=0)
    leaders = pivot.sum(axis=1).nlargest(top).index
    names = wh["dim_constructor"].set_index("constructor_id")["constructor_name"]
    return pivot.loc[leaders].rename(index=names)


def grid_win_probability(wh: Warehouse) -> pd.DataFrame:
    front = _results(wh).query("1 <= grid_position <= 10")
    rates = front.groupby(["era", "grid_position"])["is_win"].mean().unstack("grid_position")
    return rates.sort_index()


def circuit_reliability(wh: Warehouse, top: int = 12) -> pd.DataFrame:
    modern = _results(wh).query("year >= @MODERN_START and not is_dns")
    grouped = modern.groupby("circuit_id").agg(
        races=("race_id", "nunique"), starts=("result_id", "count"), dnfs=("is_dnf", "sum")
    )
    grouped["dnf_rate"] = grouped["dnfs"] / grouped["starts"]
    grouped = grouped[grouped["races"] >= MIN_CIRCUIT_RACES]
    return (
        grouped.join(_circuit_names(wh).set_index("circuit_id"))
        .sort_values("dnf_rate", ascending=False)
        .head(top)
        .reset_index()
    )


def pole_conversion(wh: Warehouse) -> pd.DataFrame:
    poles = _results(wh).query("started_on_pole and year >= @MODERN_START")
    grouped = poles.groupby("circuit_id").agg(
        races=("race_id", "nunique"), pole_win_rate=("is_win", "mean")
    )
    grouped = grouped[grouped["races"] >= MIN_CIRCUIT_RACES]
    return (
        grouped.join(_circuit_names(wh).set_index("circuit_id"))
        .sort_values("pole_win_rate", ascending=False)
        .reset_index()
    )


def pit_stop_trend(wh: Warehouse) -> pd.DataFrame:
    year = wh["dim_race"].set_index("race_id")["year"]
    stops = wh["fact_pit_stops"].query("not is_outlier_stop")
    median_stop = stops.groupby(stops["race_id"].map(year))["duration_s"].median()
    finishers = wh["fact_results"].query("is_finished")[["race_id", "driver_id"]].drop_duplicates()
    performance = wh["fact_race_performance"].query("has_pit_data")
    per_finisher = performance.merge(finishers, on=["race_id", "driver_id"])
    stops_per_finisher = per_finisher.groupby(per_finisher["race_id"].map(year))["pit_stops"].mean()
    frame = pd.DataFrame({"median_stop_s": median_stop, "stops_per_finisher": stops_per_finisher})
    frame.index.name = "year"
    return frame.dropna().reset_index()


def season_trends(wh: Warehouse) -> pd.DataFrame:
    started = _results(wh).query("not is_dns")
    by_year = started.groupby("year").agg(
        starts=("result_id", "count"), finished=("is_finished", "sum")
    )
    by_year["finish_rate"] = by_year["finished"] / by_year["starts"]
    by_year["finish_rate_5y"] = by_year["finish_rate"].rolling(5, min_periods=1).mean()
    winners = started.query("is_win").groupby("year")["driver_id"].nunique()
    by_year["distinct_winners"] = winners
    return by_year.reset_index()


def sprint_effect(wh: Warehouse) -> pd.DataFrame:
    year = wh["dim_race"].set_index("race_id")["year"]
    sprints = wh["fact_sprint_results"].dropna(subset=["positions_gained"])
    grand_prix = wh["fact_results"][wh["fact_results"]["race_id"].isin(sprints["race_id"])].dropna(
        subset=["positions_gained"]
    )

    def mean_change(frame: pd.DataFrame) -> pd.Series:
        change = frame["positions_gained"].astype("float64").abs()
        return change.groupby(frame["race_id"].map(year)).mean()

    result = pd.DataFrame({"sprint": mean_change(sprints), "grand_prix": mean_change(grand_prix)})
    result["sprint_weekends"] = sprints.groupby(sprints["race_id"].map(year))["race_id"].nunique()
    result.index.name = "year"
    return result.reset_index()


def champions(wh: Warehouse, seasons: int = 10) -> pd.DataFrame:
    year = wh["dim_race"].set_index("race_id")["year"]

    def title_holders(standings: pd.DataFrame, id_column: str, names: pd.Series) -> pd.DataFrame:
        final = standings.query("is_season_final and position == 1").copy()
        final["season"] = final["race_id"].map(year)
        final["name"] = final[id_column].map(names)
        return final.set_index("season")[["name", "points", "wins"]]

    drivers = title_holders(
        wh["fact_driver_standings"],
        "driver_id",
        wh["dim_driver"].set_index("driver_id")["driver_name"],
    )
    constructors = title_holders(
        wh["fact_constructor_standings"],
        "constructor_id",
        wh["dim_constructor"].set_index("constructor_id")["constructor_name"],
    )
    table = drivers.join(constructors["name"].rename("constructor")).sort_index().tail(seasons)
    return pd.DataFrame(
        {
            "Season": table.index,
            "Driver champion": table["name"].to_numpy(),
            "Wins": table["wins"].to_numpy(),
            "Points": [f"{p:g}" for p in table["points"]],
            "Constructor champion": table["constructor"].fillna("-").to_numpy(),
        }
    )


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _markdown_table(df: pd.DataFrame) -> str:
    header = "| " + " | ".join(df.columns) + " |"
    divider = "| " + " | ".join("---" for _ in df.columns) + " |"
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([header, divider, *rows])


def _scope_summary(wh: Warehouse) -> str:
    races = wh["dim_race"]
    results = wh["fact_results"]
    return (
        f"The dataset covers {races['year'].min()}-{races['year'].max()}: {len(races):,} races, "
        f"{results['driver_id'].nunique():,} drivers, {results['constructor_id'].nunique():,} "
        f"constructors and {races['circuit_id'].nunique():,} circuits, with {len(results):,} race "
        f"results and {len(wh['fact_lap_times']):,} recorded laps."
    )


def _findings(wh: Warehouse, frames: dict[str, pd.DataFrame]) -> list[str]:
    leader = frames["drivers"].iloc[0]
    team_wins = frames["constructors"].sum(axis=1)
    pole_by_era = frames["grid"][1]
    seasons = frames["seasons"]
    first_ten = seasons[seasons["year"] < seasons["year"].min() + 10]
    latest_ten = seasons[seasons["year"] > seasons["year"].max() - 10]
    worst_circuit = frames["reliability"].iloc[0]
    best_pole, worst_pole = frames["pole"].iloc[0], frames["pole"].iloc[-1]
    pit, sprint = frames["pit"], frames["sprint"]
    pole_rate = _results(wh).query("started_on_pole")["is_win"].mean()
    return [
        f"**{leader['driver_name']}** leads all drivers with {int(leader['wins'])} wins and "
        f"{int(leader['podiums'])} podiums ({_pct(leader['win_rate'])} win rate).",
        f"**{team_wins.idxmax()}** is the most successful constructor with "
        f"{int(team_wins.max())} race wins.",
        f"Starting on pole converts to a win {_pct(pole_rate)} of the time overall; "
        f"by era the rate ranges from {_pct(pole_by_era.min())} to {_pct(pole_by_era.max())}.",
        f"The share of starters who finished rose from {_pct(first_ten['finish_rate'].mean())} "
        f"in the first ten seasons to {_pct(latest_ten['finish_rate'].mean())} in the latest ten.",
        f"Since {MODERN_START}, **{worst_circuit['circuit_name']}** has the highest retirement "
        f"rate ({_pct(worst_circuit['dnf_rate'])} of starts).",
        f"Pole conversion since {MODERN_START} ranges from {_pct(worst_pole['pole_win_rate'])} at "
        f"{worst_pole['circuit_name']} to {_pct(best_pole['pole_win_rate'])} at "
        f"{best_pole['circuit_name']}.",
        f"Median pit lane time moved from {pit['median_stop_s'].iloc[0]:.1f}s in "
        f"{int(pit['year'].iloc[0])} to {pit['median_stop_s'].iloc[-1]:.1f}s in "
        f"{int(pit['year'].iloc[-1])}.",
        f"On sprint weekends, drivers change {sprint['sprint'].mean():.2f} positions on average "
        f"in sprints versus {sprint['grand_prix'].mean():.2f} in the Grand Prix.",
    ]


def generate_report(wh: Warehouse, reports_dir: Path) -> Path:
    figures = reports_dir / "figures"
    frames = {
        "drivers": driver_leaders(wh),
        "constructors": constructor_decades(wh),
        "grid": grid_win_probability(wh),
        "reliability": circuit_reliability(wh),
        "pole": pole_conversion(wh),
        "pit": pit_stop_trend(wh),
        "seasons": season_trends(wh),
        "sprint": sprint_effect(wh),
    }
    charts = {
        "driver_wins.png": ("Driver leaders", plotting.driver_leaders, frames["drivers"]),
        "constructor_decades.png": (
            "Constructor dominance by decade",
            plotting.constructor_decades,
            frames["constructors"],
        ),
        "grid_win_probability.png": (
            "Starting position and winning",
            plotting.grid_win_probability,
            frames["grid"],
        ),
        "circuit_reliability.png": (
            "Circuit retirement rates",
            plotting.circuit_reliability,
            frames["reliability"],
        ),
        "pole_conversion.png": ("Pole conversion", plotting.pole_conversion, frames["pole"]),
        "pit_stop_trend.png": ("Pit stop trends", plotting.pit_stop_trend, frames["pit"]),
        "season_trends.png": ("Season trends", plotting.season_trends, frames["seasons"]),
        "sprint_effect.png": ("Sprint races", plotting.sprint_effect, frames["sprint"]),
    }
    for filename, (_, draw, frame) in charts.items():
        draw(frame, figures / filename)

    findings = _findings(wh, frames)

    sections = [
        "# Formula 1 Insights Report",
        _scope_summary(wh),
        "## Key findings",
        "\n".join(f"- {item}" for item in findings),
        "## Recent champions",
        _markdown_table(champions(wh)),
    ]
    for filename, (title, _, _) in charts.items():
        sections += [f"## {title}", f"![{title}](figures/{filename})"]
    sections += [
        "## Method notes",
        "\n".join(METHOD_NOTES),
    ]
    target = reports_dir / "insights.md"
    reports_dir.mkdir(parents=True, exist_ok=True)
    target.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    return target
