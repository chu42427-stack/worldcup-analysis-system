# World Cup Analysis System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Streamlit + SQLite football betting analysis system that imports 500.com odds, calculates market/Elo/Poisson signals, ranks daily matches, and exposes single-match analysis.

**Architecture:** Use a small Python package under `app/` with focused modules for configuration, persistence, data import, models, services, and the Streamlit dashboard. Data is stored in SQLite and report files are written to `outputs/`; external and manual data sources are cache-first and replaceable.

**Tech Stack:** Python 3.11+, pandas, scipy, requests, beautifulsoup4, streamlit, openpyxl, pytest, SQLite.

---

## File Structure

- `requirements.txt`: project dependencies.
- `README.md`: setup and run commands.
- `.gitignore`: ignore local databases, outputs, caches, and visual companion files.
- `config.example.toml`: editable local settings template.
- `app/__init__.py`: package marker.
- `app/config.py`: load TOML config with sane defaults.
- `app/db.py`: SQLite schema creation and DataFrame helpers.
- `app/pipelines/import_odds_500.py`: import and normalize 500.com CSV output.
- `app/pipelines/import_manual.py`: load manual seed CSVs.
- `app/pipelines/fetch_weather.py`: Open-Meteo weather adapter with cache-friendly output.
- `app/pipelines/fetch_elo.py`: free Elo/manual fallback adapter.
- `app/pipelines/run_daily.py`: orchestrate daily import, modeling, recommendation, and export.
- `app/models/market.py`: implied probability, margin removal, odds movement.
- `app/models/poisson.py`: scoreline simulation and market probabilities.
- `app/models/elo.py`: Elo gap conversion helpers.
- `app/models/xg.py`: blend model inputs into expected goals.
- `app/models/scoring.py`: combine model output into labels.
- `app/services/team_matcher.py`: team alias normalization.
- `app/services/data_quality.py`: source completeness and warnings.
- `app/services/recommendations.py`: betting recommendation labels and risk tags.
- `app/dashboard.py`: Streamlit app.
- `data/manual/*.csv`: seed and override files.
- `tests/`: unit and integration tests.

---

### Task 1: Project Scaffold And Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `README.md`
- Create: `config.example.toml`
- Create: `app/__init__.py`
- Create directories: `app/models`, `app/pipelines`, `app/services`, `data/manual`, `data/raw`, `data/processed`, `outputs`, `tests`

- [ ] **Step 1: Create dependency file**

Create `requirements.txt`:

```text
pandas>=2.2.0
numpy>=1.26.0
scipy>=1.12.0
requests>=2.31.0
beautifulsoup4>=4.12.0
streamlit>=1.36.0
openpyxl>=3.1.0
tomli>=2.0.1; python_version < "3.11"
pytest>=8.2.0
```

- [ ] **Step 2: Create ignore rules**

Create `.gitignore`:

```text
__pycache__/
.pytest_cache/
.streamlit/
.superpowers/
*.pyc
*.sqlite
*.db
data/raw/*
data/processed/*
outputs/*
!data/raw/.gitkeep
!data/processed/.gitkeep
!outputs/.gitkeep
config.toml
```

- [ ] **Step 3: Create config template**

Create `config.example.toml`:

```toml
[paths]
database = "data/worldcup_analysis.sqlite"
manual_dir = "data/manual"
raw_dir = "data/raw"
processed_dir = "data/processed"
outputs_dir = "outputs"
odds_crawler_path = "C:/Users/A/Desktop/分析系统/数据抓取/crawl_500_jczq.py"
odds_csv_path = "C:/Users/A/Desktop/分析系统/数据抓取/jczq_500.csv"

[model]
market_weight = 0.45
elo_weight = 0.25
recent_form_weight = 0.15
manual_weight = 0.15
max_goals = 8
strong_value_edge = 0.07
lean_value_edge = 0.035

[weather]
enabled = true
stale_hours = 6
```

- [ ] **Step 4: Create README**

Create `README.md`:

```markdown
# World Cup Betting Analysis System

Local analysis system for football betting practice.

## Setup

```powershell
python -m pip install -r requirements.txt
Copy-Item config.example.toml config.toml
```

Edit `config.toml` if the 500.com crawler or CSV paths are different.

## Run Daily Pipeline

```powershell
python -m app.pipelines.run_daily --date 2026-06-11
```

## Run Dashboard

```powershell
streamlit run app/dashboard.py
```

## Notes

The system produces model probabilities and risk labels for analysis. It does not guarantee betting outcomes.
```

- [ ] **Step 5: Create package markers and keep files**

Create empty files:

```text
app/__init__.py
app/models/__init__.py
app/pipelines/__init__.py
app/services/__init__.py
data/raw/.gitkeep
data/processed/.gitkeep
outputs/.gitkeep
```

- [ ] **Step 6: Verify scaffold**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
no tests ran
```

---

### Task 2: Configuration And SQLite Schema

**Files:**
- Create: `app/config.py`
- Create: `app/db.py`
- Create: `tests/test_config_db.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_config_db.py`:

```python
from pathlib import Path

import pandas as pd

