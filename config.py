"""
Configuration and constants for HighTrack NSE.
"""
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_CSV_DIR = DATA_DIR / "raw_csvs"
DB_PATH = DATA_DIR / "hightrack.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_CSV_DIR.mkdir(parents=True, exist_ok=True)

# NSE Settings
NSE_BASE_URL = "https://www.nseindia.com"
NSE_52W_HIGH_URL = "https://www.nseindia.com/api/live-analysis-52week-high-low"
NSE_52W_HIGH_CSV_URL = "https://www.nseindia.com/api/live-analysis-52week-high-low?type=high&csv=true"

# Request Headers to simulate a genuine browser session
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Standard series filter
DEFAULT_SERIES = "EQ"

# Market Cap Tiers in INR Crore
MCAP_TIERS = {
    "All Market Caps": 0,
    "> ₹500 Cr": 500,
    "> ₹1,000 Cr": 1000,
    "> ₹5,000 Cr (Mid/Large)": 5000,
    "> ₹20,000 Cr (Large Cap)": 20000,
    "> ₹50,000 Cr (Mega Cap)": 50000,
}
