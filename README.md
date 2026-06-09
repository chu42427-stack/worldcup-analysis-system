# World Cup Betting Analysis System

Local analysis system for football betting practice.

## Setup

Requires Python 3.11 or newer.

Optional Windows virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

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

## First Local Verification

```powershell
python -m pytest -q
python -m app.pipelines.run_daily --date 2026-06-11 --config config.example.toml
streamlit run app/dashboard.py
```

The dashboard reads `data/worldcup_analysis.sqlite`, and report files are written to `outputs/`.

## Notes

The system produces model probabilities and risk labels for analysis. It does not guarantee betting outcomes.
