from dataclasses import dataclass
from pathlib import Path

ERA_BINS = (1949, 1969, 1989, 2013, 2021, 2100)
ERA_LABELS = (
    "1950-69 Pioneer",
    "1970-89 Classic",
    "1990-2013 V10/V8",
    "2014-21 Hybrid",
    "2022+ Ground effect",
)

OUTLIER_LAP_RATIO = 2.0
OUTLIER_PIT_STOP_MS = 120_000

COUNTRY_ALIASES = {
    "UK": "United Kingdom",
    "USA": "United States",
    "UAE": "United Arab Emirates",
    "Korea": "South Korea",
}


@dataclass(frozen=True)
class Paths:
    root: Path
    raw: Path
    warehouse: Path
    reports: Path
    figures: Path

    @classmethod
    def from_root(cls, root: Path) -> "Paths":
        root = Path(root).resolve()
        return cls(
            root=root,
            raw=root / "data" / "raw",
            warehouse=root / "data" / "warehouse",
            reports=root / "reports",
            figures=root / "reports" / "figures",
        )
