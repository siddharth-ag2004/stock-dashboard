"""
Historical seed data generator for HighTrack NSE.
Populates realistic 30-day historical 52-week-high data leading up to 2026-11-04,
featuring realistic momentum leaders, repeated breakout dates, and consecutive streaks.
"""
import random
from datetime import datetime, timedelta, date
from database import init_db, insert_breakout, upsert_stock, record_market_cap_snapshot, log_ingestion
from stock_universe import NSE_STOCKS_MASTER, get_stock_metadata

# Real stocks known for hitting multi-session 52-week highs
POPULAR_BREAKOUT_STOCKS = [
    # Top repeated breakout momentum leaders
    {"symbol": "TRENT", "base_price": 7800, "step": 45, "freq": 9, "streak_at_end": 4},
    {"symbol": "DIXON", "base_price": 14200, "step": 80, "freq": 8, "streak_at_end": 3},
    {"symbol": "BEL", "base_price": 310, "step": 3.5, "freq": 7, "streak_at_end": 2},
    {"symbol": "HAL", "base_price": 4900, "step": 50, "freq": 6, "streak_at_end": 1},
    {"symbol": "ANANDRATHI", "base_price": 2200, "step": 25, "freq": 6, "streak_at_end": 2},
    {"symbol": "ALIVUS", "base_price": 1420, "step": 18, "freq": 5, "streak_at_end": 1},
    {"symbol": "COCHINSHIP", "base_price": 2100, "step": 35, "freq": 5, "streak_at_end": 0},
    {"symbol": "POLYCAB", "base_price": 6800, "step": 60, "freq": 5, "streak_at_end": 2},
    {"symbol": "PERSISTENT", "base_price": 5400, "step": 55, "freq": 4, "streak_at_end": 0},
    {"symbol": "BHARATFORG", "base_price": 1620, "step": 14, "freq": 4, "streak_at_end": 1},
    {"symbol": "MOTHERSON", "base_price": 195, "step": 2.2, "freq": 4, "streak_at_end": 0},
    {"symbol": "MAZDOCK", "base_price": 4600, "step": 75, "freq": 4, "streak_at_end": 2},
    {"symbol": "ZOMATO", "base_price": 270, "step": 4.0, "freq": 4, "streak_at_end": 1},
    {"symbol": "MAXHEALTH", "base_price": 1050, "step": 12, "freq": 3, "streak_at_end": 1},
    {"symbol": "KAYNES", "base_price": 5300, "step": 65, "freq": 3, "streak_at_end": 0},
    {"symbol": "CGPOWER", "base_price": 740, "step": 8.0, "freq": 3, "streak_at_end": 0},
    {"symbol": "SUZLON", "base_price": 78, "step": 1.2, "freq": 3, "streak_at_end": 1},
    {"symbol": "PRESTIGE", "base_price": 1880, "step": 22, "freq": 3, "streak_at_end": 0},
    {"symbol": "ALGOQUANT", "base_price": 74, "step": 1.1, "freq": 3, "streak_at_end": 1},
    {"symbol": "SUNPHARMA", "base_price": 1850, "step": 15, "freq": 2, "streak_at_end": 1},
    {"symbol": "BHARTIARTL", "base_price": 1680, "step": 12, "freq": 2, "streak_at_end": 0},
    {"symbol": "VOLTAS", "base_price": 1820, "step": 20, "freq": 2, "streak_at_end": 0},
    {"symbol": "CHAMBLFERT", "base_price": 520, "step": 6.5, "freq": 2, "streak_at_end": 1},
    {"symbol": "IREDA", "base_price": 240, "step": 3.8, "freq": 2, "streak_at_end": 0},
    {"symbol": "INDHOTEL", "base_price": 720, "step": 8.5, "freq": 2, "streak_at_end": 1},
    {"symbol": "VBL", "base_price": 630, "step": 7.0, "freq": 2, "streak_at_end": 0},
    {"symbol": "GODREJPROP", "base_price": 3150, "step": 35, "freq": 2, "streak_at_end": 0},
    {"symbol": "APARINDS", "base_price": 9800, "step": 95, "freq": 2, "streak_at_end": 1},
    # Occasional 1-day breakout stocks
    {"symbol": "RELIANCE", "base_price": 2980, "step": 15, "freq": 1, "streak_at_end": 0},
    {"symbol": "TCS", "base_price": 4150, "step": 25, "freq": 1, "streak_at_end": 0},
    {"symbol": "HDFCBANK", "base_price": 1780, "step": 10, "freq": 1, "streak_at_end": 1},
    {"symbol": "INFY", "base_price": 1920, "step": 18, "freq": 1, "streak_at_end": 0},
    {"symbol": "DLF", "base_price": 890, "step": 8, "freq": 1, "streak_at_end": 0},
    {"symbol": "COFORGE", "base_price": 7600, "step": 70, "freq": 1, "streak_at_end": 0},
    {"symbol": "FORTIS", "base_price": 560, "step": 6, "freq": 1, "streak_at_end": 1},
    {"symbol": "BLUESTARCO", "base_price": 1960, "step": 22, "freq": 1, "streak_at_end": 0},
    {"symbol": "DEEPAKNTR", "base_price": 2840, "step": 28, "freq": 1, "streak_at_end": 0},
    {"symbol": "AUROPHARMA", "base_price": 1490, "step": 14, "freq": 1, "streak_at_end": 1},
    {"symbol": "LUPIN", "base_price": 2180, "step": 24, "freq": 1, "streak_at_end": 0},
    {"symbol": "TORNTPOWER", "base_price": 1840, "step": 18, "freq": 1, "streak_at_end": 1},
    {"symbol": "HUDCO", "base_price": 265, "step": 3.2, "freq": 1, "streak_at_end": 0},
    {"symbol": "RADICO", "base_price": 2250, "step": 25, "freq": 1, "streak_at_end": 1},
]

