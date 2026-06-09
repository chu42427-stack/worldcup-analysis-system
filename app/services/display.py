from __future__ import annotations

import csv
from pathlib import Path


def load_team_display(path: str | Path) -> dict[str, dict[str, str]]:
    display_path = Path(path)
    if not display_path.exists():
        return {}
    with display_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        result: dict[str, dict[str, str]] = {}
        for row in rows:
            team_name = (row.get("team_name") or "").strip()
            if not team_name:
                continue
            result[team_name] = {
                "display_name": (row.get("display_name") or team_name).strip(),
                "country_code": (row.get("country_code") or "").strip(),
                "flag_emoji": (row.get("flag_emoji") or "").strip(),
            }
        return result


def format_team_label(team_name: str, display: dict[str, dict[str, str]]) -> str:
    metadata = display.get(team_name, {})
    name = metadata.get("display_name") or team_name
    flag = metadata.get("flag_emoji") or ""
    return f"{flag} {name}".strip()


def format_match_label(
    home_team: str, away_team: str, display: dict[str, dict[str, str]]
) -> str:
    return f"{format_team_label(home_team, display)} vs {format_team_label(away_team, display)}"

