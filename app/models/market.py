from __future__ import annotations

import math


def implied_probabilities(home_odds: float, draw_odds: float, away_odds: float) -> dict[str, float]:
    odds = {
        "home": float(home_odds),
        "draw": float(draw_odds),
        "away": float(away_odds),
    }
    if any(not math.isfinite(value) or value <= 1.0 for value in odds.values()):
        raise ValueError("odds must be finite and greater than 1")
    return {
        "home": 1.0 / odds["home"],
        "draw": 1.0 / odds["draw"],
        "away": 1.0 / odds["away"],
    }


def remove_margin(probabilities: dict[str, float]) -> dict[str, float]:
    normalized = {key: float(value) for key, value in probabilities.items()}
    if any(not math.isfinite(value) or value < 0 for value in normalized.values()):
        raise ValueError("probabilities must be finite and non-negative")
    total = sum(normalized.values())
    if total <= 0:
        raise ValueError("probability total must be positive")
    return {key: value / total for key, value in normalized.items()}


def market_edge(model_prob: float, fair_market_prob: float) -> float:
    model_prob = float(model_prob)
    fair_market_prob = float(fair_market_prob)
    if (
        not math.isfinite(model_prob)
        or not math.isfinite(fair_market_prob)
        or not 0 <= model_prob <= 1
        or not 0 <= fair_market_prob <= 1
    ):
        raise ValueError("probabilities must be finite values between 0 and 1")
    return model_prob - fair_market_prob
