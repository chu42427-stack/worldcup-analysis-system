from __future__ import annotations

from dataclasses import dataclass, fields
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
    odds_crawler_path: str = "C:/Users/A/Desktop/\u5206\u6790\u7cfb\u7edf/\u6570\u636e\u6293\u53d6/crawl_500_jczq.py"
    odds_csv_path: str = "C:/Users/A/Desktop/\u5206\u6790\u7cfb\u7edf/\u6570\u636e\u6293\u53d6/jczq_500.csv"


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
    merged = {field.name: getattr(defaults, field.name) for field in fields(defaults)}
    merged.update(values or {})
    return cls(**merged)


def load_config(path: str | Path = "config.toml") -> AppConfig:
    config_path = Path(path)
    raw: dict[str, Any] = {}
    if config_path.exists():
        raw = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    return AppConfig(
        paths=_merge_dataclass(PathConfig, raw.get("paths", {})),
        model=_merge_dataclass(ModelConfig, raw.get("model", {})),
        weather=_merge_dataclass(WeatherConfig, raw.get("weather", {})),
    )
