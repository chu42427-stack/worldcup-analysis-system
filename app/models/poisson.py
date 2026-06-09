from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.stats import poisson


@dataclass(frozen=True)
class ScoreProbability:
    home_goals: int
    away_goals: int
    probability: float


@dataclass(frozen=True)
class PoissonMarket:
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    over_25_prob: float
    top_scores: list[ScoreProbability]


def poisson_market(home_xg: float, away_xg: float, max_goals: int = 8) -> PoissonMarket:
    home_xg = float(home_xg)
    away_xg = float(away_xg)
    if not math.isfinite(home_xg) or not math.isfinite(away_xg) or home_xg < 0 or away_xg < 0:
        raise ValueError("xG values must be finite and non-negative")
    if isinstance(max_goals, bool) or not isinstance(max_goals, int) or max_goals < 0:
        raise ValueError("max_goals must be a non-negative integer")

    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    over_25 = float(1 - poisson.cdf(2, home_xg + away_xg))
    scores: list[ScoreProbability] = []

    for home_goals in range(max_goals + 1):
        home_prob = poisson.pmf(home_goals, home_xg)
        for away_goals in range(max_goals + 1):
            prob = float(home_prob * poisson.pmf(away_goals, away_xg))
            scores.append(ScoreProbability(home_goals, away_goals, prob))
            if home_goals > away_goals:
                home_win += prob
            elif home_goals == away_goals:
                draw += prob
            else:
                away_win += prob
    total = home_win + draw + away_win
    if total > 0:
        home_win, draw, away_win = [value / total for value in (home_win, draw, away_win)]
    top_scores = sorted(scores, key=lambda item: item.probability, reverse=True)[:8]
    return PoissonMarket(home_win, draw, away_win, over_25, top_scores)
