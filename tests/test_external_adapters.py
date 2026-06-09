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


def test_elo_from_profiles_skips_invalid_elo_values():
    profiles = pd.DataFrame(
        [
            {"team_id": "netherlands", "elo": 1900},
            {"team_id": "bad_value", "elo": "bad"},
            {"team_id": "not_available", "elo": "N/A"},
            {"team_id": "empty", "elo": ""},
            {"team_id": "nan", "elo": float("nan")},
            {"team_id": "argentina", "elo": "1925.5"},
        ]
    )

    assert elo_from_profiles(profiles) == {
        "netherlands": 1900.0,
        "argentina": 1925.5,
    }


def test_elo_from_profiles_skips_missing_team_ids():
    profiles = pd.DataFrame(
        [
            {"team_id": "netherlands", "elo": 1900},
            {"team_id": None, "elo": 1800},
            {"team_id": "", "elo": 1810},
            {"team_id": "   ", "elo": 1820},
            {"team_id": float("nan"), "elo": 1830},
            {"team_id": "argentina", "elo": "1925.5"},
        ]
    )

    assert elo_from_profiles(profiles) == {
        "netherlands": 1900.0,
        "argentina": 1925.5,
    }


def test_parse_open_meteo_response_handles_current_none():
    row = parse_open_meteo_response("m1", {"current": None})

    assert row["match_id"] == "m1"
    assert row["temperature_c"] is None
    assert row["humidity_pct"] is None
    assert row["wind_kph"] is None
    assert row["precipitation_probability"] is None
    assert row["weather_code"] is None
    assert row["source_confidence"] == 0.0


def test_parse_open_meteo_response_handles_missing_current():
    row = parse_open_meteo_response("m1", {})

    assert row["match_id"] == "m1"
    assert row["temperature_c"] is None
    assert row["humidity_pct"] is None
    assert row["wind_kph"] is None
    assert row["precipitation_probability"] is None
    assert row["weather_code"] is None
    assert row["source_confidence"] == 0.0


def test_parse_open_meteo_response_handles_current_list():
    row = parse_open_meteo_response("m1", {"current": []})

    assert row["match_id"] == "m1"
    assert row["temperature_c"] is None
    assert row["humidity_pct"] is None
    assert row["wind_kph"] is None
    assert row["precipitation_probability"] is None
    assert row["weather_code"] is None
    assert row["source_confidence"] == 0.0


def test_parse_open_meteo_response_without_weather_fields_has_no_confidence():
    row = parse_open_meteo_response("m1", {"current": {"time": "2026-06-11T12:00"}})

    assert row["temperature_c"] is None
    assert row["humidity_pct"] is None
    assert row["wind_kph"] is None
    assert row["precipitation_probability"] is None
    assert row["weather_code"] is None
    assert row["source_confidence"] == 0.0


def test_data_quality_score_penalizes_missing_sources():
    score, warnings = data_quality_score({"odds": True, "weather": False, "injuries": False})
    assert score < 1.0
    assert "weather_missing" in warnings
    assert "injuries_missing" in warnings
