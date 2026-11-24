from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

ACCENT = "#E10600"
INK = "#15151E"
MUTED = "#8A8D93"
GRID = "#E5E7EB"
SEQUENTIAL = ["#9CA3AF", "#6B7280", "#3B82F6", ACCENT, INK]

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "xtick.color": INK,
        "ytick.color": INK,
        "legend.frameon": False,
    }
)


def _save(fig: Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def _horizontal_bars(
    labels: pd.Series, values: pd.Series, title: str, xlabel: str, path: Path, fmt: str = "{:,.0f}"
) -> Path:
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(values) + 1.6))
    positions = np.arange(len(values))[::-1]
    ax.barh(positions, values, color=ACCENT, height=0.65)
    ax.set_yticks(positions, labels)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    for y, value in zip(positions, values, strict=True):
        ax.text(value, y, " " + fmt.format(value), va="center", color=INK, fontsize=9)
    ax.set_xlim(0, values.max() * 1.12)
    return _save(fig, path)


def driver_leaders(df: pd.DataFrame, path: Path) -> Path:
    return _horizontal_bars(df["driver_name"], df["wins"], "Most race wins", "Race wins", path)


def constructor_decades(pivot: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 0.5 * len(pivot) + 2))
    image = ax.imshow(pivot.to_numpy(), cmap="Reds", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)), [f"{c}s" for c in pivot.columns])
    ax.set_yticks(range(len(pivot.index)), pivot.index)
    ax.grid(False)
    ax.set_title("Race wins by constructor and decade")
    peak = pivot.to_numpy().max()
    for (row, col), value in np.ndenumerate(pivot.to_numpy()):
        if value:
            ax.text(
                col,
                row,
                int(value),
                ha="center",
                va="center",
                fontsize=9,
                color="white" if value > peak * 0.55 else INK,
            )
    fig.colorbar(image, ax=ax, label="Wins", shrink=0.8)
    return _save(fig, path)


def grid_win_probability(pivot: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    for color, (era, row) in zip(SEQUENTIAL, pivot.iterrows(), strict=False):
        ax.plot(row.index, row.to_numpy() * 100, marker="o", ms=4, lw=2, color=color, label=era)
    ax.set_xticks(range(1, 11))
    ax.set_xlabel("Starting grid position")
    ax.set_ylabel("Win probability (%)")
    ax.set_title("Win probability by starting position and era")
    ax.legend(title="Era")
    return _save(fig, path)


def circuit_reliability(df: pd.DataFrame, path: Path) -> Path:
    return _horizontal_bars(
        df["circuit_name"],
        df["dnf_rate"] * 100,
        "Highest retirement rate by circuit (since 2000)",
        "Retirements per start (%)",
        path,
        fmt="{:.1f}%",
    )


def pole_conversion(df: pd.DataFrame, path: Path) -> Path:
    return _horizontal_bars(
        df["circuit_name"],
        df["pole_win_rate"] * 100,
        "Pole position conversion by circuit (since 2000)",
        "Pole starters who won the race (%)",
        path,
        fmt="{:.0f}%",
    )


def pit_stop_trend(df: pd.DataFrame, path: Path) -> Path:
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True)
    top.plot(df["year"], df["median_stop_s"], color=ACCENT, lw=2.2, marker="o", ms=4)
    top.set_ylabel("Median pit lane time (s)")
    top.set_title("Pit stop duration and frequency")
    bottom.plot(df["year"], df["stops_per_finisher"], color=INK, lw=2.2, marker="o", ms=4)
    bottom.set_ylabel("Stops per finisher")
    bottom.set_xlabel("Season")
    return _save(fig, path)


def season_trends(df: pd.DataFrame, path: Path) -> Path:
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True)
    top.plot(df["year"], df["finish_rate"] * 100, color=MUTED, lw=1.2, label="Season")
    top.plot(df["year"], df["finish_rate_5y"] * 100, color=ACCENT, lw=2.4, label="5-season average")
    top.set_ylabel("Starters who finished (%)")
    top.set_title("Reliability and competitive balance over time")
    top.legend()
    bottom.bar(df["year"], df["distinct_winners"], color=INK, width=0.75)
    bottom.set_ylabel("Different race winners")
    bottom.set_xlabel("Season")
    bottom.set_xlim(df["year"].min() - 1, df["year"].max() + 1)
    return _save(fig, path)


def sprint_effect(df: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(df))
    ax.bar(x - 0.2, df["sprint"], width=0.4, color=ACCENT, label="Sprint")
    ax.bar(x + 0.2, df["grand_prix"], width=0.4, color=INK, label="Grand Prix")
    ax.set_xticks(x, df["year"].astype(str))
    ax.set_xlabel("Season")
    ax.set_ylabel("Average positions changed vs. grid")
    ax.set_title("Position changes: sprint vs. Grand Prix (sprint weekends)")
    ax.legend()
    return _save(fig, path)
