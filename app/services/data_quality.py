from __future__ import annotations


PENALTIES = {
    "odds": 0.60,
    "weather": 0.10,
    "injuries": 0.15,
    "elo": 0.10,
    "manual": 0.05,
}


def data_quality_score(flags: dict[str, bool]) -> tuple[float, list[str]]:
    score = 1.0
    warnings: list[str] = []
    for key, penalty in PENALTIES.items():
        if flags.get(key, True) is False:
            score -= penalty
            warnings.append(f"{key}_missing")
    return max(score, 0.0), warnings
