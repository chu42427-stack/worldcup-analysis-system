# World Cup Betting Analysis System Design

## Goal

Build a local football betting analysis system for World Cup practice. The first version focuses on two workflows:

1. Daily match screening: rank matches by value, risk, and model-market disagreement.
2. Single-match analysis: explain win/draw/loss, handicap, totals, scoreline probabilities, and major risks.

The system must run locally, use free data sources first, and keep paid/API-key data providers replaceable later.

## First-Version Scope

In scope:

- Use the existing 500.com crawler as the odds input. The real local path contains Chinese directory names and should be stored in configuration as `odds_crawler_path`.
- Fetch or import free public data for schedule, venues, weather, Elo, team profiles, squads, coach notes, and recent team context.
- Store normalized data in SQLite.
- Calculate model probabilities with Elo, Poisson, odds-implied probabilities, and rule-based risk factors.
- Provide a Streamlit dashboard for daily screening and single-match drill-down.
- Export CSV/Excel reports for offline review.
- Allow manual overrides for data that is hard to get reliably for free, such as injuries, predicted lineups, player xG adjustments, and tactical notes.

Out of scope for first version:

- Automatic paid data integration.
- Fully automated player xG and verified injury feeds.
- Account login, multi-user permissions, cloud deployment, or automated betting.
- Final champion simulation as the main product surface. It can be added after match-level analysis is stable.

## Architecture

The system is a Python application with three layers:

1. Data pipeline
   - Runs the existing odds crawler.
   - Fetches free external data.
   - Reads manual correction files.
   - Normalizes teams, match IDs, timestamps, and venues.

2. Modeling engine
   - Builds expected goals from Elo, market odds, recent scoring, squad strength, tactical factors, venue/weather, and manual adjustments.
   - Runs Poisson score simulation.
   - Compares model probabilities with market probabilities.
   - Produces value, confidence, and risk labels.

3. Streamlit dashboard
   - Shows daily ranked matches.
   - Provides filters for competition, value rating, risk, model edge, kickoff time, and missing-data status.
   - Shows single-match analysis with market movement, model probabilities, scoreline distribution, factor breakdown, and recommendation notes.
   - Exports CSV/Excel reports.

## Data Sources

### Odds

Primary input:

- Existing local script: `C:\Users\A\Desktop\分析系统\数据抓取\crawl_500_jczq.py`
- Current output example: configured by `odds_csv_path`.

Useful fields already available from the sample:

- Match number, competition, home team, away team.
- Initial and live win/draw/loss odds.
- Initial and live handicap odds.
- Initial and live Asian handicap.
- Initial and live totals line.
- Placeholder xG, xGA, injury xG adjustment, tempo coefficient, low-event coefficient, team scores, and tolerance fields.

Integration rule:

- Treat the 500.com CSV as a raw input file.
- Do not modify the existing crawler in first version unless a small adapter is required.
- Create a normalization layer that maps Chinese field names into internal English field names.

### Schedule, Teams, Venues

Use free public sources first:

- FIFA official pages for tournament structure, schedule, venues, and team confirmation when accessible.
- Manual seed files for World Cup groups, venues, kickoff times, and team aliases.

Reason:

- Official pages are reliable for tournament facts but may not be convenient as machine-readable APIs.
- A local seed file prevents the whole system from breaking if a website layout changes.

### Weather

Use Open-Meteo free APIs for forecast data by venue latitude and longitude.

Stored weather factors:

- Temperature.
- Humidity.
- Wind speed.
- Precipitation probability.
- Weather code.
- Source timestamp.

Model use:

- High heat/humidity reduces expected tempo.
- Heavy wind/rain lowers finishing quality and increases upset/variance risk.
- Indoor or roof-controlled venues can override weather impact.

### Elo

Use a free national-team Elo source when available, with manual fallback.

Stored Elo factors:

- Current Elo.
- Elo rank.
- Recent Elo movement.
- Home/neutral adjustment.

Model use:

- Convert Elo gap into base win/draw/loss expectation.
- Blend with odds and Poisson expected goals.

### Squads, Coach, Tactics, Injuries

First version uses structured manual files plus optional scraping where stable:

- `data/manual/team_profiles.csv`
- `data/manual/squad_strength.csv`
- `data/manual/injuries.csv`
- `data/manual/coach_tactics.csv`
- `data/manual/team_aliases.csv`

Reason:

- Free sources for injuries, xG, and predicted lineups are often incomplete, late, or blocked.
- Manual override files keep the model practical for betting decisions.

## Database Design

Use SQLite at `data/worldcup_analysis.sqlite`.

Tables:

- `raw_odds_500`: original imported odds rows from the 500.com CSV.
- `matches`: canonical match identity, teams, competition, kickoff, venue, group, and status.
- `teams`: canonical team names, aliases, confederation, Elo, strength scores, and profile notes.
- `venues`: venue city, stadium, coordinates, roof/indoor flag, surface notes, and timezone.
- `weather_snapshots`: weather data by match and fetch time.
- `manual_adjustments`: user-controlled correction values by match or team.
- `model_runs`: run timestamp, model version, source completeness, and parameter set.
- `match_predictions`: model output by match and model run.
- `recommendations`: final labels, betting market notes, risk reasons, and suggested action category.

Use a `source_confidence` field where data can be incomplete or manually inferred.

## Modeling Design

The model produces probabilities and explanations, not guaranteed betting instructions.

### Step 1: Market Baseline

- Convert odds into implied probabilities.
- Remove bookmaker margin.
- Track opening-to-live movement.
- Detect market disagreement between win/draw/loss, handicap, Asian handicap, and totals.