from app.config import load_config
from app.db import connect, initialize_database, write_dataframe, read_dataframe


def test_load_config_uses_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.paths.database.endswith("data/worldcup_analysis.sqlite")
    assert cfg.model.max_goals == 8


def test_initialize_database_creates_core_tables(tmp_path):
    db_path = tmp_path / "test.sqlite"
    with connect(db_path) as conn:
        initialize_database(conn)
        tables = pd.read_sql_query(
            "select name from sqlite_master where type='table' order by name",
            conn,
        )["name"].tolist()
    assert "raw_odds_500" in tables
    assert "matches" in tables
    assert "match_predictions" in tables
    assert "recommendations" in tables


def test_dataframe_round_trip(tmp_path):
    db_path = tmp_path / "test.sqlite"
    df = pd.DataFrame([{"match_id": "m1", "home_team": "A", "away_team": "B"}])
    with connect(db_path) as conn:
        initialize_database(conn)
        write_dataframe(conn, "matches", df, if_exists="append")
        loaded = read_dataframe(conn, "select match_id, home_team, away_team from matches")
    assert loaded.to_dict("records") == [{"match_id": "m1", "home_team": "A", "away_team": "B"}]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_config_db.py -q
```

Expected: FAIL with `ModuleNotFoundError` or missing functions.

- [ ] **Step 3: Implement configuration**

Create `app/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


@dataclass(frozen=True)
class PathConfig:
    database: str = "data/worldcup_analysis.sqlite"
    manual_dir: str = "data/manual"
    raw_dir: str = "data/raw"
    processed_dir: str = "data/processed"
    outputs_dir: str = "outputs"
    odds_crawler_path: str = "C:/Users/A/Desktop/分析系统/数据抓取/crawl_500_jczq.py"
    odds_csv_path: str = "C:/Users/A/Desktop/分析系统/数据抓取/jczq_500.csv"


@dataclass(frozen=True)
class ModelConfig:
    market_weight: float = 0.45
    elo_weight: float = 0.25
    recent_form_weight: float = 0.15
    manual_weight: float = 0.15
    max_goals: int = 8
    strong_value_edge: float = 0.07
    lean_value_edge: float = 0.035


@dataclass(frozen=True)
class WeatherConfig:
    enabled: bool = True
    stale_hours: int = 6


@dataclass(frozen=True)
class AppConfig:
    paths: PathConfig
    model: ModelConfig
    weather: WeatherConfig


def _merge_dataclass(cls: type, values: dict[str, Any]) -> Any:
    defaults = cls()
    merged = {field: getattr(defaults, field) for field in defaults.__dataclass_fields__}
    merged.update(values or {})
    return cls(**merged)


def load_config(path: str | Path = "config.toml") -> AppConfig:
    config_path = Path(path)
    raw: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("rb") as file:
            raw = tomllib.load(file)
    return AppConfig(
        paths=_merge_dataclass(PathConfig, raw.get("paths", {})),
        model=_merge_dataclass(ModelConfig, raw.get("model", {})),
        weather=_merge_dataclass(WeatherConfig, raw.get("weather", {})),
    )
```

- [ ] **Step 4: Implement database helpers**

Create `app/db.py`:

```python
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