def generate_trading_days(end_date_str: str = "2026-11-04", count: int = 22):
    """Generate the last `count` trading business days (excluding weekends)."""
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    days = []
    curr = end_dt
    while len(days) < count:
        # 5 is Saturday, 6 is Sunday
        if curr.weekday() < 5:
            days.append(curr.strftime("%Y-%m-%d"))
        curr -= timedelta(days=1)
    return sorted(days)

def seed_sample_database(force: bool = False):
    """Seed the database with historical data if empty or forced."""
    init_db()
    trading_days = generate_trading_days("2026-11-04", 20) # 20 trading sessions (~1 month)
    
    # Check if database already has breakouts
    from database import get_connection
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM daily_breakouts")
        count = cursor.fetchone()[0]
        if count > 0 and not force:
            return False, f"Database already has {count} breakouts. Skipping seed."
            
    random.seed(42) # Consistent reproducible sample data
    
    # Register all stocks first
    for sym, meta in NSE_STOCKS_MASTER.items():
        upsert_stock(
            symbol=sym,
            company_name=meta["name"],
            series="EQ",
            sector=meta["sector"],
            industry=meta["industry"],
            market_cap_cr=meta["mcap"]
        )
        record_market_cap_snapshot(sym, trading_days[-1], meta["mcap"])

    inserted_total = 0
    daily_records_count = {d: 0 for d in trading_days}
    
    for item in POPULAR_BREAKOUT_STOCKS:
        sym = item["symbol"]
        meta = get_stock_metadata(sym)
        base_p = item["base_price"]
        step = item["step"]
        freq = item["freq"]
        streak_len = item.get("streak_at_end", 0)
        
        # Determine breakout dates for this stock
        selected_dates = []
        
        # If there's an ending streak, include the last `streak_len` days
        if streak_len > 0:
            selected_dates.extend(trading_days[-streak_len:])
            
        # Distribute remaining days across prior trading days
        remaining_needed = freq - len(selected_dates)
        prior_pool = [d for d in trading_days[:-streak_len if streak_len > 0 else len(trading_days)] if d not in selected_dates]
        
        if remaining_needed > 0 and prior_pool:
            sampled = random.sample(prior_pool, min(remaining_needed, len(prior_pool)))
            selected_dates.extend(sampled)
            
        selected_dates = sorted(list(set(selected_dates)))
        
        current_52w_high = base_p
        for i, b_date in enumerate(selected_dates):
            prev_high_date = selected_dates[i-1] if i > 0 else (datetime.strptime(b_date, "%Y-%m-%d") - timedelta(days=random.randint(15, 60))).strftime("%Y-%m-%d")
            prev_high = current_52w_high
            
            # Fresh high is incremented
            price_boost = step * (1 + random.uniform(0.1, 0.4))
            current_52w_high = round(prev_high + price_boost, 2)
            
            # LTP can be at the high or slightly pulled back
            if b_date == trading_days[-1]:
                # On the latest day, maybe a small pullback or right at high
                ltp = round(current_52w_high * random.uniform(0.97, 1.00), 2)
            else:
                ltp = round(current_52w_high * random.uniform(0.985, 1.00), 2)
                
            pct_chg = round(random.uniform(0.8, 6.5), 2)
            vol = random.randint(250000, 3500000)
            vol_ratio = round(random.uniform(1.2, 3.8), 2)
            
            rec = {
                "symbol": sym,
                "series": "EQ",
                "breakout_date": b_date,
                "ltp": ltp,
                "pct_change": pct_chg,
                "new_52w_high": current_52w_high,
                "prev_high": prev_high,
                "prev_high_date": prev_high_date,
                "volume": vol,
                "volume_ratio": vol_ratio,
                "source_file": f"52WeekHigh_{b_date}.csv"
            }
            if insert_breakout(rec):
                inserted_total += 1
                daily_records_count[b_date] += 1
                
    # Log the simulated ingestion history
    for d in trading_days:
        cnt = daily_records_count[d]
        log_ingestion(
            trading_date=d,
            source="NSE 52W High Report (EQ)",
            status="SUCCESS",
            total=cnt + random.randint(5, 12), # Total including SME/BE
            eq=cnt,
            inserted=cnt,
            duplicates=0,
            message=f"Ingested {cnt} mainboard EQ 52-week-high records."
        )
        
    return True, f"Successfully seeded {inserted_total} breakouts across {len(trading_days)} trading days (up to 2026-11-04)."

if __name__ == "__main__":
    success, msg = seed_sample_database(force=True)
    print(msg)
