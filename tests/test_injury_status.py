from pathlib import Path

from app.services.injuries import injury_status_for_match, load_injury_records


def test_injury_status_uses_manual_csv_records(tmp_path):
    injuries_csv = tmp_path / "injuries.csv"
    injuries_csv.write_text(
        "match_id,team_name,player_name,position,status,xg_adjustment,note,source_url,source_confidence,updated_at\n"
        "m1,荷兰,Player A,FW,out,-0.15,确认缺阵,https://example.com,0.9,2026-06-09\n"
        "m1,日本,,,,0,伤停数据待确认,,0.2,2026-06-09\n"
        "m2,法国,,,,0,伤停数据待确认,,0.2,2026-06-09\n",
        encoding="utf-8",
    )

    records = load_injury_records(injuries_csv)

    assert injury_status_for_match("m1", records) == "已维护"
    assert injury_status_for_match("m2", records) == "待确认"
    assert injury_status_for_match("missing", records) == "缺失"

