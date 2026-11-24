import os

import pytest

from f1_analytics.cli import main

ARCHIVE = os.environ.get("F1_ARCHIVE")


def test_missing_source_returns_error_code(tmp_path):
    exit_code = main(["--root", str(tmp_path), "build", "--source", str(tmp_path / "missing.zip")])
    assert exit_code == 1


def test_report_requires_an_existing_warehouse(tmp_path):
    assert main(["--root", str(tmp_path), "report"]) == 1


@pytest.mark.skipif(not ARCHIVE, reason="Set F1_ARCHIVE to the source ZIP to run the full pipeline")
def test_full_pipeline_on_real_archive(tmp_path):
    assert main(["--root", str(tmp_path), "run", "--source", ARCHIVE]) == 0
    assert (tmp_path / "reports" / "insights.md").exists()
    assert len(list((tmp_path / "reports" / "figures").glob("*.png"))) == 8
    assert len(list((tmp_path / "data" / "warehouse" / "parquet").glob("*.parquet"))) == 14
    assert len(list((tmp_path / "data" / "warehouse" / "csv").glob("*.csv"))) == 14
