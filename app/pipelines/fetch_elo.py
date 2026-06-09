from __future__ import annotations

import pandas as pd


def elo_from_profiles(profiles: pd.DataFrame) -> dict[str, float]:
    if profiles.empty or "team_id" not in profiles or "elo" not in profiles:
        return {}
    valid_profiles = profiles.assign(elo=pd.to_numeric(profiles["elo"], errors="coerce")).dropna(subset=["elo"])
    valid_profiles = valid_profiles[
        valid_profiles["team_id"].notna() & valid_profiles["team_id"].astype(str).str.strip().ne("")
    ]
    return {
        str(row["team_id"]): float(row["elo"])
        for _, row in valid_profiles.iterrows()
    }