Output:

- Market probabilities.
- Market heat index.
- Odds movement direction.
- Suspected trap or overreaction flags.

### Step 2: Elo Baseline

- Calculate Elo difference.
- Adjust for neutral/home context.
- Convert into expected team strength and rough W/D/L probabilities.

Output:

- Elo win/draw/loss estimate.
- Elo mismatch flag.

### Step 3: Expected Goals

Build home and away expected goals from:

- Elo strength gap.
- Recent scoring and conceding form where available.
- Market totals line.
- Team strength and squad depth scores.
- Injury xG adjustments.
- Coach/tactical style modifiers.
- Weather and venue tempo modifiers.
- Group motivation and rotation risk.

Output:

- `home_xg`.
- `away_xg`.
- `total_xg`.
- `tempo_factor`.
- `low_event_factor`.

### Step 4: Poisson Simulation

- Use home and away xG to compute score probabilities.
- Generate W/D/L, handicap cover, totals over/under, and likely scorelines.

Output:

- Model probabilities for each market.
- Top scorelines.
- Draw and upset risk.

### Step 5: Value And Risk

Compare model probability with market probability.

Value labels:

- `Strong value`: model edge is high and data confidence is acceptable.
- `Lean value`: edge exists but risk or missing data limits confidence.
- `No bet`: no clear edge.
- `Avoid`: high uncertainty, poor data, or conflicting signals.

Risk tags:

- Missing injury/lineup data.
- High rotation risk.
- Weather/venue variance.
- Market movement conflict.
- Low-event draw risk.
- Favorite overheat.
- Style mismatch.
- Group motivation uncertainty.

## Dashboard Design

### Daily Screening Page

Columns:

- Kickoff time.
- Match.
- Competition/group.
- Model W/D/L.
- Market W/D/L.
- Edge.
- Handicap lean.
- Totals lean.
- Recommendation.
- Risk level.
- Data completeness.

Filters:

- Date.
- Recommendation.
- Risk level.
- Edge threshold.
- Missing-data status.
- Competition/group/team.

### Single-Match Page

Sections:

- Match header: teams, kickoff, venue, weather, group motivation.
- Market panel: opening odds, live odds, implied probabilities, movement.
- Model panel: xG, Poisson scoreline table, W/D/L, handicap, totals.
- Factor breakdown: Elo, squad depth, injuries, coach tactics, weather, style matchup, motivation.
- Recommendation panel: action category, confidence, risk reasons, and notes.
- Manual override panel: injury xG, squad score, motivation, tactical notes, and final analyst comment.

### Reports

Export:

- `outputs/daily_screening_YYYY-MM-DD.csv`
- `outputs/daily_screening_YYYY-MM-DD.xlsx`
- `outputs/match_analysis_<match_id>.html` if needed later.

## Project Structure

Proposed structure:

```text
worldcup/
  app/
    dashboard.py
    config.py
    db.py
    models/
      market.py
      elo.py
      xg.py
      poisson.py
      scoring.py
    pipelines/
      import_odds_500.py
      fetch_weather.py
      fetch_elo.py
      import_manual.py
      run_daily.py
    services/
      team_matcher.py
      data_quality.py
      recommendations.py
  data/
    manual/
      team_aliases.csv
      team_profiles.csv
      squad_strength.csv
      injuries.csv
      coach_tactics.csv
      venues.csv
    raw/
    processed/
    worldcup_analysis.sqlite
  outputs/
  tests/
  docs/
```

## Configuration

Use `.env` or `config.toml` later for optional paid providers.

First version settings:

- Path to 500.com crawler, including support for Chinese Windows paths.
- Path to latest odds CSV, including support for Chinese Windows paths.
- SQLite path.
- Weather refresh interval.
- Model weights.
- Manual data directory.

Paid provider placeholders:

- `FOOTBALL_DATA_API_KEY`
- `INJURY_DATA_API_KEY`
- `PLAYER_XG_API_KEY`
- `ODDS_API_KEY`

## Error Handling And Data Quality

Each model run includes a data quality score.

Rules:

- If odds are missing, no recommendation is produced.
- If weather is missing, run model but mark weather confidence as low.
- If lineup/injury data is missing, use neutral defaults and raise risk label.
- If team name cannot be matched confidently, quarantine the row for manual review.
- If external fetch fails, use cached data and mark source as stale.

## Testing Strategy

Tests focus on business logic and data reliability:

- Odds CSV import maps fields correctly.
- Team aliases normalize Chinese and English names.
- Market implied probability removes margin correctly.
- Poisson probabilities sum close to 1.
- Recommendation labels respond correctly to edge and risk.
- Missing data produces warnings rather than crashes.
- A sample daily pipeline run creates expected database rows and report files.

## Implementation Sequence

1. Create project scaffold and dependency file.
2. Build odds CSV importer for the existing 500.com output.
3. Add SQLite schema and database helper.
4. Add manual seed files for teams, aliases, venues, and model overrides.
5. Build market probability and Poisson modules.
6. Add Elo and weather adapters with cache-first behavior.
7. Add recommendation scoring and risk labels.
8. Build Streamlit dashboard pages.
9. Add CSV/Excel export.
10. Add tests and sample run command.

## Open Decisions

- Exact World Cup team/group seed file should be verified before production use.
- Free player xG source may not be reliable; first version should support manual xG adjustment.
- Injury and predicted lineup automation should be treated as optional until a stable source is confirmed.
- Existing 500.com crawler has mojibake in source comments/strings when read in this environment, but the output CSV header is usable UTF-8.
