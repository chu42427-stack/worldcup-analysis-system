from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


SCHEMA = """
create table if not exists raw_odds_500 (
    row_id integer primary key autoincrement,
    source_file text not null,
    import_time text not null,
    match_id text,
    match_number text,
    competition text,
    kickoff_time text,
    home_team_raw text,
    away_team_raw text,
    payload_json text not null
);

create table if not exists matches (
    match_id text primary key,
    match_number text,
    competition text,
    group_name text,
    kickoff_time text,
    venue_id text,
    home_team text,
    away_team text,
    status text default 'scheduled'
);

create table if not exists teams (
    team_id text primary key,
    team_name text not null,
    confederation text,
    elo real,
    squad_strength real default 0,
    depth_score real default 0,
    style_notes text default ''
);

create table if not exists venues (
    venue_id text primary key,
    venue_name text not null,
    city text,
    country text,
    latitude real,
    longitude real,
    indoor_flag integer default 0,
    timezone text default ''
);

create table if not exists weather_snapshots (
    snapshot_id integer primary key autoincrement,
    match_id text not null,
    fetched_at text not null,
    temperature_c real,
    humidity_pct real,
    wind_kph real,
    precipitation_probability real,
    weather_code integer,
    source_confidence real default 1
);

create table if not exists manual_adjustments (
    adjustment_id integer primary key autoincrement,
    scope text not null,
    target_id text not null,
    key text not null,
    value text not null,
    source_confidence real default 1
);

create table if not exists model_runs (
    run_id text primary key,
    run_time text not null,
    model_version text not null,
    data_quality_score real not null,
    parameters_json text not null
);

create table if not exists match_predictions (
    run_id text not null,
    match_id text not null,
    home_xg real not null,
    away_xg real not null,
    home_win_prob real not null,
    draw_prob real not null,
    away_win_prob real not null,
    over_25_prob real not null,
    top_scores_json text not null,
    primary key (run_id, match_id)
);

create table if not exists recommendations (
    run_id text not null,
    match_id text not null,
    market text not null,
    label text not null,
    edge real not null,
    confidence real not null,
    risk_level text not null,
    risk_tags_json text not null,
    note text not null,
    primary key (run_id, match_id, market)
);
"""


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def write_dataframe(
    conn: sqlite3.Connection,
    table: str,
    frame: pd.DataFrame,
    if_exists: str = "append",
) -> None:
    frame.to_sql(table, conn, if_exists=if_exists, index=False)


def read_dataframe(conn: sqlite3.Connection, query: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(query, conn, params=params)
