import pytest

from f1_analytics import insights, plotting


def test_driver_leaders_ranks_by_wins(warehouse):
    leaders = insights.driver_leaders(warehouse).set_index("driver_name")
    assert leaders.index[0] == "Ann Alpha"
    assert leaders.loc["Ann Alpha", ["wins", "starts"]].tolist() == [2, 4]
    assert leaders.loc["Ann Alpha", "win_rate"] == pytest.approx(0.5)


def test_constructor_decades_counts_wins_by_team(warehouse):
    pivot = insights.constructor_decades(warehouse)
    assert pivot.loc["Red", 2020] == 2
    assert pivot.loc["Blue", 2020] == 1


def test_season_trends_excludes_non_starters(warehouse):
    seasons = insights.season_trends(warehouse).set_index("year")
    assert seasons.loc[2020, "starts"] == 6
    assert seasons.loc[2020, "finish_rate"] == pytest.approx(5 / 6)
    assert seasons.loc[2021, "finish_rate"] == pytest.approx(0.5)
    assert seasons.loc[2020, "distinct_winners"] == 2


def test_sprint_effect_compares_sprint_and_grand_prix(warehouse):
    effect = insights.sprint_effect(warehouse).set_index("year")
    assert effect.loc[2020, "sprint"] == pytest.approx(1.0)
    assert effect.loc[2020, "grand_prix"] == pytest.approx(0.0)
    assert effect.loc[2020, "sprint_weekends"] == 1


def test_champions_table(warehouse):
    table = insights.champions(warehouse)
    assert table["Driver champion"].tolist() == ["Bob Beta", "Ann Alpha"]
    assert table["Constructor champion"].tolist() == ["Blue", "-"]


def test_chart_is_written_to_disk(warehouse, tmp_path):
    target = plotting.driver_leaders(insights.driver_leaders(warehouse), tmp_path / "wins.png")
    assert target.exists()
    assert target.stat().st_size > 0
