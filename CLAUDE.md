# CLAUDE.md - HighTrack NSE Project Context & Knowledge Base

## 1. Project Overview & Objective

**HighTrack NSE** is an automated momentum intelligence screener and quantitative research platform for Indian equities traded on the **National Stock Exchange of India (NSE)**, primarily targeting the mainboard **EQ (Equity)** series.

### The Problem It Solves
Single-day 52-week high breakouts often result in false signals or bull traps. HighTrack NSE identifies sustained institutional accumulation and genuine momentum by tracking:
1. **Breakout Frequency**: How many distinct trading sessions a stock has printed a fresh 52-week high across rolling windows (7D, 15D, 30D, 60D, 90D, or All-Time).
2. **Consecutive Streaks**: Real trading-session consecutive streaks (ignoring weekends and NSE holidays) ending on the latest session.
3. **Peak Drawdown**: Distance from the highest recorded 52W high to identify healthy pullbacks vs. blown-off tops.
4. **Market Breadth & Sector Trends**: Aggregated sector momentum and daily breakout distribution.

---

## 2. Tech Stack & Environment

- **Frontend / Dashboard**: Streamlit (>= 1.35.0), Plotly (>= 5.20.0)
- **Data & Computation**: Python 3.11, Pandas (>= 2.2.0), SQLite3
- **Network / Scraping**: Requests (>= 2.31.0), yfinance (>= 0.2.38)
- **Deployment Platform**: Streamlit Community Cloud (`https://stock-dashboard-hightrack.streamlit.app`)
- **Automation / Scheduler**: GitHub Actions (`.github/workflows/daily_collector.yml`)
- **Theme**: Dark financial terminal theme (`.streamlit/config.toml`)
- **Local Environment**: macOS, virtual environment at `.venv`

---

## 3. Repository Structure

```
stock-dashboard/
├── app.py                      # Main Streamlit dashboard application (4 tabs, filters, charts)
├── database.py                 # SQLite schema, indexing, queries, streak & leaderboard logic
├── collector.py                # NSE data ingestion engine (MTF PR API, backfills, parsers)
├── stock_universe.py           # Master NSE stock metadata (symbols, sectors, industries, mcap)
├── sample_data.py              # Synthetic seed generator (used only if database is completely empty)
├── config.py                   # Paths, constants, market cap tiers, default HTTP headers
├── requirements.txt            # Python dependencies (pinned for Streamlit Cloud & Actions)
├── run.sh                      # Shell launch script for local development
├── Procfile / render.yaml      # Render/Heroku blueprint deployment specs (optional)
├── .streamlit/
│   ├── config.toml             # Streamlit dark theme & headless settings
│   └── credentials.toml        # Disable telemetry / email prompt
├── .github/workflows/
│   └── daily_collector.yml     # Multi-slot weekday cron job committing DB updates
├── data/
│   ├── hightrack.db            # Embedded SQLite database (committed to repo for persistence)
│   └── raw_csvs/               # Historical backup CSVs
└── CLAUDE.md                   # This project reference document
```

---

## 4. Database Architecture (`data/hightrack.db`)

Embedded SQLite database with indexes optimized for daily time-series filtering and symbol lookups:

### Schema Overview

1. **`stocks`**
   - `symbol` (TEXT PRIMARY KEY) - NSE trading symbol (e.g. `RELIANCE`, `TCS`)
   - `company_name` (TEXT) - Full company name
   - `series` (TEXT DEFAULT 'EQ') - Market series (`EQ`, `BE`, `SM`, `ST`)
   - `sector` (TEXT) - Sector classification (from `stock_universe.py`)
   - `industry` (TEXT) - Industry classification
   - `isin` (TEXT) - International Securities Identification Number
   - `market_cap_cr` (REAL) - Latest market capitalization in ₹ Crores
   - `last_updated` (TEXT) - ISO timestamp

