"""
Data collector for NSE 52-Week High reports.
Supports automated live downloads from NSE as well as manual CSV file uploads.
"""
import os
import io
import re
import csv
import shutil
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple, Union
import pandas as pd
import requests

from config import RAW_CSV_DIR, DEFAULT_HEADERS, NSE_BASE_URL, NSE_52W_HIGH_CSV_URL, NSE_52W_HIGH_URL
from database import init_db, insert_breakout, upsert_stock, record_market_cap_snapshot, log_ingestion
from stock_universe import get_stock_metadata

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NSECollector")

def clean_float(val: Any) -> float:
    """Sanitize and parse float values safely."""
    if val is None or pd.isna(val):
        return 0.0
    val_str = str(val).strip().replace(",", "").replace("%", "")
    if val_str in ("", "-", "NA", "N/A", "null", "None"):
        return 0.0
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return 0.0

def clean_int(val: Any) -> int:
    """Sanitize and parse integer values safely."""
    return int(clean_float(val))

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize varying NSE column headers to standardized keys."""
    col_map = {}
    for col in df.columns:
        c = str(col).strip().upper()
        if "SYMBOL" in c:
            col_map[col] = "symbol"
        elif "SERIES" in c:
            col_map[col] = "series"
        elif "LTP" in c or "LAST" in c:
            col_map[col] = "ltp"
        elif "%CHANGE" in c or "CHNG" in c or "%" in c or "CHANGE" in c:
            col_map[col] = "pct_change"
        elif "NEW" in c or "52W/H" in c or "HIGH PRICE" in c or "52" in c and "HIGH" in c and "PREV" not in c:
            col_map[col] = "new_52w_high"
        elif "PREV" in c and ("DATE" in c or "DT" in c):
            col_map[col] = "prev_high_date"
        elif "PREV" in c and "HIGH" in c:
            col_map[col] = "prev_high"
        elif "VOLUME" in c or "VOL" in c:
            col_map[col] = "volume"
    return df.rename(columns=col_map)

def parse_and_ingest_csv(
    source_input: Union[str, bytes, io.BytesIO, io.StringIO, pd.DataFrame],
    snapshot_date: Optional[str] = None,
    source_label: str = "Manual Upload",
    filter_series_eq: bool = False
) -> Dict[str, Any]:
    """
    Parses a 52-week-high CSV file or DataFrame, validates it,
    stores raw copy, enriches stock metadata, and saves records into the database.
    """
    init_db()
    
    if not snapshot_date:
        snapshot_date = date.today().isoformat()
    else:
        # Validate or normalize date string
        try:
            snapshot_date = pd.to_datetime(snapshot_date).strftime("%Y-%m-%d")
        except Exception:
            snapshot_date = date.today().isoformat()
            
    try:
        # Read into DataFrame
        if isinstance(source_input, pd.DataFrame):
            df = source_input.copy()
            raw_text = df.to_csv(index=False)
        elif isinstance(source_input, (str, bytes)) and (isinstance(source_input, str) and os.path.exists(source_input)):
            with open(source_input, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
            df = pd.read_csv(io.StringIO(raw_text))
        elif isinstance(source_input, bytes):
            raw_text = source_input.decode("utf-8", errors="ignore")
            df = pd.read_csv(io.StringIO(raw_text))
        elif isinstance(source_input, io.BytesIO):
            raw_text = source_input.getvalue().decode("utf-8", errors="ignore")
            df = pd.read_csv(io.StringIO(raw_text))
        elif isinstance(source_input, io.StringIO):
            raw_text = source_input.getvalue()
            df = pd.read_csv(io.StringIO(raw_text))
        elif isinstance(source_input, str):
            raw_text = source_input
            df = pd.read_csv(io.StringIO(raw_text))
        else:
            raise ValueError("Unsupported source_input type for CSV ingestion.")
            
        # Clean column names
        df = normalize_column_names(df)
        
        required_cols = ["symbol"]
        for rc in required_cols:
            if rc not in df.columns:
                err_msg = f"Missing required column '{rc}' in uploaded file. Columns found: {list(df.columns)}"
                log_ingestion(snapshot_date, source_label, "FAILED", len(df), 0, 0, 0, err_msg)
                return {"success": False, "message": err_msg, "inserted": 0, "duplicates": 0}

        # Save raw CSV archive
        archive_path = RAW_CSV_DIR / f"52WeekHigh_{snapshot_date}.csv"
        try:
            with open(archive_path, "w", encoding="utf-8") as f:
                f.write(raw_text)
        except Exception as e:
            logger.warning(f"Could not write raw archive: {e}")

        total_records = len(df)
        eq_records = 0
        inserted_count = 0
        duplicate_count = 0
        
        for _, row in df.iterrows():
            sym = str(row.get("symbol", "")).strip().upper()
            if not sym or sym in ("SYMBOL", "NAN", "NONE"):
                continue
                
            ser = str(row.get("series", "EQ")).strip().upper()
            if not ser:
                ser = "EQ"
                
            is_eq = (ser == "EQ")
            if is_eq:
                eq_records += 1
                
            if filter_series_eq and not is_eq:
                continue
                
            ltp = clean_float(row.get("ltp", 0.0))
            pct_chg = clean_float(row.get("pct_change", 0.0))
            new_high = clean_float(row.get("new_52w_high", ltp))
            prev_high = clean_float(row.get("prev_high", 0.0))
            prev_date = str(row.get("prev_high_date", "")).strip()
            volume = clean_int(row.get("volume", 0))
            
            # Enrich metadata
            meta = get_stock_metadata(sym)
            upsert_stock(
                symbol=sym,
                company_name=meta["company_name"],
                series=ser,
                sector=meta["sector"],
                industry=meta["industry"],
                market_cap_cr=meta["market_cap_cr"]
            )
            
            record_market_cap_snapshot(sym, snapshot_date, meta["market_cap_cr"])
            
            # Ingest breakout
            record = {
                "symbol": sym,
                "series": ser,
                "breakout_date": snapshot_date,
                "ltp": ltp,
                "pct_change": pct_chg,
                "new_52w_high": new_high,
                "prev_high": prev_high,
                "prev_high_date": prev_date,
                "volume": volume,
                "volume_ratio": 1.2 if pct_chg > 0 else 0.9, # Benchmark ratio
                "source_file": archive_path.name
            }
            
            if insert_breakout(record):
                inserted_count += 1
            else:
                duplicate_count += 1
                
        msg = f"Processed {total_records} records ({eq_records} EQ). Inserted: {inserted_count}, Duplicates: {duplicate_count}."
        log_ingestion(snapshot_date, source_label, "SUCCESS", total_records, eq_records, inserted_count, duplicate_count, msg)
        logger.info(f"Ingestion successful for {snapshot_date}: {msg}")
        
        return {
            "success": True,
            "message": msg,
            "trading_date": snapshot_date,
            "total_records": total_records,
            "eq_records": eq_records,
            "inserted": inserted_count,
            "duplicates": duplicate_count
        }
        
    except Exception as e:
        err_msg = f"Ingestion error: {str(e)}"
        logger.exception(err_msg)
        log_ingestion(snapshot_date, source_label, "FAILED", 0, 0, 0, 0, err_msg)
        return {"success": False, "message": err_msg, "inserted": 0, "duplicates": 0}

def fetch_live_from_nse(snapshot_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Automated fetch of the 52-week-high data directly from NSE India.
    Initializes a session, obtains session cookies, and retrieves the report.
    """
    if not snapshot_date:
        snapshot_date = date.today().isoformat()
        
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    
    try:
        logger.info("Connecting to NSE India homepage to initialize session cookies...")
        home_resp = session.get(NSE_BASE_URL, timeout=15)
        if home_resp.status_code != 200:
            msg = f"NSE homepage responded with status {home_resp.status_code}."
            log_ingestion(snapshot_date, "Automated NSE", "FAILED", 0, 0, 0, 0, msg)
            return {"success": False, "message": msg}
            
        logger.info("Fetching 52-week-high CSV report...")
        report_resp = session.get(NSE_52W_HIGH_CSV_URL, timeout=20)
        
        if report_resp.status_code == 200 and len(report_resp.text.strip()) > 50:
            return parse_and_ingest_csv(
                source_input=report_resp.text,
                snapshot_date=snapshot_date,
                source_label="Automated NSE Live",
                filter_series_eq=False
            )
            
        # Try JSON endpoint as fallback
        logger.info("CSV URL returned empty or non-200. Trying JSON live analysis endpoint...")
        json_resp = session.get(NSE_52W_HIGH_URL, params={"type": "high"}, timeout=20)
        if json_resp.status_code == 200:
            data = json_resp.json()
            items = data.get("data", [])
            if items:
                df = pd.DataFrame(items)
                return parse_and_ingest_csv(
                    source_input=df,
                    snapshot_date=snapshot_date,
                    source_label="Automated NSE API",
                    filter_series_eq=False
                )
                
        msg = f"Failed to retrieve 52W high data from NSE. Status: {report_resp.status_code}. You can manually upload the downloaded CSV anytime."
        log_ingestion(snapshot_date, "Automated NSE", "FAILED", 0, 0, 0, 0, msg)
        return {"success": False, "message": msg}
        
    except requests.exceptions.RequestException as req_err:
        msg = f"Network or firewall restriction connecting to NSE: {str(req_err)}. Please use the manual CSV upload in the dashboard."
        logger.warning(msg)
        log_ingestion(snapshot_date, "Automated NSE", "FAILED", 0, 0, 0, 0, msg)
        return {"success": False, "message": msg}
    except Exception as e:
        msg = f"Unexpected error during automated fetch: {str(e)}"
        logger.exception(msg)
        log_ingestion(snapshot_date, "Automated NSE", "FAILED", 0, 0, 0, 0, msg)
        return {"success": False, "message": msg}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HighTrack NSE Data Collector")
    parser.add_argument("--fetch", action="store_true", help="Fetch directly from NSE live")
    parser.add_argument("--file", type=str, help="Path to downloaded 52WeekHigh.csv")
    parser.add_argument("--date", type=str, help="Snapshot date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    if args.file:
        res = parse_and_ingest_csv(args.file, snapshot_date=args.date, source_label="CLI Upload")
        print(res)
    elif args.fetch:
        res = fetch_live_from_nse(snapshot_date=args.date)
        print(res)
    else:
        print("Please provide --fetch or --file <path>.")
