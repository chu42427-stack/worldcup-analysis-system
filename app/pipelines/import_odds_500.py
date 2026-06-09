from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from app.services.team_matcher import TeamMatcher


COLUMN_MAP = {
    "场次": "match_number",
    "赛事": "competition",
    "比赛时间": "kickoff_time",
    "主队": "home_team_raw",
    "客队": "away_team_raw",
    "初胜": "open_home_odds",
    "初平": "open_draw_odds",
    "初负": "open_away_odds",
    "临胜": "live_home_odds",
    "临平": "live_draw_odds",
    "临负": "live_away_odds",
    "初让胜": "open_handicap_home_odds",
    "初让平": "open_handicap_draw_odds",
    "初让负": "open_handicap_away_odds",
    "临让胜": "live_handicap_home_odds",
    "临让平": "live_handicap_draw_odds",
    "临让负": "live_handicap_away_odds",
    "初亚盘(如:平/半)": "open_asian_handicap_line",
    "初亚盘主水": "open_asian_home_water",
    "初亚盘客水": "open_asian_away_water",
    "临亚盘(如:半球)": "live_asian_handicap_line",
    "临亚盘主水": "live_asian_home_water",
    "临亚盘客水": "live_asian_away_water",
    "初大小球": "open_total_line",
    "初大水": "open_over_water",
    "初小水": "open_under_water",
    "临大小球": "total_line",
    "临大水": "live_over_water",
    "临小水": "live_under_water",
    "主近6xG": "home_recent_xg",
    "主近6xGA": "home_recent_xga",
    "客近6xG": "away_recent_xg",
    "客近6xGA": "away_recent_xga",
    "主近5主xG": "home_recent_home_xg",
    "主近5主xGA": "home_recent_home_xga",
    "客近5客xG": "away_recent_away_xg",
    "客近5客xGA": "away_recent_away_xga",
    "主伤停xG修正": "home_injury_xg_adjustment",
    "客伤停xG修正": "away_injury_xg_adjustment",
    "节奏系数": "tempo_factor",
    "ZIP闷战系数": "low_event_factor",
    "主xGD评分": "home_xgd_rating",
    "客xGD评分": "away_xgd_rating",
    "主分": "home_score",
    "客分": "away_score",
    "容差": "tolerance",
}

REQUIRED_SOURCE_COLUMNS = [
    "场次",
    "赛事",
    "主队",
    "客队",
    "临胜",
    "临平",
    "临负",
    "临大小球",
]


def import_odds_csv(path: str | Path) -> pd.DataFrame:
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise last_error or UnicodeDecodeError("utf-8", b"", 0, 1, "unable to decode odds CSV")


def _to_number(value) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text in {"", "--"}:
        return None
    if "/" in text:
        parts = [float(match) for match in re.findall(r"-?\d+(?:\.\d+)?", text)]
        if len(parts) >= 2:
            return sum(parts) / len(parts)
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def _match_id(match_number: str, home_team: str, away_team: str) -> str:
    home_slug = re.sub(r"[^\w]+", "-", home_team, flags=re.UNICODE).strip("-")
    away_slug = re.sub(r"[^\w]+", "-", away_team, flags=re.UNICODE).strip("-")
    home_slug = home_slug or "home"
    away_slug = away_slug or "away"
    return f"500-{match_number}-{home_slug}-{away_slug}"


def normalize_odds_frame(frame: pd.DataFrame, matcher: TeamMatcher) -> pd.DataFrame:
    missing_columns = [column for column in REQUIRED_SOURCE_COLUMNS if column not in frame]
    if missing_columns:
        raise ValueError(
            "missing required odds columns: " + ", ".join(missing_columns)
        )

    normalized = frame.rename(columns=COLUMN_MAP).copy()
    for column in COLUMN_MAP.values():
        if column not in normalized:
            normalized[column] = None

    normalized["home_team"] = normalized["home_team_raw"].map(matcher.canonical)
    normalized["away_team"] = normalized["away_team_raw"].map(matcher.canonical)
    normalized["match_number"] = normalized["match_number"].astype(str)
    normalized["match_id"] = normalized.apply(
        lambda row: _match_id(row["match_number"], row["home_team"], row["away_team"]),
        axis=1,
    )

    numeric_columns = [
        "open_home_odds",
        "open_draw_odds",
        "open_away_odds",
        "live_home_odds",
        "live_draw_odds",
        "live_away_odds",
        "open_handicap_home_odds",
        "open_handicap_draw_odds",
        "open_handicap_away_odds",
        "live_handicap_home_odds",
        "live_handicap_draw_odds",
        "live_handicap_away_odds",
        "open_asian_home_water",
        "open_asian_away_water",
        "live_asian_home_water",
        "live_asian_away_water",
        "open_total_line",
        "open_over_water",
        "open_under_water",
        "total_line",
        "live_over_water",
        "live_under_water",
        "home_recent_xg",
        "home_recent_xga",
        "away_recent_xg",
        "away_recent_xga",
        "home_recent_home_xg",
        "home_recent_home_xga",
        "away_recent_away_xg",
        "away_recent_away_xga",
        "home_injury_xg_adjustment",
        "away_injury_xg_adjustment",
        "tempo_factor",
        "low_event_factor",
        "home_xgd_rating",
        "away_xgd_rating",
        "home_score",
        "away_score",
        "tolerance",
    ]
    for column in numeric_columns:
        normalized[column] = normalized[column].map(_to_number)

    return normalized
