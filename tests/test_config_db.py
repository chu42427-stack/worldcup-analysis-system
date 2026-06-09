import sqlite3

import pandas as pd
import pytest

from app.config import load_config
from app.db import connect, initialize_database, write_dataframe, read_dataframe


def test_load_config_uses_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.paths.database.endswith("data/worldcup_analysis.sqlite")
    assert cfg.model.max_goals == 8
    assert "分析系统" in cfg.paths.odds_crawler_path
    assert "数据抓取" in cfg.paths.odds_crawler_path
    assert "分析系统" in cfg.paths.odds_csv_path
    assert "数据抓取" in cfg.paths.odds_csv_path


def test_load_config_accepts_utf8_bom_toml(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[paths]\ndatabase = "data/custom.sqlite"\n\n[model]\nmax_goals = 6\n',
        encoding="utf-8-sig",
    )

    cfg = load_config(config_path)

    assert cfg.paths.database == "data/custom.sqlite"
    assert cfg.model.max_goals == 6


def test_initialize_database_creates_core_tables(tmp_path):
    db_path = tmp_path / "test.sqlite"
    with connect(db_path) as conn:
        initialize_database(conn)
        tables = pd.read_sql_query(
            "select name from sqlite_master where type='table' order by name",
            conn,
        )["name"].tolist()
    assert "raw_odds_500" in tables
    assert "matches" in tables
    assert "match_predictions" in tables
    assert "recommendations" in tables


def test_dataframe_round_trip(tmp_path):
    db_path = tmp_path / "test.sqlite"
    df = pd.DataFrame([{"match_id": "m1", "home_team": "A", "away_team": "B"}])
    with connect(db_path) as conn:
        initialize_database(conn)
        write_dataframe(conn, "matches", df, if_exists="append")
        loaded = read_dataframe(conn, "select match_id, home_team, away_team from matches")
    assert loaded.to_dict("records") == [{"match_id": "m1", "home_team": "A", "away_team": "B"}]


def test_connect_closes_after_context_manager(tmp_path):
    db_path = tmp_path / "test.sqlite"
    with connect(db_path) as conn:
        initialize_database(conn)
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        conn.execute("select 1")
