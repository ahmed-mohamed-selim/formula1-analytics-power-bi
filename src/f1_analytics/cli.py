import argparse
import logging
import sys
from pathlib import Path

from f1_analytics import __version__, pipeline
from f1_analytics.config import Paths
from f1_analytics.ingestion import SourceDataError
from f1_analytics.validation import DataQualityError

FORMATS = {"parquet": ["parquet"], "csv": ["csv"], "both": ["parquet", "csv"]}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="f1-analytics",
        description="Build the Formula 1 analytics warehouse and insight report.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="Project root (default: current directory)"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("build", "Clean the source data and write the star schema"),
        ("run", "Build the warehouse, then generate the insight report"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--source", type=Path, required=True, help="Source ZIP or CSV folder")
        command.add_argument(
            "--format", choices=sorted(FORMATS), default="both", help="Warehouse output format"
        )
    commands.add_parser("report", help="Generate the insight report from an existing warehouse")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    paths = Paths.from_root(args.root)
    try:
        warehouse = None
        if args.command in ("build", "run"):
            warehouse = pipeline.build(args.source, paths, FORMATS[args.format])
        if args.command in ("report", "run"):
            target = pipeline.report(warehouse, paths)
            logging.getLogger(__name__).info("Report written to %s", target)
    except (SourceDataError, DataQualityError, FileNotFoundError) as error:
        logging.getLogger(__name__).error("%s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
