from __future__ import annotations


def elo_expected_score(team_elo: float, opponent_elo: float) -> float:
    return 1.0 / (1.0 + 10 ** ((opponent_elo - team_elo) / 400.0))


def elo_to_goal_delta(team_elo: float, opponent_elo: float) -> float:
    return max(min((team_elo - opponent_elo) / 500.0, 1.2), -1.2)
