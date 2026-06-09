from pathlib import Path

import pytest

from app.pipelines.import_odds_500 import import_odds_csv, normalize_odds_frame
from app.services.team_matcher import TeamMatcher


def test_team_matcher_maps_aliases(tmp_path):
    alias_file = tmp_path / "aliases.csv"
    alias_file.write_text("alias,canonical\n\u8377\u5170,Netherlands\n", encoding="utf-8")
    matcher = TeamMatcher.from_csv(alias_file)
    assert matcher.canonical("\u8377\u5170") == "Netherlands"
    assert matcher.canonical("Unknown FC") == "Unknown FC"


def test_import_odds_csv_reads_gb18030_files(tmp_path):
    csv_path = tmp_path / "jczq_gb18030.csv"
    csv_path.write_text("场次,赛事,主队,客队\n201,国际赛,荷兰,乌兹别克\n", encoding="gb18030")

    frame = import_odds_csv(csv_path)

    assert frame.loc[0, "主队"] == "荷兰"


def test_normalize_odds_frame_maps_core_fields():
    frame = import_odds_csv(Path("tests/fixtures/jczq_500_sample.csv"))
    matcher = TeamMatcher.from_csv(Path("data/manual/team_aliases.csv"))
    normalized = normalize_odds_frame(frame, matcher)
    row = normalized.iloc[0].to_dict()
    assert row["match_id"] == "500-201-Netherlands-Uzbekistan"
    assert row["home_team"] == "Netherlands"
    assert row["away_team"] == "Uzbekistan"
    assert row["live_home_odds"] == 1.14
    assert row["live_draw_odds"] == 5.85
    assert row["live_away_odds"] == 12.5
    assert row["total_line"] == 3.0


def test_normalize_odds_frame_keeps_chinese_team_names_in_match_id():
    frame = import_odds_csv(Path("tests/fixtures/jczq_500_sample.csv"))
    frame.loc[0, "\u573a\u6b21"] = 1
    frame.loc[0, "\u4e3b\u961f"] = "\u58a8\u897f\u54e5"
    frame.loc[0, "\u5ba2\u961f"] = "\u5357\u975e"
    matcher = TeamMatcher.from_csv(Path("data/manual/team_aliases.csv"))

    normalized = normalize_odds_frame(frame, matcher)

    assert normalized.iloc[0]["match_id"] == "500-1-\u58a8\u897f\u54e5-\u5357\u975e"


def test_normalize_odds_frame_renames_all_fixture_columns_and_converts_values():
    frame = import_odds_csv(Path("tests/fixtures/jczq_500_sample.csv"))
    matcher = TeamMatcher.from_csv(Path("data/manual/team_aliases.csv"))
    normalized = normalize_odds_frame(frame, matcher)
    row = normalized.iloc[0].to_dict()

    assert set(frame.columns).isdisjoint(normalized.columns)
    assert row["open_asian_handicap_line"] == "\u7403\u534a/\u4e24\u7403"
    assert row["live_asian_handicap_line"] == "\u7403\u534a/\u4e24\u7403"
    assert isinstance(row["open_asian_handicap_line"], str)
    assert isinstance(row["live_asian_handicap_line"], str)
    assert row["open_total_line"] == 3.0
    assert row["live_over_water"] == 0.82
    assert row["home_recent_home_xg"] == 2.6
    assert row["away_xgd_rating"] == -1.1


def test_normalize_odds_frame_requires_core_source_columns():
    frame = import_odds_csv(Path("tests/fixtures/jczq_500_sample.csv")).drop(
        columns=["\u4e34\u80dc"]
    )
    matcher = TeamMatcher.from_csv(Path("data/manual/team_aliases.csv"))

    with pytest.raises(ValueError, match="missing required odds columns") as exc_info:
        normalize_odds_frame(frame, matcher)

    assert "\u4e34\u80dc" in str(exc_info.value)


def test_normalize_odds_frame_averages_slash_total_line():
    frame = import_odds_csv(Path("tests/fixtures/jczq_500_sample.csv"))
    frame["\u4e34\u5927\u5c0f\u7403"] = frame["\u4e34\u5927\u5c0f\u7403"].astype(object)
    frame.loc[0, "\u4e34\u5927\u5c0f\u7403"] = "2/2.5"
    matcher = TeamMatcher.from_csv(Path("data/manual/team_aliases.csv"))

    normalized = normalize_odds_frame(frame, matcher)

    assert normalized.iloc[0]["total_line"] == 2.25


def test_team_matcher_ignores_blank_canonical_aliases(tmp_path):
    alias_file = tmp_path / "aliases.csv"
    alias_file.write_text(
        "alias,canonical\n\u8377\u5170,\n\u6cd5\u56fd,France\n",
        encoding="utf-8",
    )

    matcher = TeamMatcher.from_csv(alias_file)

    assert matcher.canonical("\u8377\u5170") == "\u8377\u5170"
    assert matcher.canonical("\u6cd5\u56fd") == "France"
