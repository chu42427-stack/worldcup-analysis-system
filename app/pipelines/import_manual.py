from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_manual_table(path: str | Path) -> pd.DataFrame:
    table_path = Path(path)
    if not table_path.exists():
        return pd.DataFrame()
    return pd.read_csv(table_path, encoding="utf-8-sig")
