from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import load_config
from app.db import connect, initialize_database, write_dataframe
from app.models.elo import elo_to_goal_delta
from app.models.market import implied_probabilities, market_edge, remove_margin
from app.models.poisson import poisson_market
from app.models.xg import build_expected_goals
from app.pipelines.fetch_weather import fetch_open_meteo, parse_open_meteo_response
from app.pipelines.import_odds_500 import import_odds_csv, normalize_odds_frame
from app.services.data_quality import data_quality_score
from app.services.recommendations import classify_recommendation
from app.services.team_matcher import TeamMatcher


PREDICTION_COLUMNS = [
    "run_id",
    "match_id",
    "home_xg",
    "away_xg",
    "home_win_prob",
    "draw_prob",
    "away_win_prob",
    "over_25_prob",
    "top_scores_json",
]

MATCH_COLUMNS = [
    "match_id",
    "match_number",
    "competition",
    "group_name",
    "kickoff_time",
    "venue_id",
    "home_team",
    "away_team",
    "status",
]

REPORT_COLUMNS = [
    "run_id",
    "match_id",
    "market",
    "label",
    "edge",
    "confidence",
    "risk_level",
    "risk_tags_json",
    "note",
    "date_label",
    "match",
    "home_win_prob",
    "market_home_prob",
]

RECOMMENDATION_COLUMNS = [
    "run_id",
    "match_id",
    "market",
    "label",
    "edge",
    "confidence",
    "risk_level",
    "risk_tags_json",
    "note",
]

WEATHER_COLUMNS = [
    "match_id",
    "fetched_at",
    "temperature_c",
    "humidity_pct",
    "wind_kph",
    "precipitation_probability",
    "weather_code",
    "source_confidence",
]


@dataclass(frozen=True)
class DailyRunOutput:
    database: Path
    csv_report: Path
    xlsx_report: Path
    match_count: int


def _optional(value: Any) -> Any:
    return None if pd.isna(value) else value


def _score_or_default(value: Any, default: float = 75) -> float:
    score = _optional(value)
    return float(default) if score is None else float(score)


def _score_row(
    row: pd.Series,
    run_id: str,
    date_label: str,
    weather_available: bool = False,
) -> tuple[dict, dict]:
    market = remove_margin(
        implied_probabilities(
            row["live_home_odds"], row["live_draw_odds"], row["live_away_odds"]
        )
    )
    elo_delta = elo_to_goal_delta(
        _score_or_default(row.get("home_score")),
        _score_or_default(row.get("away_score")),
    )
    xg = build_expected_goals(
        market_total=_optional(row.get("total_line")),
        elo_goal_delta=elo_delta,
        home_recent_xg=_optional(row.get("home_recent_xg")),
        away_recent_xg=_optional(row.get("away_recent_xg")),
        home_injury_adjustment=_optional(row.get("home_injury_xg_adjustment")),
        away_injury_adjustment=_optional(row.get("away_injury_xg_adjustment")),
        tempo_factor=_optional(row.get("tempo_factor")),
        low_event_factor=_optional(row.get("low_event_factor")),
    )
    poisson = poisson_market(xg.home_xg, xg.away_xg)
    flags = {
        "odds": True,
        "weather": weather_available,
        "injuries": pd.notna(row.get("home_injury_xg_adjustment")),
    }
    quality, warnings = data_quality_score(flags)
    edge = market_edge(poisson.home_win_prob, market["home"])
    recommendation = classify_recommendation(
        edge=edge, data_quality=quality, risk_tags=warnings
    )
    prediction = {
        "run_id": run_id,
        "match_id": row["match_id"],
        "home_xg": xg.home_xg,
        "away_xg": xg.away_xg,
        "home_win_prob": poisson.home_win_prob,
        "draw_prob": poisson.draw_prob,
        "away_win_prob": poisson.away_win_prob,
        "over_25_prob": poisson.over_25_prob,
        "top_scores_json": json.dumps(
            [score.__dict__ for score in poisson.top_scores], ensure_ascii=False
        ),
    }
    rec = {
        "run_id": run_id,
        "match_id": row["match_id"],
        "market": "home_win",
        "label": recommendation.label,
        "edge": recommendation.edge,
        "confidence": recommendation.confidence,
        "risk_level": recommendation.risk_level,
        "risk_tags_json": json.dumps(recommendation.risk_tags, ensure_ascii=False),
        "note": recommendation.note,
        "date_label": date_label,
        "match": f"{row['home_team_raw']} vs {row['away_team_raw']}",
        "home_win_prob": poisson.home_win_prob,
        "market_home_prob": market["home"],
    }
    return prediction, rec


