# Dashboard UI And Data Upgrade Implementation Plan

## Goal

Implement the first phase of the approved dashboard upgrade:

- betting-practice dashboard UI
- team flags and Chinese display names
- schedule enrichment and a schedule view
- explicit weather and injury data states

The implementation must preserve the existing odds import and model scoring behavior.

## Steps

1. Add display data fixtures.
   - Create `data/manual/team_display.csv`.
   - Create `data/manual/schedule.csv`.
   - Extend `data/manual/injuries.csv` schema with display-friendly fields.

2. Add tests for schedule and display data behavior.
   - Run daily pipeline with a schedule CSV and assert `matches` includes schedule fields.
   - Assert display helpers produce flag + Chinese team labels.
   - Assert dashboard data includes schedule and weather status fields.

3. Implement display helpers.
   - Add a small service module to load team display metadata.
   - Add helpers to format team and match labels.
   - Keep missing display metadata graceful.

4. Implement schedule merge.
   - Let `run_daily` optionally read `schedule.csv`.
   - Merge schedule fields into `matches`.
   - Use raw Chinese team names for display.
   - Keep model team fields unchanged.

5. Upgrade dashboard query and derived states.
   - Include `kickoff_time`, `group_name`, `venue_id`, and latest weather snapshot status.
   - Derive injury status from risk tags.
   - Keep fallback behavior if tables are empty.

6. Upgrade Streamlit UI.
   - Add top KPI row.
   - Add tabs: `实战看板`, `赛程`, `单场分析`.
   - Add readable CSS styling.
   - Use flag + Chinese match labels.
   - Show weather and injury state columns.

7. Verify.
   - Run focused tests.
   - Run `python -m pytest -q`.
   - Regenerate daily data.
   - Restart Streamlit and check service health.

