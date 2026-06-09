import importlib
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

from app.db import connect, initialize_database


def _import_dashboard_with_fake_streamlit(monkeypatch):
    def fail_stop():
        raise AssertionError("st.stop() should not run while importing app.dashboard")

    fake_streamlit = SimpleNamespace(
        set_page_config=lambda *args, **kwargs: None,
        title=lambda *args, **kwargs: None,
        caption=lambda *args, **kwargs: None,
        info=lambda *args, **kwargs: None,
        stop=fail_stop,
    )
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    sys.modules.pop("app.dashboard", None)
    return importlib.import_module("app.dashboard")


def test_dashboard_file_exists_and_uses_streamlit():
    path = Path("app/dashboard.py")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "import streamlit as st" in text
    assert "世界杯竞彩分析系统" in text
    assert "每日筛选" in text
    assert "推荐结论" in text
    assert "def main()" in text
    assert 'if __name__ == "__main__"' in text


def test_dashboard_translates_display_values(monkeypatch):
    dashboard = _import_dashboard_with_fake_streamlit(monkeypatch)

    assert dashboard._translate_label("Strong value") == "强价值"
    assert dashboard._translate_label("Lean value") == "轻仓观察"
    assert dashboard._translate_label("No bet") == "不下注"
    assert dashboard._translate_label("Avoid") == "回避"
    assert dashboard._translate_risk("low") == "低"
    assert dashboard._translate_risk("medium") == "中"
    assert dashboard._translate_risk("high") == "高"


def test_load_recommendations_import_does_not_run_streamlit_ui(monkeypatch):
    dashboard = _import_dashboard_with_fake_streamlit(monkeypatch)

    assert callable(dashboard.load_recommendations)


def test_dashboard_imports_when_started_from_app_directory():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy; runpy.run_path('dashboard.py', run_name='dashboard_import_check')",
        ],
        cwd=Path("app"),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_load_recommendations_returns_empty_for_database_with_no_runs(tmp_path, monkeypatch):
    dashboard = _import_dashboard_with_fake_streamlit(monkeypatch)
    database = tmp_path / "empty.sqlite"

    result = dashboard.load_recommendations(database)

    assert result.empty


def test_load_recommendations_returns_only_latest_model_run(tmp_path, monkeypatch):
    dashboard = _import_dashboard_with_fake_streamlit(monkeypatch)
    database = tmp_path / "runs.sqlite"
    with connect(database) as conn:
        initialize_database(conn)
        conn.executemany(
            """
            insert into model_runs (
                run_id,
                run_time,
                model_version,
                data_quality_score,
                parameters_json
            )
            values (?, ?, ?, ?, ?)
            """,
            [
                ("old-run", "2026-06-08T10:00:00", "test", 0.9, "{}"),
                ("latest-run", "2026-06-09T10:00:00", "test", 0.9, "{}"),
            ],
        )
        conn.executemany(
            """
            insert into match_predictions (
                run_id,
                match_id,
                home_xg,
                away_xg,
                home_win_prob,
                draw_prob,
                away_win_prob,
                over_25_prob,
                top_scores_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("old-run", "old-match", 1.1, 0.9, 0.45, 0.30, 0.25, 0.48, "[]"),
                ("latest-run", "latest-match", 1.8, 0.7, 0.62, 0.24, 0.14, 0.57, "[]"),
            ],
        )
        conn.executemany(
            """
            insert into recommendations (
                run_id,
                match_id,
                market,
                label,
                edge,
                confidence,
                risk_level,
                risk_tags_json,
                note
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("old-run", "old-match", "1x2", "Avoid", -0.01, 0.40, "high", "[]", "old"),
                ("latest-run", "latest-match", "1x2", "Lean", 0.05, 0.70, "low", "[]", "latest"),
            ],
        )
        conn.execute(
            """
            insert into matches (
                match_id,
                match_number,
                competition,
                home_team,
                away_team
            )
            values (?, ?, ?, ?, ?)
            """,
            ("latest-match", "1", "friendly", "Netherlands", "Uzbekistan"),
        )
        conn.commit()

    result = dashboard.load_recommendations(database)

    assert result["run_id"].tolist() == ["latest-run"]
    assert result["match_id"].tolist() == ["latest-match"]
    assert result["match_name"].tolist() == ["Netherlands vs Uzbekistan"]
