from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectedGoals:
    home_xg: float
    away_xg: float
    total_xg: float
    tempo_factor: float
    low_event_factor: float


def _coalesce(value: float | None, default: float) -> float:
    return default if value is None else float(value)


def _validate_optional_positive(value: float | None, name: str) -> None:
    if value is None:
        return
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and greater than 0")


def _validate_optional_non_negative(value: float | None, name: str) -> None:
    if value is None:
        return
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")


def _validate_optional_finite(value: float | None, name: str) -> None:
    if value is None:
        return
    if not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")


def build_expected_goals(
    market_total: float | None,
    elo_goal_delta: float,
    home_recent_xg: float | None,
    away_recent_xg: float | None,
    home_injury_adjustment: float | None,
    away_injury_adjustment: float | None,
    tempo_factor: float | None,
    low_event_factor: float | None,
) -> ExpectedGoals:
    _validate_optional_positive(market_total, "market_total")
    _validate_optional_positive(tempo_factor, "tempo_factor")
    _validate_optional_positive(low_event_factor, "low_event_factor")
    _validate_optional_non_negative(home_recent_xg, "home_recent_xg")
    _validate_optional_non_negative(away_recent_xg, "away_recent_xg")
    _validate_optional_finite(home_injury_adjustment, "home_injury_adjustment")
    _validate_optional_finite(away_injury_adjustment, "away_injury_adjustment")
    if not math.isfinite(float(elo_goal_delta)):
        raise ValueError("elo_goal_delta must be finite")

    total_base = _coalesce(market_total, 2.5)
    home_recent = _coalesce(home_recent_xg, total_base / 2)
    away_recent = _coalesce(away_recent_xg, total_base / 2)
    recent_gap = (home_recent - away_recent) * 0.25
    split_delta = elo_goal_delta + recent_gap
    home = total_base / 2 + split_delta / 2
    away = total_base / 2 - split_delta / 2
    home += _coalesce(home_injury_adjustment, 0)
    away += _coalesce(away_injury_adjustment, 0)
    tempo = _coalesce(tempo_factor, 1.0)
    low_event = _coalesce(low_event_factor, 1.0)
    home = max(home * tempo * low_event, 0.05)
    away = max(away * tempo * low_event, 0.05)
    return ExpectedGoals(
        home_xg=home,
        away_xg=away,
        total_xg=home + away,
        tempo_factor=tempo,
        low_event_factor=low_event,
    )
