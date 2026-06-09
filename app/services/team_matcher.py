from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class TeamMatcher:
    aliases: dict[str, str]

    @classmethod
    def from_csv(cls, path: str | Path) -> "TeamMatcher":
        alias_path = Path(path)
        if not alias_path.exists():
            return cls({})
        frame = pd.read_csv(alias_path, encoding="utf-8-sig")
        aliases = {}
        for _, row in frame.iterrows():
            alias = str(row.get("alias", "")).strip()
            canonical_value = row.get("canonical", "")
            if not alias or pd.isna(canonical_value):
                continue
            canonical = str(canonical_value).strip()
            if canonical:
                aliases[alias] = canonical
        return cls(aliases)

    def canonical(self, name: str) -> str:
        cleaned = str(name or "").strip()
        return self.aliases.get(cleaned, cleaned)
