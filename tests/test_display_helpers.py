from pathlib import Path

from app.services.display import format_match_label, format_team_label, load_team_display


def test_load_team_display_and_format_labels(tmp_path):
    display_csv = tmp_path / "team_display.csv"
    display_csv.write_text(
        "team_name,display_name,country_code,flag_emoji\n"
        "荷兰,荷兰,NL,🇳🇱\n"
        "日本,日本,JP,🇯🇵\n",
        encoding="utf-8",
    )

    display = load_team_display(display_csv)

    assert format_team_label("荷兰", display) == "🇳🇱 荷兰"
    assert format_team_label("Unknown", display) == "Unknown"
    assert format_match_label("荷兰", "日本", display) == "🇳🇱 荷兰 vs 🇯🇵 日本"

