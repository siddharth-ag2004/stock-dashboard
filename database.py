"""
Database layer for HighTrack NSE.
Uses SQLite for robust, portable, zero-configuration local and cloud deployment.
"""
import sqlite3
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from config import DB_PATH

def get_connection():
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables and indexes."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Stocks Master Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                symbol TEXT PRIMARY KEY,
                company_name TEXT,
                series TEXT DEFAULT 'EQ',
                sector TEXT DEFAULT 'Uncategorized',
                industry TEXT DEFAULT 'General',
                isin TEXT,
                market_cap_cr REAL DEFAULT 0.0,
                last_updated TEXT
            );
        """)
        
        # Daily Breakouts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_breakouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                series TEXT DEFAULT 'EQ',
                breakout_date TEXT NOT NULL,
                ltp REAL,
                pct_change REAL,
                new_52w_high REAL,
                prev_high REAL,
                prev_high_date TEXT,
                volume INTEGER DEFAULT 0,
                volume_ratio REAL DEFAULT 1.0,
                source_file TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, breakout_date)
            );
        """)
        
        # Market Cap History
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_cap_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                market_cap_cr REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, snapshot_date)
            );
        """)
        
        # Ingestion Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                total_records INTEGER DEFAULT 0,
                eq_records INTEGER DEFAULT 0,
                inserted_records INTEGER DEFAULT 0,
                duplicate_records INTEGER DEFAULT 0,
                message TEXT
            );
        """)
        
        # Indices for optimal query speed
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_breakout_symbol ON daily_breakouts(symbol);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_breakout_date ON daily_breakouts(breakout_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_breakout_series ON daily_breakouts(series);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stocks_sector ON stocks(sector);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stocks_mcap ON stocks(market_cap_cr);")
        
        conn.commit()

def upsert_stock(
    symbol: str,
    company_name: Optional[str] = None,
    series: str = 'EQ',
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    isin: Optional[str] = None,
    market_cap_cr: Optional[float] = None
):
    """Insert or update stock metadata."""
    now = datetime.now().isoformat()
    symbol = symbol.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, company_name, sector, industry, isin, market_cap_cr FROM stocks WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        
        if row:
            new_name = company_name if company_name else row["company_name"]
            new_sector = sector if sector else row["sector"]
            new_industry = industry if industry else row["industry"]
            new_isin = isin if isin else row["isin"]
            new_mcap = market_cap_cr if market_cap_cr is not None else row["market_cap_cr"]
            
            cursor.execute("""
                UPDATE stocks
                SET company_name = ?, series = ?, sector = ?, industry = ?, isin = ?, market_cap_cr = ?, last_updated = ?
                WHERE symbol = ?
            """, (new_name, series, new_sector, new_industry, new_isin, new_mcap, now, symbol))
        else:
            cursor.execute("""
                INSERT INTO stocks (symbol, company_name, series, sector, industry, isin, market_cap_cr, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                company_name or symbol,
                series,
                sector or "Uncategorized",
                industry or "General",
                isin or "",
                market_cap_cr or 0.0,
                now
            ))
        conn.commit()

def insert_breakout(record: Dict[str, Any]) -> bool:
    """
    Insert a daily breakout record.
    Returns True if inserted, False if it was already recorded for that date.
    """
    symbol = str(record["symbol"]).strip().upper()
    series = str(record.get("series", "EQ")).strip().upper()
    breakout_date = str(record["breakout_date"]).strip()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO daily_breakouts (
                    symbol, series, breakout_date, ltp, pct_change,
                    new_52w_high, prev_high, prev_high_date,
                    volume, volume_ratio, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                series,
                breakout_date,
                float(record.get("ltp") or 0.0),
                float(record.get("pct_change") or 0.0),
                float(record.get("new_52w_high") or 0.0),
                float(record.get("prev_high") or 0.0),
                record.get("prev_high_date") or "",
                int(record.get("volume") or 0),
                float(record.get("volume_ratio") or 1.0),
                record.get("source_file") or ""
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate (symbol + breakout_date)
            return False

def delete_breakouts_for_date(breakout_date: str) -> int:
    """Remove all breakout rows for a session before an authoritative rebuild."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM daily_breakouts WHERE breakout_date = ?",
            (breakout_date,),
        )
        return cursor.rowcount


def record_market_cap_snapshot(symbol: str, snapshot_date: str, market_cap_cr: float):
    """Store historical market cap snapshot."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO market_cap_history (symbol, snapshot_date, market_cap_cr)
            VALUES (?, ?, ?)
            ON CONFLICT(symbol, snapshot_date) DO UPDATE SET market_cap_cr = excluded.market_cap_cr
        """, (symbol.strip().upper(), snapshot_date, float(market_cap_cr)))
        
        # Also update current market cap in stocks master
        cursor.execute("""
            UPDATE stocks SET market_cap_cr = ?, last_updated = ? WHERE symbol = ?
        """, (float(market_cap_cr), datetime.now().isoformat(), symbol.strip().upper()))
        conn.commit()

