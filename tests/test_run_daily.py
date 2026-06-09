import json
import sqlite3
from pathlib import Path

import pandas as pd

from app.pipelines.import_odds_500 import COLUMN_MAP
from app.pipelines.run_daily import REPORT_COLUMNS, _score_or_default, run_daily


KNOWN_LABELS = {"Strong value", "Lean value", "No bet", "Avoid"}


def _row_count(database: Path, table: str) -> int:
    with sqlite3.connect(database) as conn:
        return conn.execute(f"select count(*) from {table}").fetchone()[0]


def test_run_daily_creates_predictions_and_reports(tmp_path):
    output = run_daily(
        odds_csv=Path("tests/fixtures/jczq_500_sample.csv"),
        alias_csv=Path("data/manual/team_aliases.csv"),
        database=tmp_path / "analysis.sqlite",
        outputs_dir=tmp_path / "outputs",
        date_label="2026-06-11",
    )
    assert output.database.exists()
    assert output.csv_report.exists()
    assert output.xlsx_report.exists()
    assert output.match_count == 1
    assert _row_count(output.database, "model_runs") == 1
    assert _row_count(output.database, "matches") == 1
    assert _row_count(output.database, "match_predictions") == 1
    assert _row_count(output.database, "recommendations") == 1
    with sqlite3.connect(output.database) as conn:
        match_row = conn.execute(
            "select home_team, away_team from matches"
        ).fetchone()
    assert match_row == ("荷兰", "乌兹别克")

    report = pd.read_csv(output.csv_report, encoding="utf-8-sig")
    assert list(report.columns) == REPORT_COLUMNS
    for column in [
        "date_label",
        "match",
        "market",
        "label",
        "edge",
        "confidence",
        "risk_level",
        "risk_tags_json",
        "home_win_prob",
        "market_home_prob",
    ]:
        assert column in report.columns
    assert isinstance(json.loads(report.loc[0, "risk_tags_json"]), list)
    assert report.loc[0, "label"] in KNOWN_LABELS


def test_run_daily_merges_manual_schedule_into_matches(tmp_path):
    schedule_csv = tmp_path / "schedule.csv"
    schedule_csv.write_text(
        "match_number,match_id,date,kickoff_time,round_name,group_name,venue_id,home_team,away_team\n"
        "201,,2026-06-11,2026-06-11 22:00,小组赛,A组,azteca,荷兰,乌兹别克\n",
        encoding="utf-8",
    )

    output = run_daily(
        odds_csv=Path("tests/fixtures/jczq_500_sample.csv"),
        alias_csv=Path("data/manual/team_aliases.csv"),
        database=tmp_path / "analysis.sqlite",
        outputs_dir=tmp_path / "outputs",
        date_label="2026-06-11",
        schedule_csv=schedule_csv,
    )

    with sqlite3.connect(output.database) as conn:
        match_row = conn.execute(
            """
            select kickoff_time, group_name, venue_id, home_team, away_team
            from matches
            """
        ).fetchone()

    assert match_row == ("2026-06-11 22:00", "A组", "azteca", "荷兰", "乌兹别克")


def test_run_daily_handles_missing_live_odds_with_empty_reports(tmp_path):
    raw = pd.read_csv(
        Path("tests/fixtures/jczq_500_sample.csv"),
        encoding="utf-8-sig",
        dtype=str,
    )
    live_odds_columns = [
        source for source, normalized in COLUMN_MAP.items() if normalized in {
            "live_home_odds",
            "live_draw_odds",
            "live_away_odds",
        }
    ]
    raw.loc[:, live_odds_columns] = "--"
    odds_csv = tmp_path / "missing_live_odds.csv"
    raw.to_csv(odds_csv, index=False, encoding="utf-8-sig")

    output = run_daily(
        odds_csv=odds_csv,
        alias_csv=Path("data/manual/team_aliases.csv"),
        database=tmp_path / "analysis.sqlite",
        outputs_dir=tmp_path / "outputs",
        date_label="2026-06-11",
    )

    assert output.match_count == 0
    assert output.csv_report.exists()
    assert output.xlsx_report.exists()
    assert pd.read_csv(output.csv_report, encoding="utf-8-sig").columns.tolist() == REPORT_COLUMNS
    assert _row_count(output.database, "model_runs") == 1
    assert _row_count(output.database, "match_predictions") == 0
    assert _row_count(output.database, "recommendations") == 0


def test_score_or_default_preserves_zero_score():
    assert _score_or_default(0) == 0
    assert _score_or_default(None) == 75
    assert _score_or_default(float("nan")) == 75
