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
from app.services.display import format_match_label, load_team_display
from app.services.injuries import injury_status_for_match, load_injury_records

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


def _parse_risk_tags(value: str) -> list[str]:
    try:
        tags = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return tags if isinstance(tags, list) else []


def _data_status(row: pd.Series) -> str:
    missing = []
    if row.weather_status == "缺失":
        missing.append("天气")
    if row.injury_status == "待确认":
        missing.append("伤停")
    if not row.kickoff_time:
        missing.append("赛程")
    return "完整" if not missing else "缺失：" + "、".join(missing)


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
                mt.home_team,
                mt.away_team,
                mt.kickoff_time,
                mt.group_name,
                mt.venue_id,
                case
                    when w.match_id is null then '缺失'
                    else '已获取'
                end as weather_status,
                w.temperature_c,
                w.humidity_pct,
                w.wind_kph,
                w.precipitation_probability,
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
            left join (
                select ws.*
                from weather_snapshots ws
                join (
                    select match_id, max(fetched_at) as fetched_at
                    from weather_snapshots
                    group by match_id
                ) latest
                  on latest.match_id = ws.match_id
                 and latest.fetched_at = ws.fetched_at
            ) w
              on w.match_id = r.match_id
            where m.run_time = (select max(run_time) from model_runs)
            order by r.confidence desc, r.edge desc
            """,
        )


def _display_risk_tags(value: str) -> object:
    tags = _parse_risk_tags(value)
    if not tags:
        return value
    if isinstance(tags, list):
        return [_translate_risk_tag(tag) for tag in tags]
    return tags


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .main .block-container { padding-top: 1.5rem; }
        .wc-hero {
            border: 1px solid #d8dee6;
            border-radius: 8px;
            padding: 18px 20px;
            background: #f7f9fb;
            margin-bottom: 14px;
        }
        .wc-hero h1 { margin: 0 0 6px 0; font-size: 28px; }
        .wc-hero p { margin: 0; color: #536171; }
        .wc-card {
            border: 1px solid #dfe5ec;
            border-radius: 8px;
            padding: 14px;
            background: #ffffff;
            margin-bottom: 10px;
        }
        .wc-match-title { font-size: 17px; font-weight: 700; margin-bottom: 8px; }
        .wc-meta { color: #667382; font-size: 13px; }
        .wc-badge {
            display: inline-block;
            border-radius: 999px;
            padding: 3px 9px;
            background: #eef4ff;
            color: #255c99;
            font-size: 12px;
            margin-right: 6px;
        }
        .wc-warning { color: #9a5b00; }
        .wc-good { color: #137547; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="世界杯竞彩分析系统", layout="wide")
    _inject_styles()

    cfg = load_config(PROJECT_ROOT / "config.toml")
    team_display = load_team_display(PROJECT_ROOT / "data" / "manual" / "team_display.csv")
    injury_records = load_injury_records(PROJECT_ROOT / "data" / "manual" / "injuries.csv")
    st.markdown(
        """
        <div class="wc-hero">
          <h1>世界杯竞彩分析系统</h1>
          <p>赔率、xG、Poisson、风险标签和数据完整性一屏筛选。仅作赛前决策辅助，不代表确定收益。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
    data["risk_tags"] = data["risk_tags_json"].map(_parse_risk_tags)
    data["injury_status"] = data["match_id"].map(
        lambda match_id: injury_status_for_match(match_id, injury_records)
    )
    data["match_display"] = data.apply(
        lambda row: format_match_label(row.home_team, row.away_team, team_display)
        if pd.notna(row.home_team) and pd.notna(row.away_team)
        else row.match_name,
        axis=1,
    )
    data["data_status"] = data.apply(_data_status, axis=1)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("今日比赛", len(data))
    kpi2.metric("强价值", int((data["label"] == "Strong value").sum()))
    kpi3.metric("高风险", int((data["risk_level"] == "high").sum()))
    kpi4.metric("数据缺失", int((data["data_status"] != "完整").sum()))

    board_tab, schedule_tab, single_tab = st.tabs(["实战看板", "赛程", "单场分析"])

    with board_tab:
        st.subheader("每日筛选")
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
                    "match_display",
                    "kickoff_time",
                    "market_display",
                    "label_display",
                    "edge",
                    "confidence",
                    "risk_level_display",
                    "home_xg",
                    "away_xg",
                    "weather_status",
                    "injury_status",
                    "data_status",
                    "note_display",
                ]
            ].rename(
                columns={
                    "match_display": "比赛",
                    "kickoff_time": "开球时间",
                    "market_display": "市场",
                    "label_display": "推荐结论",
                    "edge": "模型优势",
                    "confidence": "置信度",
                    "risk_level_display": "风险等级",
                    "home_xg": "主队 xG",
                    "away_xg": "客队 xG",
                    "weather_status": "天气",
                    "injury_status": "伤停",
                    "data_status": "数据状态",
                    "note_display": "说明",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with schedule_tab:
        st.subheader("赛程")
        schedule_view = data[
            [
                "kickoff_time",
                "group_name",
                "venue_id",
                "match_display",
                "weather_status",
                "injury_status",
            ]
        ].drop_duplicates()
        st.dataframe(
            schedule_view.rename(
                columns={
                    "kickoff_time": "开球时间",
                    "group_name": "分组/轮次",
                    "venue_id": "场地",
                    "match_display": "比赛",
                    "weather_status": "天气",
                    "injury_status": "伤停",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with single_tab:
        st.subheader("单场分析")
        match_names = dict(zip(data["match_id"], data["match_display"]))
        match_id = st.selectbox(
            "比赛",
            data["match_id"].tolist(),
            format_func=lambda value: match_names.get(value, value),
        )
        match = data[data["match_id"] == match_id].iloc[0]

        st.markdown(
            f"""
            <div class="wc-card">
              <div class="wc-match-title">{match.match_display}</div>
              <span class="wc-badge">{match.label_display}</span>
              <span class="wc-badge">风险：{match.risk_level_display}</span>
              <span class="wc-badge">数据：{match.data_status}</span>
              <div class="wc-meta">开球：{match.kickoff_time or "待确认"} ｜ 场地：{match.venue_id or "待确认"} ｜ 分组：{match.group_name or "待确认"}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("主队 xG", f"{match.home_xg:.2f}")
        col2.metric("客队 xG", f"{match.away_xg:.2f}")
        col3.metric("模型优势", f"{match.edge:.1%}")
        col4.metric("置信度", f"{match.confidence:.1%}")

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

        weather_col, injury_col = st.columns(2)
        with weather_col:
            st.subheader("天气")
            if match.weather_status == "已获取":
                st.write(
                    {
                        "温度": match.temperature_c,
                        "湿度": match.humidity_pct,
                        "风速": match.wind_kph,
                        "降水": match.precipitation_probability,
                    }
                )
            else:
                st.warning("天气数据缺失：需要补充赛程场地、经纬度并运行天气抓取。")
        with injury_col:
            st.subheader("伤停")
            if match.injury_status == "待确认":
                st.warning("伤停数据待确认：请维护 data/manual/injuries.csv。")
            else:
                st.success("伤停数据已维护。")

        st.subheader("风险与说明")
        st.write(_display_risk_tags(match.risk_tags_json))
        st.write(match.note_display)


if __name__ == "__main__":
    main()
