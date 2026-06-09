from __future__ import annotations

from pathlib import Path

import pandas as pd


INJURY_COLUMNS = [
    "match_id",
    "team_name",
    "player_name",
    "position",
    "status",
    "xg_adjustment",
    "note",
    "source_url",
    "source_confidence",
    "updated_at",
]

PENDING_NOTES = {"伤停数据待确认", "待确认", ""}


def load_injury_records(path: str | Path) -> pd.DataFrame:
    injury_path = Path(path)
    if not injury_path.exists():
        return pd.DataFrame(columns=INJURY_COLUMNS)
    records = pd.read_csv(injury_path, encoding="utf-8-sig", dtype=str).fillna("")
    for column in INJURY_COLUMNS:
        if column not in records:
            records[column] = ""
    return records[INJURY_COLUMNS]


def injury_status_for_match(match_id: str, records: pd.DataFrame) -> str:
    if records.empty:
        return "缺失"
    match_records = records[records["match_id"] == match_id]
    if match_records.empty:
        return "缺失"
    for _, row in match_records.iterrows():
        status = str(row.get("status", "")).strip()
        player = str(row.get("player_name", "")).strip()
        note = str(row.get("note", "")).strip()
        if status or player or note not in PENDING_NOTES:
            return "已维护"
    return "待确认"