2. **`daily_breakouts`**
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `symbol` (TEXT NOT NULL)
   - `series` (TEXT DEFAULT 'EQ')
   - `breakout_date` (TEXT NOT NULL, format `YYYY-MM-DD`)
   - `ltp` (REAL) - Last Traded Price on breakout date
   - `pct_change` (REAL) - Daily percentage change
   - `new_52w_high` (REAL) - The 52W high printed on that date
   - `prev_high` (REAL) - Previous recorded 52W high
   - `prev_high_date` (TEXT) - Date previous 52W high occurred
   - `volume` (INTEGER) - Total traded volume
   - `volume_ratio` (REAL DEFAULT 1.0) - Volume relative to moving average
   - `source_file` (TEXT) - Archive member or source identifier
   - `created_at` (TEXT DEFAULT CURRENT_TIMESTAMP)
   - **Constraint**: `UNIQUE(symbol, breakout_date)`

3. **`market_cap_history`**
   - `symbol` (TEXT NOT NULL)
   - `snapshot_date` (TEXT NOT NULL)
   - `market_cap_cr` (REAL NOT NULL)
   - **Constraint**: `UNIQUE(symbol, snapshot_date)`

4. **`ingestion_log`**
   - Tracks every automated or manual run (`trading_date`, `status`, `total_records`, `eq_records`, `inserted_records`, `message`).

---

## 5. Data Ingestion & Pipeline Details

### Primary Data Source: MTF PR Archive API
- **Endpoint**: `https://mtf.trading/api/v1/pr?date=YYYY-MM-DD&file=<member>`
- Mirrors the official NSE daily Price Report (`PR<ddmmyy>.zip`) archive.
- Key Members ingested:
  1. `file=pd`: Security-wise price data (`SYMBOL`, `SERIES`, `HIGH_PRICE`, `HI_52_WK`, `CLOSE_PRICE`, `PREV_CLOSE`, `NET_TRDQTY`).
     - **Breakout Condition**: `HIGH_PRICE >= HI_52_WK - 0.05` (0.05 tolerance) and `SERIES in ('EQ', 'BE', 'SM', 'ST')`.
  2. `file=mcap`: Security market capitalisation data for accurate numeric market cap in ₹ Crores.
- **Why NOT `file=hl`**: NSE's `hl` member mixes highs and lows together, contains ETFs, and uses security names rather than exact ticker symbols.
- **Why NOT Direct NSE Scraping**: `nseindia.com` enforces Akamai Bot Manager / WAF, returning `403 Forbidden` on headless and cloud IP addresses.

### Automated Cron Collection (`daily_collector.yml`)
- Triggered on weekdays via GitHub Actions at multiple UTC slots to prevent dropped runs:
  - `10:45 UTC` (16:15 IST - market closes at 15:30 IST)
  - `12:20 UTC` (17:50 IST)
  - `14:20 UTC` (19:50 IST)
  - `16:50 UTC` (22:20 IST)
- Command: `python collector.py --pr auto`
- Workflow commits `data/hightrack.db` directly and pushes to both `main` and `master` branches.
- Pushes trigger automatic redeployment on Streamlit Community Cloud within 1-2 minutes.

### Holidays / No-Session Days
- There is no holiday calendar. If the MTF API returns no `pd` rows for a date, `fetch_from_mtf_pr` logs status `NO_SESSION` in `ingestion_log` and returns `no_session: True`.
- `collector.py --pr` exits **0** for `no_session` (so GitHub Actions stays green on NSE holidays) and **1** only for real failures.
- `pending_session_dates()` skips dates with a `NO_SESSION` log entry once they are >= 2 days old (`get_confirmed_no_session_dates`), so late-published sessions are still retried.
- Example: 2026-11-10 (Diwali Balipratipada) was a holiday; all 4 runs failed before this fix.
- GitHub cron slots can fire hours late (10:45 UTC slot ran ~18:14 UTC); the 4 retry slots cover this.

### In-App Startup Sync (`sync_recent_sessions`)
- Whenever a user opens `app.py`, `pending_session_dates()` checks if any closed trading session weekdays are missing from the DB.
- Missing dates are automatically fetched via MTF PR API in the background.

---

## 6. Dashboard Structure & User Experience (`app.py`)

