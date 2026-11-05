# 📈 HighTrack NSE - 52-Week High Intelligence Dashboard

> **Automated research platform and momentum scanner for NSE Mainboard Equities (EQ Series) repeatedly making fresh 52-week highs.**

---

## 🌟 Overview & Key Capabilities

When stocks break out to fresh 52-week highs, isolated single-day breakouts often produce false positives. **HighTrack NSE** isolates true institutional momentum by tracking:

1. **Repeated Breakout Frequency**:
   - Ranks stocks by how many distinct trading sessions they hit fresh 52-week highs across rolling windows (**7D, 15D, 30D, 60D, 90D, or All-Time**).
2. **Consecutive-Day Breakout Streaks**:
   - Calculates **Active Streaks** (stocks hitting new highs today/consecutive sessions) and **Historical Max Streaks**, accounting for weekends and market holidays.
3. **Market Capitalisation Filters**:
   - Quickly filter by market cap: **> ₹500 Cr (Default)**, **> ₹1,000 Cr**, **> ₹5,000 Cr**, **> ₹20,000 Cr**, or custom range.
4. **Mainboard Equity Universe (EQ)**:
   - Filters out illiquid penny or SME stocks while allowing full flexibility to inspect other series (BE, SM, ST) if desired.
5. **Drawdown from Peak**:
   - Tracks current price vs the highest recorded 52W high to identify healthy pullbacks in leading momentum stocks.
6. **Sector & Industry Momentum**:
   - Sector-wise breakdown, treemap visualizations, and breadth indicators to spot where momentum is concentrated (e.g. Capital Goods, Tech, Financials, Healthcare).
7. **Stock Deep-Dive**:
   - Individual stock page showing all breakout dates, price progression timeline, daily % change, and volume confirmation ratio.
8. **Dual Ingestion (Automated + 1-Click Upload)**:
   - **Automated**: Directly scrapes and parses NSE India reports with session cookie warming.
   - **Manual Upload**: Drag-and-drop your downloaded `52WeekHigh.csv` directly in the dashboard and assign the trading date.
9. **One-Click Export**:
   - Download the full filtered leaderboard to **CSV** or styled **Excel (.xlsx)**.

---

## 📁 Project Architecture

```
stock-dashboard/
├── app.py                      # Main Streamlit interactive dashboard
├── database.py                 # SQLite database layer, schema, indexes & queries
├── collector.py                # Automated NSE fetcher + CSV parser + validator
├── stock_universe.py           # NSE EQ stock metadata, sectors, industries & mcap
├── sample_data.py              # Realistic 30-day historical seed generator
├── config.py                   # Configuration paths, URLs, and constants
├── run.sh                      # 1-click startup script for macOS/Linux
├── requirements.txt            # Python dependencies
├── Procfile                    # Render / Heroku deployment specification
├── render.yaml                 # Render Blueprint configuration
├── .streamlit/
│   ├── config.toml             # Dark modern financial UI theme
│   └── credentials.toml        # Non-interactive configuration
├── .github/workflows/
│   └── daily_collector.yml     # Automated free daily cron job on GitHub Actions
└── data/
    ├── hightrack.db            # SQLite database with all historical breakouts
    └── raw_csvs/               # Preserved exact historical raw CSVs
```

---

## 🚀 How to Run Locally

You don't need to configure any external database; the application includes its own embedded, pre-indexed SQLite database and a pre-configured Python environment.

### Quick Start (1 Command)
In your terminal, navigate to the folder and run:

```bash
./run.sh
```

Or run directly with Streamlit:

```bash
./.venv/bin/streamlit run app.py
```

Open your browser at: **`http://localhost:8501`**

---

## ☁️ Cloud Deployment Options

### Option A: Streamlit Community Cloud (Recommended & 100% Free)
1. Push this folder to your GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Connect your GitHub repository and select `app.py`.
4. Click **Deploy**. Your dashboard is now accessible on the web!

### Option B: Render (Web Service / Blueprint)
1. Push this folder to GitHub.
2. In [Render.com](https://render.com), click **New + > Blueprint** and select your repository.
3. Render will read `render.yaml` and deploy your app automatically.

---

## ⏰ Automated Daily Data Collection

A GitHub Actions workflow is included at `.github/workflows/daily_collector.yml`.
- First run is **Monday through Friday at 4:15 PM IST**. Three later runs the same evening retry the same session, because GitHub sometimes drops a single scheduled run.
- The job asks for the latest **closed** NSE session in IST (not the UTC date), fetches it from the MTF/NSE PR archive API, writes it into `hightrack.db`, and commits that database.
- Opening the dashboard also downloads a closed session if it is missing from the database.
- You can also manually trigger it anytime from the GitHub Actions tab.

Historical sessions in `hightrack.db` are API-sourced `PR_YYYY-MM-DD.json` records. To replace an older mixed-source range with the authoritative archive data, run:

```bash
python collector.py --rebuild-api-start YYYY-MM-DD --rebuild-api-end YYYY-MM-DD
```

---

## 📊 Ingesting Your Daily NSE CSV Manually

If you prefer to manually download `52WeekHigh.csv` from [NSE India](https://www.nseindia.com/market-data/52-week-high-equity-market):
1. Open the dashboard and navigate to the **⚙️ Data Ingestion & Health** tab.
2. Under **Upload Downloaded NSE CSV**, drop your file.
3. Confirm the snapshot date (defaults to today) and click **Process & Ingest CSV**.
4. The system validates the columns, removes duplicates, enriches sectors, and updates all rankings instantly!