def log_ingestion(
    trading_date: str,
    source: str,
    status: str,
    total: int,
    eq: int,
    inserted: int,
    duplicates: int,
    message: str = ""
):
    """Log the outcome of a data ingestion job."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ingestion_log (
                timestamp, trading_date, source, status,
                total_records, eq_records, inserted_records, duplicate_records, message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            trading_date,
            source,
            status,
            total,
            eq,
            inserted,
            duplicates,
            message
        ))
        conn.commit()

def get_distinct_trading_dates(series: str = "EQ") -> List[str]:
    """Get all unique breakout dates present in the database, descending."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if series == "ALL":
            cursor.execute("SELECT DISTINCT breakout_date FROM daily_breakouts ORDER BY breakout_date DESC")
        else:
            cursor.execute("SELECT DISTINCT breakout_date FROM daily_breakouts WHERE series = ? ORDER BY breakout_date DESC", (series,))
        rows = cursor.fetchall()
        return [row[0] for row in rows]

def get_all_sectors() -> List[str]:
    """Get list of distinct sectors."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT sector FROM stocks WHERE sector IS NOT NULL AND sector != '' ORDER BY sector ASC")
        return [r[0] for r in cursor.fetchall()]

def get_leaderboard_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    series: str = "EQ",
    min_days: int = 1,
    min_mcap: float = 0.0,
    sector: Optional[str] = None
) -> pd.DataFrame:
    """
    Calculate breakout leaderboard aggregating across dates.
    Calculates:
      - Frequency (number of breakout dates)
      - Breakout dates list
      - Latest LTP, Highest 52W High
      - Drawdown %
      - Market Cap
      - Sector & Industry
      - Consecutive Streaks
    """
    with get_connection() as conn:
        # Base query to fetch all breakouts in the date range
        params = []
        where_clauses = []
        
        if series != "ALL":
            where_clauses.append("b.series = ?")
            params.append(series)
            
        if start_date:
            where_clauses.append("b.breakout_date >= ?")
            params.append(start_date)
            
        if end_date:
            where_clauses.append("b.breakout_date <= ?")
            params.append(end_date)
            
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        
        query = f"""
            SELECT 
                b.symbol,
                b.series,
                b.breakout_date,
                b.ltp,
                b.pct_change,
                b.new_52w_high,
                b.prev_high,
                b.volume,
                b.volume_ratio,
                COALESCE(s.company_name, b.symbol) as company_name,
                COALESCE(s.sector, 'Uncategorized') as sector,
                COALESCE(s.industry, 'General') as industry,
                COALESCE(s.market_cap_cr, 0.0) as market_cap_cr
            FROM daily_breakouts b
            LEFT JOIN stocks s ON b.symbol = s.symbol
            {where_sql}
            ORDER BY b.symbol ASC, b.breakout_date ASC
        """
        
        df = pd.read_sql_query(query, conn, params=params)
        
        if df.empty:
            return pd.DataFrame()
            
        # Get list of all distinct trading dates in range (for streak calculation)
        trading_dates = sorted(df['breakout_date'].unique())
        
        # Group by symbol
        grouped = []
        for symbol, group in df.groupby('symbol'):
            company_name = group['company_name'].iloc[0]
            sec = group['sector'].iloc[0]
            ind = group['industry'].iloc[0]
            mcap = group['market_cap_cr'].iloc[0]
            ser = group['series'].iloc[0]
            
            # Filter by market cap if requested
            if mcap < min_mcap:
                continue
                
            # Filter by sector if requested
            if sector and sector != "All" and sec != sector:
                continue
                
            dates_list = group['breakout_date'].tolist()
            num_breakouts = len(dates_list)
            
            if num_breakouts < min_days:
                continue
                
            first_date = dates_list[0]
            latest_date = dates_list[-1]
            
            latest_row = group.sort_values('breakout_date').iloc[-1]
            latest_ltp = latest_row['ltp']
            latest_pct_change = latest_row['pct_change']
            latest_volume_ratio = latest_row['volume_ratio']
            
            highest_52w_high = group['new_52w_high'].max()
            
            # Current Drawdown from highest 52w high: ((latest_ltp - highest) / highest) * 100
            if highest_52w_high > 0:
                drawdown_pct = ((latest_ltp - highest_52w_high) / highest_52w_high) * 100.0
            else:
                drawdown_pct = 0.0
                
            # Streak Calculation against available trading dates
            current_streak, max_streak = calculate_streaks(dates_list, trading_dates)
            
            grouped.append({
                'symbol': symbol,
                'company_name': company_name,
                'series': ser,
                'sector': sec,
                'industry': ind,
                'market_cap_cr': round(mcap, 2),
                'breakout_days': num_breakouts,
                'current_streak': current_streak,
                'max_streak': max_streak,
                'latest_date': latest_date,
                'first_date': first_date,
                'breakout_dates_str': ", ".join(dates_list),
                'breakout_dates_list': dates_list,
                'latest_ltp': round(latest_ltp, 2),
                'highest_52w_high': round(highest_52w_high, 2),
                'drawdown_pct': round(drawdown_pct, 2),
                'latest_pct_change': round(latest_pct_change, 2),
                'volume_ratio': round(latest_volume_ratio, 2)
            })
            
        res_df = pd.DataFrame(grouped)
        if not res_df.empty:
            res_df = res_df.sort_values(
                by=['breakout_days', 'current_streak', 'market_cap_cr'],
                ascending=[False, False, False]
            ).reset_index(drop=True)
            
        return res_df

def calculate_streaks(stock_dates: List[str], all_trading_dates: List[str]) -> Tuple[int, int]:
    """
    Calculate current streak and max streak in terms of trading sessions.
    stock_dates: sorted ascending list of dates stock hit high.
    all_trading_dates: sorted ascending list of all trading dates in the database/universe.
    """
    if not stock_dates:
        return 0, 0
        
    date_set = set(stock_dates)
    all_sorted = sorted(all_trading_dates)
    
    # Calculate max streak across all trading dates
    max_streak = 0
    curr_run = 0
    for d in all_sorted:
        if d in date_set:
            curr_run += 1
            if curr_run > max_streak:
                max_streak = curr_run
        else:
            curr_run = 0
            
    # Calculate current streak (ending at the most recent trading date)
    current_streak = 0
    for d in reversed(all_sorted):
        if d in date_set:
            current_streak += 1
        else:
            break
            
    return current_streak, max_streak

def get_stock_details(symbol: str) -> Dict[str, Any]:
    """Retrieve full history and metadata for a single stock."""
    symbol = symbol.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stocks WHERE symbol = ?", (symbol,))
        stock_info = cursor.fetchone()
        
        breakouts_df = pd.read_sql_query("""
            SELECT * FROM daily_breakouts
            WHERE symbol = ?
            ORDER BY breakout_date ASC
        """, conn, params=(symbol,))
        
        mcap_df = pd.read_sql_query("""
            SELECT * FROM market_cap_history
            WHERE symbol = ?
            ORDER BY snapshot_date ASC
        """, conn, params=(symbol,))
        
        return {
            "stock": dict(stock_info) if stock_info else {"symbol": symbol, "company_name": symbol},
            "breakouts": breakouts_df,
            "mcap_history": mcap_df
        }

def get_ingestion_logs(limit: int = 50) -> pd.DataFrame:
    """Fetch recent ingestion logs."""
    with get_connection() as conn:
        return pd.read_sql_query("""
            SELECT id, timestamp, trading_date, source, status,
                   total_records, eq_records, inserted_records, duplicate_records, message
            FROM ingestion_log
            ORDER BY id DESC
            LIMIT ?
        """, conn, params=(limit,))