Navigation uses `st.segmented_control` with a pre-render `pending_tab` queue pattern to avoid `StreamlitWidgetAlreadyInstantiatedError`:

1. **Breakout Leaderboard** (Default view):
   - Interactive table of top momentum stocks ranked by `breakout_days DESC`, `current_streak DESC`, `market_cap_cr DESC`.
   - Headers indicate default sorting: `High Days ↓`, `Current Streak ↓`, `Market Cap (Cr) ↓`.
   - Pure numeric values (no string prefixes) for accurate client-side sorting.
   - Click-to-drilldown: Clicking any row navigates directly to **Stock Deep-Dive** for that symbol.
2. **Stock Deep-Dive**:
   - Deep analysis of an individual stock.
   - High progression timeline, daily % change bar chart, volume confirmation.
   - Direct clickable link to official NSE equity quote page (`https://www.nseindia.com/get-quotes/equity?symbol=...`).
3. **Market Breadth & Trends**:
   - Daily 52-week high count bar chart over time.
   - Sector distribution and momentum concentration.
4. **Data Ingestion & Health**:
   - Status of historical sessions in database.
   - Ingestion logs, manual CSV uploader, and on-demand backfill controls.

### Sidebar Filters
- **Equity Universe**: `EQ Only (Mainboard Equity)` (Default), `EQ + BE`, `All Series`.
- **Timeframe**: `30 Days` (Default), `7 Days`, `15 Days`, `60 Days`, `90 Days`, `All Time`.
- **Market Cap**: `> ₹500 Cr` (Default), `> ₹1,000 Cr`, `> ₹5,000 Cr`, `> ₹20,000 Cr`, `All Market Caps`.
- **Breakout Frequency**: Minimum breakout days slider (default: 1).
- **Hit 52W High Today**: Toggle to filter strictly to stocks that hit a new 52W high on the latest trading session.
- **Search**: Symbol or company name filter.

---

## 7. Key Calculations & Math

### 1. Streaks (`database.py -> calculate_streaks`)
- Uses full calendar of all recorded NSE trading dates in ascending order.
- **Current Streak**: Number of consecutive trading sessions ending at the most recent session where the stock broke out.
- **Max Streak**: Longest continuous sequence of consecutive trading sessions with breakouts across the period.

### 2. Drawdown from Peak
$$\text{Drawdown \%} = \frac{\text{LTP} - \text{Highest 52W High}}{\text{Highest 52W High}} \times 100$$
- `0.0%` means stock is trading at its highest level.
- Negative percentage represents pullback from peak breakout level.

---

## 8. Development & Maintenance Commands

### Local Testing
```bash
# Run local Streamlit server (use HOME=/tmp on macOS to avoid permission issues)
HOME=/tmp ./.venv/bin/streamlit run app.py --server.port 8501

# Run with shell helper
./run.sh
```

### Collector CLI Commands
```bash
# Fetch latest closed session automatically (IST time-aware)
python collector.py --pr auto

# Fetch specific date from MTF PR archive
python collector.py --pr 2026-11-05

# Backfill N trading days of historical data
python collector.py --backfill 30

# Ingest local CSV file
python collector.py --file path/to/52WeekHigh.csv --date 2026-11-05
```

### GitHub Actions Trigger
```bash
# Manually trigger workflow via GitHub CLI
gh workflow run daily_collector.yml
gh run watch <run_id>
```

---

## 9. Important User Rules & Conventions

- **Deploys**: Streamlit Cloud deploys from `master`; the workflow and manual pushes must update both `main` and `master`.
- **Do NOT push to Git without explicit user approval** if the user asks to test locally first. Pushing to `main` immediately triggers a live production deployment on Streamlit Cloud.
- **No Emojis in Data Tables**: Emojis were intentionally removed from table headers and cell values per user request.
- **Numeric Market Cap**: The market cap column is formatted purely as numbers with `(Cr)` in the header for proper numerical column sorting.
- **Sector Mapping**: The `stocks` table contains basic sector mappings; unmapped stocks fall back to `Uncategorized` or `Other Equities`.
