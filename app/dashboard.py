from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_config
from app.db import connect, initialize_database, read_dataframe

LABEL_TRANSLATIONS = {
    "Strong value": "强价值",
    "Lean value": "轻仓观察",
    "No bet": "不下注",
    "Avoid": "回避",
    "Lean": "轻仓观察",
}

RISK_TRANSLATIONS = {
    "low": "低",
    "medium": "中",
    "high": "高",
}

MARKET_TRANSLATIONS = {
    "home_win": "主胜",
    "draw": "平局",
    "away_win": "客胜",
    "over_25": "大 2.5 球",
    "under_25": "小 2.5 球",
    "1x2": "胜平负",
}

RISK_TAG_TRANSLATIONS = {
    "weather_missing": "天气数据缺失",
    "injuries_missing": "伤停数据缺失",
    "squad_missing": "阵容数据缺失",
    "market_conflict": "市场分歧较大",
    "low_data_quality": "数据质量偏低",
}

NOTE_TRANSLATIONS = {
    "Data quality or risk conditions are too weak for a confident position.": "数据质量或风险条件不足，不适合建立信心仓位。",
    "Model edge is meaningful and data confidence is acceptable.": "模型优势较明显，数据可信度可以接受。",
    "Model edge exists, but risk or confidence limits stake conviction.": "模型存在优势，但风险或置信度限制下注强度。",
    "No clear model-market edge.": "模型与市场之间没有明确优势。",
}


def _project_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _translate_label(value: str) -> str:
    return LABEL_TRANSLATIONS.get(value, value)


def _translate_risk(value: str) -> str:
    return RISK_TRANSLATIONS.get(value, value)


def _translate_market(value: str) -> str:
    return MARKET_TRANSLATIONS.get(value, value)


def _translate_note(value: str) -> str:
    return NOTE_TRANSLATIONS.get(value, value)


def _translate_risk_tag(value: str) -> str:
    return RISK_TAG_TRANSLATIONS.get(value, value)


def load_recommendations(database: Path) -> pd.DataFrame:
    with connect(database) as conn:
        initialize_database(conn)
        return read_dataframe(
            conn,
            """
            select
                r.run_id,
                r.match_id,
                case
                    when mt.home_team is not null and mt.away_team is not null
                    then mt.home_team || ' vs ' || mt.away_team
                    else r.match_id
                end as match_name,
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
            join model_runs m
              on m.run_id = r.run_id
            join match_predictions p
              on p.run_id = r.run_id and p.match_id = r.match_id
            left join matches mt
              on mt.match_id = r.match_id
            where m.run_time = (select max(run_time) from model_runs)
            order by r.confidence desc, r.edge desc
            """,
        )


def _display_risk_tags(value: str) -> object:
    try:
        tags = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value
    if isinstance(tags, list):
        return [_translate_risk_tag(tag) for tag in tags]
    return tags


def main():
    st.set_page_config(page_title="世界杯竞彩分析系统", layout="wide")

    cfg = load_config(PROJECT_ROOT / "config.toml")
    st.title("世界杯竞彩分析系统")
    st.caption("本地模型输出，用于足球竞彩分析和赛前决策辅助，不代表确定收益。")

    database = _project_path(cfg.paths.database)
    data = load_recommendations(database)

    if data.empty:
        st.info("还没有模型结果。请先运行：`python -m app.pipelines.run_daily --date YYYY-MM-DD`。")
        st.stop()

    data = data.assign(
        market_display=data["market"].map(_translate_market),
        label_display=data["label"].map(_translate_label),
        risk_level_display=data["risk_level"].map(_translate_risk),
        note_display=data["note"].map(_translate_note),
    )

    st.header("每日筛选")
    left, middle, right = st.columns(3)
    with left:
        labels = sorted(data["label"].dropna().unique().tolist())
        selected_labels = st.multiselect("推荐结论", labels, default=labels, format_func=_translate_label)
    with middle:
        risks = sorted(data["risk_level"].dropna().unique().tolist())
        selected_risks = st.multiselect("风险等级", risks, default=risks, format_func=_translate_risk)
    with right:
        min_edge = st.slider("最低模型优势", min_value=-0.20, max_value=0.20, value=-0.20, step=0.005)

    filtered = data[
        data["label"].isin(selected_labels)
        & data["risk_level"].isin(selected_risks)
        & (data["edge"] >= min_edge)
    ].copy()

    if filtered.empty:
        st.warning("没有符合当前筛选条件的推荐。")
        st.stop()

    st.dataframe(
        filtered[
            [
                "match_name",
                "market_display",
                "label_display",
                "edge",
                "confidence",
                "risk_level_display",
                "home_xg",
                "away_xg",
                "home_win_prob",
                "draw_prob",
                "away_win_prob",
                "over_25_prob",
                "note_display",
            ]
        ].rename(
            columns={
                "match_name": "比赛",
                "market_display": "市场",
                "label_display": "推荐结论",
                "edge": "模型优势",
                "confidence": "置信度",
                "risk_level_display": "风险等级",
                "home_xg": "主队 xG",
                "away_xg": "客队 xG",
                "home_win_prob": "主胜概率",
                "draw_prob": "平局概率",
                "away_win_prob": "客胜概率",
                "over_25_prob": "大 2.5 球概率",
                "note_display": "说明",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.header("单场分析")
    match_names = dict(zip(filtered["match_id"], filtered["match_name"]))
    match_id = st.selectbox(
        "比赛",
        filtered["match_id"].tolist(),
        format_func=lambda value: match_names.get(value, value),
    )
    match = filtered[filtered["match_id"] == match_id].iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("主队 xG", f"{match.home_xg:.2f}")
    col2.metric("客队 xG", f"{match.away_xg:.2f}")
    col3.metric("模型优势", f"{match.edge:.1%}")

    st.subheader("概率分布")
    st.bar_chart(
        pd.DataFrame(
            {
                "probability": {
                    "主胜": match.home_win_prob,
                    "平局": match.draw_prob,
                    "客胜": match.away_win_prob,
                    "大 2.5 球": match.over_25_prob,
                }
            }
        )
    )

    st.subheader("风险与说明")
    st.write(_display_risk_tags(match.risk_tags_json))
    st.write(match.note_display)


if __name__ == "__main__":
    main()