SCHEDULE_COLUMNS = [
    "match_number",
    "match_id",
    "date",
    "kickoff_time",
    "round_name",
    "group_name",
    "venue_id",
    "home_team",
    "away_team",
]


def _load_schedule(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=SCHEDULE_COLUMNS)
    schedule = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    for column in SCHEDULE_COLUMNS:
        if column not in schedule:
            schedule[column] = ""
    schedule["match_number"] = schedule["match_number"].astype(str)
    return schedule[SCHEDULE_COLUMNS]


def _matches_frame(normalized: pd.DataFrame, schedule: pd.DataFrame | None = None) -> pd.DataFrame:
    if normalized.empty:
        return pd.DataFrame(columns=MATCH_COLUMNS)
    frame = normalized[
        [
            "match_id",
            "match_number",
            "competition",
            "kickoff_time",
            "home_team_raw",
            "away_team_raw",
        ]
    ].copy()
    frame["match_number"] = frame["match_number"].astype(str)
    if schedule is not None and not schedule.empty:
        schedule_fields = schedule[
            [
                "match_number",
                "date",
                "kickoff_time",
                "round_name",
                "group_name",
                "venue_id",
                "home_team",
                "away_team",
            ]
        ].rename(
            columns={
                "kickoff_time": "schedule_kickoff_time",
                "home_team": "schedule_home_team",
                "away_team": "schedule_away_team",
            }
        )
        frame = frame.merge(schedule_fields, on="match_number", how="left")
    else:
        frame["date"] = ""
        frame["schedule_kickoff_time"] = ""
        frame["round_name"] = ""
        frame["group_name"] = ""
        frame["venue_id"] = ""
        frame["schedule_home_team"] = ""
        frame["schedule_away_team"] = ""

    frame["kickoff_time"] = frame["schedule_kickoff_time"].where(
        frame["schedule_kickoff_time"].fillna("") != "",
        frame["kickoff_time"],
    )
    frame["home_team_raw"] = frame["schedule_home_team"].where(
        frame["schedule_home_team"].fillna("") != "",
        frame["home_team_raw"],
    )
    frame["away_team_raw"] = frame["schedule_away_team"].where(
        frame["schedule_away_team"].fillna("") != "",
        frame["away_team_raw"],
    )
    frame["group_name"] = frame["group_name"].fillna("")
    frame["venue_id"] = frame["venue_id"].fillna("")
    frame = frame[
        [
            "match_id",
            "match_number",
            "competition",
            "group_name",
            "kickoff_time",
            "venue_id",
            "home_team_raw",
            "away_team_raw",
        ]
    ].copy()
    frame = frame.rename(
        columns={
            "home_team_raw": "home_team",
            "away_team_raw": "away_team",
        }
    )
    frame["status"] = "scheduled"
    return frame.drop_duplicates(subset=["match_id"])[MATCH_COLUMNS]


def _write_matches(conn, matches: pd.DataFrame) -> None:
    if matches.empty:
        return
    conn.executemany(
        """
        insert or replace into matches (
            match_id,
            match_number,
            competition,
            group_name,
            kickoff_time,
            venue_id,
            home_team,
            away_team,
            status
        )
        values (
            :match_id,
            :match_number,
            :competition,
            :group_name,
            :kickoff_time,
            :venue_id,
            :home_team,
            :away_team,
            :status
        )
        """,
        matches.to_dict("records"),
    )


def _load_venues(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["venue_id", "latitude", "longitude"])
    venues = pd.read_csv(path, encoding="utf-8-sig")
    for column in ["venue_id", "latitude", "longitude"]:
        if column not in venues:
            venues[column] = None
    return venues[["venue_id", "latitude", "longitude"]]