SCHEMA = """
create table if not exists raw_odds_500 (
    row_id integer primary key autoincrement,
    source_file text not null,
    import_time text not null,
    match_id text,
    match_number text,
    competition text,
    kickoff_time text,
    home_team_raw text,
    away_team_raw text,
    payload_json text not null
);

create table if not exists matches (
    match_id text primary key,
    match_number text,
    competition text,
    group_name text,
    kickoff_time text,
    venue_id text,
    home_team text,
    away_team text,
    status text default 'scheduled'
);

create table if not exists teams (
    team_id text primary key,
    team_name text not null,
    confederation text,
    elo real,
    squad_strength real default 0,
    depth_score real default 0,
    style_notes text default ''
);

create table if not exists venues (
    venue_id text primary key,
    venue_name text not null,
    city text,
    country text,
    latitude real,
    longitude real,
    indoor_flag integer default 0,
    timezone text default ''
);

create table if not exists weather_snapshots (
    snapshot_id integer primary key autoincrement,
    match_id text not null,
    fetched_at text not null,
    temperature_c real,
    humidity_pct real,
    wind_kph real,
    precipitation_probability real,
    weather_code integer,
    source_confidence real default 1
);

create table if not exists manual_adjustments (
    adjustment_id integer primary key autoincrement,
    scope text not null,
    target_id text not null,
    key text not null,
    value text not null,
    source_confidence real default 1
);

create table if not exists model_runs (
    run_id text primary key,
    run_time text not null,
    model_version text not null,
    data_quality_score real not null,
    parameters_json text not null
);

create table if not exists match_predictions (
    run_id text not null,
    match_id text not null,
    home_xg real not null,
    away_xg real not null,
    home_win_prob real not null,
    draw_prob real not null,
    away_win_prob real not null,
    over_25_prob real not null,
    top_scores_json text not null,
    primary key (run_id, match_id)
);

create table if not exists recommendations (
    run_id text not null,
    match_id text not null,
    market text not null,
    label text not null,
    edge real not null,
    confidence real not null,
    risk_level text not null,
    risk_tags_json text not null,
    note text not null,
    primary key (run_id, match_id, market)
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def write_dataframe(
    conn: sqlite3.Connection,
    table: str,
    frame: pd.DataFrame,
    if_exists: str = "append",
) -> None:
    frame.to_sql(table, conn, if_exists=if_exists, index=False)


def read_dataframe(conn: sqlite3.Connection, query: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(query, conn, params=params)
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m pytest tests/test_config_db.py -q
```

Expected: `3 passed`.

---

### Task 3: Team Matching And 500.com Odds Importer

**Files:**
- Create: `app/services/team_matcher.py`
- Create: `app/pipelines/import_odds_500.py`
- Create: `data/manual/team_aliases.csv`
- Create: `tests/fixtures/jczq_500_sample.csv`
- Create: `tests/test_import_odds_500.py`

- [ ] **Step 1: Create sample aliases**

Create `data/manual/team_aliases.csv`:

```csv
alias,canonical
荷兰,Netherlands
乌兹别克,Uzbekistan
法国,France
北爱尔兰,Northern Ireland
西班牙,Spain
秘鲁,Peru
```

- [ ] **Step 2: Create test fixture**

Create `tests/fixtures/jczq_500_sample.csv`:

```csv
场次,赛事,主队,客队,初胜,初平,初负,临胜,临平,临负,初让胜,初让平,初让负,临让胜,临让平,临让负,初亚盘(如:平/半),初亚盘主水,初亚盘客水,临亚盘(如:半球),临亚盘主水,临亚盘客水,初大小球,初大水,初小水,临大小球,临大水,临小水,主近6xG,主近6xGA,客近6xG,客近6xGA,主近5主xG,主近5主xGA,客近5客xG,客近5客xGA,主伤停xG修正,客伤停xG修正,节奏系数,ZIP闷战系数,主xGD评分,客xGD评分,主分,客分,容差
201,国际赛,荷兰,乌兹别克,1.14,5.85,12.5,1.14,5.85,12.5,2.62,3.85,2.05,2.69,3.37,2.17,球半/两球,0.97,0.81,球半/两球,0.86,0.92,3,0.76,0.96,3,0.82,0.9,2.4,0.7,0.8,1.9,2.6,0.6,0.7,2.0,0,0,1,0.95,1.7,-1.1,85,63,0.05
```

- [ ] **Step 3: Write failing tests**

Create `tests/test_import_odds_500.py`:

```python
from pathlib import Path

from app.pipelines.import_odds_500 import import_odds_csv, normalize_odds_frame
from app.services.team_matcher import TeamMatcher


def test_team_matcher_maps_aliases(tmp_path):
    alias_file = tmp_path / "aliases.csv"
    alias_file.write_text("alias,canonical\n荷兰,Netherlands\n", encoding="utf-8")
    matcher = TeamMatcher.from_csv(alias_file)
    assert matcher.canonical("荷兰") == "Netherlands"
    assert matcher.canonical("Unknown FC") == "Unknown FC"


def test_normalize_odds_frame_maps_core_fields():
    frame = import_odds_csv(Path("tests/fixtures/jczq_500_sample.csv"))
    matcher = TeamMatcher.from_csv(Path("data/manual/team_aliases.csv"))
    normalized = normalize_odds_frame(frame, matcher)
    row = normalized.iloc[0].to_dict()
    assert row["match_id"] == "500-201-Netherlands-Uzbekistan"
    assert row["home_team"] == "Netherlands"
    assert row["away_team"] == "Uzbekistan"
    assert row["live_home_odds"] == 1.14
    assert row["live_draw_odds"] == 5.85
    assert row["live_away_odds"] == 12.5
    assert row["total_line"] == 3.0
```

- [ ] **Step 4: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_import_odds_500.py -q
```

Expected: FAIL with missing module/function errors.

- [ ] **Step 5: Implement team matcher**

Create `app/services/team_matcher.py`:

```python
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
        frame = pd.read_csv(alias_path)
        aliases = {
            str(row["alias"]).strip(): str(row["canonical"]).strip()
            for _, row in frame.iterrows()
            if str(row.get("alias", "")).strip()
        }
        return cls(aliases)

    def canonical(self, name: str) -> str:
        cleaned = str(name or "").strip()
        return self.aliases.get(cleaned, cleaned)
```

- [ ] **Step 6: Implement importer**

Create `app/pipelines/import_odds_500.py`:

```python
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from app.services.team_matcher import TeamMatcher


COLUMN_MAP = {
    "场次": "match_number",
    "赛事": "competition",
    "比赛时间": "kickoff_time",
    "主队": "home_team_raw",
    "客队": "away_team_raw",
    "初胜": "open_home_odds",
    "初平": "open_draw_odds",
    "初负": "open_away_odds",
    "临胜": "live_home_odds",
    "临平": "live_draw_odds",
    "临负": "live_away_odds",
    "初让胜": "open_handicap_home_odds",
    "初让平": "open_handicap_draw_odds",
    "初让负": "open_handicap_away_odds",
    "临让胜": "live_handicap_home_odds",
    "临让平": "live_handicap_draw_odds",
    "临让负": "live_handicap_away_odds",
    "临大小球": "total_line",
    "主近6xG": "home_recent_xg",
    "主近6xGA": "home_recent_xga",
    "客近6xG": "away_recent_xg",
    "客近6xGA": "away_recent_xga",
    "主伤停xG修正": "home_injury_xg_adjustment",
    "客伤停xG修正": "away_injury_xg_adjustment",
    "节奏系数": "tempo_factor",
    "ZIP闷战系数": "low_event_factor",
    "主分": "home_score",
    "客分": "away_score",
    "容差": "tolerance",
}


def import_odds_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def _to_number(value) -> float | None:
    if pd.isna(value) or str(value).strip() in {"", "--"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def _match_id(match_number: str, home_team: str, away_team: str) -> str:
    home_slug = re.sub(r"[^A-Za-z0-9]+", "-", home_team).strip("-")
    away_slug = re.sub(r"[^A-Za-z0-9]+", "-", away_team).strip("-")
    return f"500-{match_number}-{home_slug}-{away_slug}"


def normalize_odds_frame(frame: pd.DataFrame, matcher: TeamMatcher) -> pd.DataFrame:
    normalized = frame.rename(columns=COLUMN_MAP).copy()
    for column in COLUMN_MAP.values():
        if column not in normalized:
            normalized[column] = None

    normalized["home_team"] = normalized["home_team_raw"].map(matcher.canonical)
    normalized["away_team"] = normalized["away_team_raw"].map(matcher.canonical)
    normalized["match_number"] = normalized["match_number"].astype(str)
    normalized["match_id"] = normalized.apply(
        lambda row: _match_id(row["match_number"], row["home_team"], row["away_team"]),
        axis=1,
    )

    numeric_columns = [
        "open_home_odds",
        "open_draw_odds",
        "open_away_odds",
        "live_home_odds",
        "live_draw_odds",
        "live_away_odds",
        "open_handicap_home_odds",
        "open_handicap_draw_odds",
        "open_handicap_away_odds",
        "live_handicap_home_odds",
        "live_handicap_draw_odds",
        "live_handicap_away_odds",
        "total_line",
        "home_recent_xg",
        "home_recent_xga",
        "away_recent_xg",
        "away_recent_xga",
        "home_injury_xg_adjustment",
        "away_injury_xg_adjustment",
        "tempo_factor",
        "low_event_factor",
        "home_score",
        "away_score",
        "tolerance",
    ]
    for column in numeric_columns:
        normalized[column] = normalized[column].map(_to_number)

    return normalized
```

- [ ] **Step 7: Run tests**

Run:

```powershell
python -m pytest tests/test_import_odds_500.py -q
```

Expected: `2 passed`.

---

### Task 4: Market, Elo, XG, And Poisson Model Core

**Files:**
- Create: `app/models/market.py`
- Create: `app/models/elo.py`
- Create: `app/models/xg.py`
- Create: `app/models/poisson.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_models.py`:

```python
from app.models.elo import elo_expected_score, elo_to_goal_delta
from app.models.market import implied_probabilities, remove_margin
from app.models.poisson import poisson_market
from app.models.xg import build_expected_goals


def test_market_probabilities_remove_margin():
    raw = implied_probabilities(2.0, 3.5, 4.0)
    fair = remove_margin(raw)
    assert round(sum(fair.values()), 6) == 1.0
    assert fair["home"] > fair["away"]


def test_elo_helpers_are_directional():
    assert elo_expected_score(1800, 1600) > 0.5
    assert elo_to_goal_delta(1800, 1600) > 0


def test_build_expected_goals_uses_recent_and_adjustments():
    result = build_expected_goals(
        market_total=2.8,
        elo_goal_delta=0.4,
        home_recent_xg=1.8,
        away_recent_xg=1.1,
        home_injury_adjustment=-0.1,
        away_injury_adjustment=0,
        tempo_factor=1.0,
        low_event_factor=0.95,
    )
    assert result.home_xg > result.away_xg
    assert 2.0 < result.total_xg < 3.2


def test_poisson_market_probabilities_sum_to_one():
    result = poisson_market(1.7, 0.9, max_goals=8)
    total = result.home_win_prob + result.draw_prob + result.away_win_prob
    assert abs(total - 1.0) < 0.01
    assert result.home_win_prob > result.away_win_prob
    assert result.top_scores[0].probability > 0
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_models.py -q
```

Expected: FAIL with missing modules.

- [ ] **Step 3: Implement market model**

Create `app/models/market.py`:

```python
from __future__ import annotations


def implied_probabilities(home_odds: float, draw_odds: float, away_odds: float) -> dict[str, float]:
    return {
        "home": 1.0 / float(home_odds),
        "draw": 1.0 / float(draw_odds),
        "away": 1.0 / float(away_odds),
    }


def remove_margin(probabilities: dict[str, float]) -> dict[str, float]:
    total = sum(probabilities.values())
    if total <= 0:
        raise ValueError("probability total must be positive")
    return {key: value / total for key, value in probabilities.items()}


def market_edge(model_prob: float, fair_market_prob: float) -> float:
    return float(model_prob) - float(fair_market_prob)
```

- [ ] **Step 4: Implement Elo helpers**

Create `app/models/elo.py`:

```python
from __future__ import annotations


def elo_expected_score(team_elo: float, opponent_elo: float) -> float:
    return 1.0 / (1.0 + 10 ** ((opponent_elo - team_elo) / 400.0))


def elo_to_goal_delta(team_elo: float, opponent_elo: float) -> float:
    return max(min((team_elo - opponent_elo) / 500.0, 1.2), -1.2)
```

- [ ] **Step 5: Implement xG builder**

Create `app/models/xg.py`:

```python
from __future__ import annotations

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
    return ExpectedGoals(home_xg=home, away_xg=away, total_xg=home + away, tempo_factor=tempo, low_event_factor=low_event)
```

- [ ] **Step 6: Implement Poisson model**

Create `app/models/poisson.py`:

```python
from __future__ import annotations

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
    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    over_25 = 0.0
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
            if home_goals + away_goals > 2.5:
                over_25 += prob

    total = home_win + draw + away_win
    if total > 0:
        home_win, draw, away_win, over_25 = [value / total for value in (home_win, draw, away_win, over_25)]
    top_scores = sorted(scores, key=lambda item: item.probability, reverse=True)[:8]
    return PoissonMarket(home_win, draw, away_win, over_25, top_scores)
```

- [ ] **Step 7: Run tests**

Run:

```powershell
python -m pytest tests/test_models.py -q
```

Expected: `4 passed`.

---

### Task 5: Manual Data, Weather, Elo, And Data Quality

**Files:**
- Create: `data/manual/venues.csv`
- Create: `data/manual/team_profiles.csv`
- Create: `data/manual/squad_strength.csv`
- Create: `data/manual/injuries.csv`
- Create: `data/manual/coach_tactics.csv`
- Create: `app/pipelines/import_manual.py`
- Create: `app/pipelines/fetch_weather.py`
- Create: `app/pipelines/fetch_elo.py`
- Create: `app/services/data_quality.py`
- Create: `tests/test_external_adapters.py`

- [ ] **Step 1: Create minimal manual CSVs**

Create `data/manual/venues.csv`:

```csv
venue_id,venue_name,city,country,latitude,longitude,indoor_flag,timezone
metlife,MetLife Stadium,East Rutherford,USA,40.8135,-74.0745,0,America/New_York
azteca,Estadio Azteca,Mexico City,Mexico,19.3029,-99.1505,0,America/Mexico_City
```

Create `data/manual/team_profiles.csv`:

```csv
team_id,team_name,confederation,elo,style_notes
netherlands,Netherlands,UEFA,1900,High defensive line and strong wing progression
uzbekistan,Uzbekistan,AFC,1650,Compact block with transition focus
```

Create `data/manual/squad_strength.csv`:

```csv
team_id,squad_strength,depth_score
netherlands,86,82
uzbekistan,68,62
```

Create `data/manual/injuries.csv`:

```csv
match_id,team_id,xg_adjustment,note,source_confidence
500-201-Netherlands-Uzbekistan,netherlands,0,No manual injury hit,0.5
500-201-Netherlands-Uzbekistan,uzbekistan,0,No manual injury hit,0.5
```

Create `data/manual/coach_tactics.csv`:

```csv
team_id,coach_name,tempo_modifier,low_event_modifier,style_tag,note
netherlands,Unknown,1.03,1.00,possession,Manual seed
uzbekistan,Unknown,0.97,1.03,compact,Manual seed
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_external_adapters.py`:

```python
from pathlib import Path

import pandas as pd

from app.pipelines.fetch_elo import elo_from_profiles
from app.pipelines.fetch_weather import parse_open_meteo_response
from app.pipelines.import_manual import load_manual_table
from app.services.data_quality import data_quality_score


def test_load_manual_table_reads_csv():
    frame = load_manual_table(Path("data/manual/team_profiles.csv"))
    assert "team_name" in frame.columns
    assert len(frame) >= 1


def test_parse_open_meteo_response_extracts_fields():
    payload = {
        "current": {
            "time": "2026-06-11T12:00",
            "temperature_2m": 22.5,
            "relative_humidity_2m": 60,
            "wind_speed_10m": 12.0,
            "precipitation": 0.1,
            "weather_code": 3,
        }
    }
    row = parse_open_meteo_response("m1", payload)
    assert row["match_id"] == "m1"
    assert row["temperature_c"] == 22.5
    assert row["source_confidence"] == 1.0


def test_elo_from_profiles_returns_mapping():
    profiles = pd.DataFrame([{"team_id": "netherlands", "elo": 1900}])
    assert elo_from_profiles(profiles)["netherlands"] == 1900


def test_data_quality_score_penalizes_missing_lineups():
    score, warnings = data_quality_score({"odds": True, "weather": False, "injuries": False})
    assert score < 1.0
    assert "weather_missing" in warnings
    assert "injuries_missing" in warnings
```

- [ ] **Step 3: Implement manual importer**

Create `app/pipelines/import_manual.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_manual_table(path: str | Path) -> pd.DataFrame:
    table_path = Path(path)
    if not table_path.exists():
        return pd.DataFrame()
    return pd.read_csv(table_path, encoding="utf-8-sig")
```

- [ ] **Step 4: Implement weather parser**

Create `app/pipelines/fetch_weather.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_open_meteo(latitude: float, longitude: float) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code",
    }
    response = requests.get(OPEN_METEO_URL, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def parse_open_meteo_response(match_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    current = payload.get("current", {})
    return {
        "match_id": match_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "temperature_c": current.get("temperature_2m"),
        "humidity_pct": current.get("relative_humidity_2m"),
        "wind_kph": current.get("wind_speed_10m"),
        "precipitation_probability": current.get("precipitation"),
        "weather_code": current.get("weather_code"),
        "source_confidence": 1.0 if current else 0.0,
    }
```

- [ ] **Step 5: Implement Elo fallback**

Create `app/pipelines/fetch_elo.py`:

```python
from __future__ import annotations

import pandas as pd


def elo_from_profiles(profiles: pd.DataFrame) -> dict[str, float]:
    if profiles.empty or "team_id" not in profiles or "elo" not in profiles:
        return {}
    return {
        str(row["team_id"]): float(row["elo"])
        for _, row in profiles.iterrows()
        if pd.notna(row.get("elo"))
    }
```

- [ ] **Step 6: Implement data quality**

Create `app/services/data_quality.py`:

```python
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
```

- [ ] **Step 7: Run tests**

Run:

```powershell
python -m pytest tests/test_external_adapters.py -q
```

Expected: `4 passed`.

---

### Task 6: Recommendation Scoring

**Files:**
- Create: `app/models/scoring.py`
- Create: `app/services/recommendations.py`
- Create: `tests/test_recommendations.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_recommendations.py`:

```python
from app.services.recommendations import classify_recommendation, risk_level


def test_classify_strong_value_when_edge_and_quality_are_high():
    rec = classify_recommendation(edge=0.09, data_quality=0.9, risk_tags=[])
    assert rec.label == "Strong value"
    assert rec.confidence > 0.75


def test_classify_avoid_when_data_quality_is_low():
    rec = classify_recommendation(edge=0.1, data_quality=0.35, risk_tags=["injuries_missing"])
    assert rec.label == "Avoid"
    assert rec.risk_level == "high"


def test_risk_level_uses_tag_count():
    assert risk_level([]) == "low"
    assert risk_level(["weather_missing", "market_conflict"]) == "medium"
    assert risk_level(["a", "b", "c"]) == "high"
```

- [ ] **Step 2: Implement recommendation service**

Create `app/services/recommendations.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Recommendation:
    label: str
    edge: float
    confidence: float
    risk_level: str
    risk_tags: list[str]
    note: str


def risk_level(tags: list[str]) -> str:
    if len(tags) >= 3:
        return "high"
    if len(tags) >= 1:
        return "medium"
    return "low"


def classify_recommendation(edge: float, data_quality: float, risk_tags: list[str]) -> Recommendation:
    level = risk_level(risk_tags)
    confidence = max(min(data_quality - len(risk_tags) * 0.08 + max(edge, 0), 1.0), 0.0)
    if data_quality < 0.45 or level == "high":
        label = "Avoid"
        note = "Data quality or risk conditions are too weak for a confident position."
    elif edge >= 0.07 and confidence >= 0.75:
        label = "Strong value"
        note = "Model edge is meaningful and data confidence is acceptable."
    elif edge >= 0.035:
        label = "Lean value"
        note = "Model edge exists, but risk or confidence limits stake conviction."
    else:
        label = "No bet"
        note = "No clear model-market edge."
    return Recommendation(label, edge, confidence, level, risk_tags, note)
```

- [ ] **Step 3: Add scoring re-export**

Create `app/models/scoring.py`:

```python
from __future__ import annotations

from app.services.recommendations import Recommendation, classify_recommendation

__all__ = ["Recommendation", "classify_recommendation"]
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/test_recommendations.py -q
```

Expected: `3 passed`.

---

### Task 7: Daily Pipeline And Report Export

**Files:**
- Create: `app/pipelines/run_daily.py`
- Create: `tests/test_run_daily.py`

- [ ] **Step 1: Write failing integration test**

Create `tests/test_run_daily.py`:

```python
from pathlib import Path

from app.pipelines.run_daily import run_daily


def test_run_daily_creates_predictions_and_reports(tmp_path):
    output = run_daily(
        odds_csv=Path("tests/fixtures/jczq_500_sample.csv"),
        alias_csv=Path("data/manual/team_aliases.csv"),
        database=tmp_path / "analysis.sqlite",
        outputs_dir=tmp_path / "outputs",
        date_label="2026-06-11",
    )
    assert output.database.exists()
    assert output.csv_report.exists()
    assert output.xlsx_report.exists()
    assert output.match_count == 1
```

- [ ] **Step 2: Implement daily pipeline**

Create `app/pipelines/run_daily.py`:

```python
from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.config import load_config
from app.db import connect, initialize_database, write_dataframe
from app.models.elo import elo_to_goal_delta
from app.models.market import implied_probabilities, market_edge, remove_margin
from app.models.poisson import poisson_market
from app.models.xg import build_expected_goals
from app.pipelines.import_odds_500 import import_odds_csv, normalize_odds_frame
from app.services.data_quality import data_quality_score
from app.services.recommendations import classify_recommendation
from app.services.team_matcher import TeamMatcher


@dataclass(frozen=True)
class DailyRunOutput:
    database: Path
    csv_report: Path
    xlsx_report: Path
    match_count: int


def _score_row(row: pd.Series, run_id: str, date_label: str) -> tuple[dict, dict]:
    market = remove_margin(
        implied_probabilities(row["live_home_odds"], row["live_draw_odds"], row["live_away_odds"])
    )
    elo_delta = elo_to_goal_delta(float(row.get("home_score") or 75), float(row.get("away_score") or 75))
    xg = build_expected_goals(
        market_total=row.get("total_line"),
        elo_goal_delta=elo_delta,
        home_recent_xg=row.get("home_recent_xg"),
        away_recent_xg=row.get("away_recent_xg"),
        home_injury_adjustment=row.get("home_injury_xg_adjustment"),
        away_injury_adjustment=row.get("away_injury_xg_adjustment"),
        tempo_factor=row.get("tempo_factor"),
        low_event_factor=row.get("low_event_factor"),
    )
    poisson = poisson_market(xg.home_xg, xg.away_xg)
    flags = {"odds": True, "weather": False, "injuries": pd.notna(row.get("home_injury_xg_adjustment"))}
    quality, warnings = data_quality_score(flags)
    edge = market_edge(poisson.home_win_prob, market["home"])
    recommendation = classify_recommendation(edge=edge, data_quality=quality, risk_tags=warnings)
    prediction = {
        "run_id": run_id,
        "match_id": row["match_id"],
        "home_xg": xg.home_xg,
        "away_xg": xg.away_xg,
        "home_win_prob": poisson.home_win_prob,
        "draw_prob": poisson.draw_prob,
        "away_win_prob": poisson.away_win_prob,
        "over_25_prob": poisson.over_25_prob,
        "top_scores_json": json.dumps([score.__dict__ for score in poisson.top_scores], ensure_ascii=False),
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
        "match": f"{row['home_team']} vs {row['away_team']}",
        "home_win_prob": poisson.home_win_prob,
        "market_home_prob": market["home"],
    }
    return prediction, rec


def run_daily(
    odds_csv: Path,
    alias_csv: Path,
    database: Path,
    outputs_dir: Path,
    date_label: str,
) -> DailyRunOutput:
    matcher = TeamMatcher.from_csv(alias_csv)
    raw = import_odds_csv(odds_csv)
    normalized = normalize_odds_frame(raw, matcher)
    run_id = uuid.uuid4().hex
    run_time = datetime.now(timezone.utc).isoformat()
    outputs_dir.mkdir(parents=True, exist_ok=True)

    predictions = []
    recommendations = []
    for _, row in normalized.iterrows():
        if pd.isna(row.get("live_home_odds")) or pd.isna(row.get("live_draw_odds")) or pd.isna(row.get("live_away_odds")):
            continue
        prediction, recommendation = _score_row(row, run_id, date_label)
        predictions.append(prediction)
        recommendations.append(recommendation)

    report = pd.DataFrame(recommendations)
    csv_report = outputs_dir / f"daily_screening_{date_label}.csv"
    xlsx_report = outputs_dir / f"daily_screening_{date_label}.xlsx"
    report.to_csv(csv_report, index=False, encoding="utf-8-sig")
    report.to_excel(xlsx_report, index=False)

    with connect(database) as conn:
        initialize_database(conn)
        write_dataframe(conn, "model_runs", pd.DataFrame([{
            "run_id": run_id,
            "run_time": run_time,
            "model_version": "v0.1",
            "data_quality_score": 0.75,
            "parameters_json": "{}",
        }]))
        write_dataframe(conn, "match_predictions", pd.DataFrame(predictions))
        write_dataframe(conn, "recommendations", report.drop(columns=["date_label", "match", "home_win_prob", "market_home_prob"]))

    return DailyRunOutput(database, csv_report, xlsx_report, len(report))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().date().isoformat())
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    output = run_daily(
        odds_csv=Path(cfg.paths.odds_csv_path),
        alias_csv=Path(cfg.paths.manual_dir) / "team_aliases.csv",
        database=Path(cfg.paths.database),
        outputs_dir=Path(cfg.paths.outputs_dir),
        date_label=args.date,
    )
    print(f"done: {output.match_count} matches -> {output.csv_report}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run integration test**

Run:

```powershell
python -m pytest tests/test_run_daily.py -q
```

Expected: `1 passed`.

---

### Task 8: Streamlit Dashboard

**Files:**
- Create: `app/dashboard.py`
- Create: `tests/test_dashboard_smoke.py`

- [ ] **Step 1: Write smoke test**

Create `tests/test_dashboard_smoke.py`:

```python
from pathlib import Path


def test_dashboard_file_exists_and_uses_streamlit():
    path = Path("app/dashboard.py")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "import streamlit as st" in text
    assert "Daily Screening" in text
```

- [ ] **Step 2: Implement dashboard**

Create `app/dashboard.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app.config import load_config
from app.db import connect, initialize_database, read_dataframe


st.set_page_config(page_title="World Cup Analysis", layout="wide")


def load_recommendations(database: Path) -> pd.DataFrame:
    with connect(database) as conn:
        initialize_database(conn)
        return read_dataframe(
            conn,
            """
            select
                r.run_id,
                r.match_id,
                r.market,
                r.label,
                r.edge,
                r.confidence,
                r.risk_level,
                r.risk_tags_json,
                r.note,
                p.home_xg,
                p.away_xg,
                p.home_win_prob,
                p.draw_prob,
                p.away_win_prob,
                p.over_25_prob,
                p.top_scores_json
            from recommendations r
            join match_predictions p
              on p.run_id = r.run_id and p.match_id = r.match_id
            order by r.confidence desc, r.edge desc
            """,
        )


cfg = load_config("config.toml")
st.title("World Cup Analysis")
st.caption("Local model output for football betting analysis. Use as decision support, not a guarantee.")

database = Path(cfg.paths.database)
data = load_recommendations(database)

if data.empty:
    st.info("No model run found. Run `python -m app.pipelines.run_daily --date YYYY-MM-DD` first.")
    st.stop()

st.header("Daily Screening")
left, middle, right = st.columns(3)
with left:
    labels = sorted(data["label"].dropna().unique().tolist())
    selected_labels = st.multiselect("Recommendation", labels, default=labels)
with middle:
    risks = sorted(data["risk_level"].dropna().unique().tolist())
    selected_risks = st.multiselect("Risk", risks, default=risks)
with right:
    min_edge = st.slider("Minimum edge", min_value=-0.20, max_value=0.20, value=-0.20, step=0.005)

filtered = data[
    data["label"].isin(selected_labels)
    & data["risk_level"].isin(selected_risks)
    & (data["edge"] >= min_edge)
].copy()

st.dataframe(
    filtered[
        [
            "match_id",
            "market",
            "label",
            "edge",
            "confidence",
            "risk_level",
            "home_xg",
            "away_xg",
            "home_win_prob",
            "draw_prob",
            "away_win_prob",
            "over_25_prob",
            "note",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

st.header("Single Match")
match_id = st.selectbox("Match", filtered["match_id"].tolist())
match = filtered[filtered["match_id"] == match_id].iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("Home xG", f"{match.home_xg:.2f}")
col2.metric("Away xG", f"{match.away_xg:.2f}")
col3.metric("Edge", f"{match.edge:.1%}")

st.subheader("Probabilities")
st.bar_chart(
    pd.DataFrame(
        {
            "probability": {
                "Home": match.home_win_prob,
                "Draw": match.draw_prob,
                "Away": match.away_win_prob,
                "Over 2.5": match.over_25_prob,
            }
        }
    )
)

st.subheader("Risk And Note")
st.write(match.risk_tags_json)
st.write(match.note)
```

- [ ] **Step 3: Run smoke test**

Run:

```powershell
python -m pytest tests/test_dashboard_smoke.py -q
```

Expected: `1 passed`.

- [ ] **Step 4: Manual dashboard verification**

Run:

```powershell
python -m app.pipelines.run_daily --date 2026-06-11 --config config.example.toml
streamlit run app/dashboard.py
```

Expected:

- Browser shows "World Cup Analysis".
- Daily Screening table has at least one row when sample or real odds data is present.
- Single Match section updates when selecting a match.

---

### Task 9: Full Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run full test suite**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
18 passed
```

- [ ] **Step 2: Run sample daily pipeline**

Run:

```powershell
python -m app.pipelines.run_daily --date 2026-06-11 --config config.example.toml
```

Expected:

```text
done: <N> matches -> outputs\daily_screening_2026-06-11.csv
```

- [ ] **Step 3: Update README with actual first-run commands**

Append to `README.md`:

```markdown
## First Local Verification

```powershell
python -m pytest -q
python -m app.pipelines.run_daily --date 2026-06-11 --config config.example.toml
streamlit run app/dashboard.py
```

The dashboard reads `data/worldcup_analysis.sqlite` and report files are written to `outputs/`.
```

- [ ] **Step 4: Final verification**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

---

## Self-Review Notes

- Spec coverage: odds import, free/manual data, SQLite, Elo, Poisson, xG, recommendation labels, Streamlit dashboard, exports, and tests are covered.
- Known first-version limitation: World Cup official teams/groups are represented as manual seed files until a stable free machine-readable source is confirmed.
- Known first-version limitation: player xG, injuries, and predicted lineups use manual adjustments first; paid/API data sources can be plugged in through config later.
- Execution should use TDD. Each task starts with failing tests except the initial scaffold task.