def _weather_frame(
    matches: pd.DataFrame,
    venues_csv: Path | None,
    enabled: bool,
    weather_fetcher=fetch_open_meteo,
) -> pd.DataFrame:
    if not enabled or matches.empty:
        return pd.DataFrame(columns=WEATHER_COLUMNS)
    venues = _load_venues(venues_csv)
    if venues.empty:
        return pd.DataFrame(columns=WEATHER_COLUMNS)
    candidates = matches.merge(venues, on="venue_id", how="left")
    payloads_by_venue: dict[str, dict[str, Any]] = {}
    snapshots = []
    for _, row in candidates.iterrows():
        if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
            continue
        venue_id = str(row.get("venue_id") or "")
        try:
            if venue_id not in payloads_by_venue:
                payloads_by_venue[venue_id] = weather_fetcher(
                    float(row["latitude"]), float(row["longitude"])
                )
            payload = payloads_by_venue[venue_id]
        except Exception:
            continue
        snapshots.append(parse_open_meteo_response(row["match_id"], payload))
    return pd.DataFrame(snapshots, columns=WEATHER_COLUMNS)


def run_daily(
    odds_csv: Path,
    alias_csv: Path,
    database: Path,
    outputs_dir: Path,
    date_label: str,
    schedule_csv: Path | None = None,
    venues_csv: Path | None = None,
    fetch_weather_enabled: bool = False,
    weather_fetcher=fetch_open_meteo,
) -> DailyRunOutput:
    matcher = TeamMatcher.from_csv(alias_csv)
    raw = import_odds_csv(odds_csv)
    normalized = normalize_odds_frame(raw, matcher)
    schedule = _load_schedule(schedule_csv)
    matches_frame = _matches_frame(normalized, schedule)
    weather_frame = _weather_frame(
        matches_frame, venues_csv, fetch_weather_enabled, weather_fetcher
    )
    run_id = uuid.uuid4().hex
    run_time = datetime.now(timezone.utc).isoformat()
    outputs_dir.mkdir(parents=True, exist_ok=True)

    predictions = []
    recommendations = []
    weather_available_matches = set()
    if not weather_frame.empty:
        weather_available_matches = set(
            weather_frame[weather_frame["source_confidence"] > 0]["match_id"].tolist()
        )
    for _, row in normalized.iterrows():
        if (
            pd.isna(row.get("live_home_odds"))
            or pd.isna(row.get("live_draw_odds"))
            or pd.isna(row.get("live_away_odds"))
        ):
            continue
        prediction, recommendation = _score_row(
            row,
            run_id,
            date_label,
            weather_available=row["match_id"] in weather_available_matches,
        )
        predictions.append(prediction)
        recommendations.append(recommendation)

    predictions_frame = pd.DataFrame(predictions, columns=PREDICTION_COLUMNS)
    report = pd.DataFrame(recommendations, columns=REPORT_COLUMNS)
    csv_report = outputs_dir / f"daily_screening_{date_label}.csv"
    xlsx_report = outputs_dir / f"daily_screening_{date_label}.xlsx"
    report.to_csv(csv_report, index=False, encoding="utf-8-sig")
    report.to_excel(xlsx_report, index=False)

    with connect(database) as conn:
        initialize_database(conn)
        write_dataframe(
            conn,
            "model_runs",
            pd.DataFrame(
                [
                    {
                        "run_id": run_id,
                        "run_time": run_time,
                        "model_version": "v0.1",
                        "data_quality_score": 0.75,
                        "parameters_json": "{}",
                    }
                ]
            ),
        )
        write_dataframe(conn, "match_predictions", predictions_frame)
        _write_matches(conn, matches_frame)
        write_dataframe(conn, "weather_snapshots", weather_frame)
        # DB recommendations stay normalized; reports keep dashboard display fields.
        write_dataframe(conn, "recommendations", report[RECOMMENDATION_COLUMNS])

    return DailyRunOutput(database, csv_report, xlsx_report, len(report))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().date().isoformat())
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    schedule_csv = Path(cfg.paths.manual_dir) / "schedule.csv"
    venues_csv = Path(cfg.paths.manual_dir) / "venues.csv"
    output = run_daily(
        odds_csv=Path(cfg.paths.odds_csv_path),
        alias_csv=Path(cfg.paths.manual_dir) / "team_aliases.csv",
        database=Path(cfg.paths.database),
        outputs_dir=Path(cfg.paths.outputs_dir),
        date_label=args.date,
        schedule_csv=schedule_csv if schedule_csv.exists() else None,
        venues_csv=venues_csv if venues_csv.exists() else None,
        fetch_weather_enabled=cfg.weather.enabled,
    )
    print(f"done: {output.match_count} matches -> {output.csv_report}")


if __name__ == "__main__":
    main()
