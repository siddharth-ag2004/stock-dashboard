"""
NSE Stock Universe Master Data & Enrichment.
Contains sectors, industries, and market cap classifications for major NSE EQ stocks,
with dynamic updater support.
"""
from typing import Dict, Any, Optional

# Comprehensive master data for prominent NSE mainboard equities (EQ series)
# Market caps in ₹ Crore (approximate benchmark values for filtering)
NSE_STOCKS_MASTER: Dict[str, Dict[str, Any]] = {
    "RELIANCE": {"name": "Reliance Industries Ltd", "sector": "Energy & Petrochemicals", "industry": "Refineries", "mcap": 1980000},
    "TCS": {"name": "Tata Consultancy Services Ltd", "sector": "Information Technology", "industry": "IT Services", "mcap": 1420000},
    "HDFCBANK": {"name": "HDFC Bank Ltd", "sector": "Financial Services", "industry": "Private Banks", "mcap": 1310000},
    "BHARTIARTL": {"name": "Bharti Airtel Ltd", "sector": "Telecommunications", "industry": "Telecom Services", "mcap": 950000},
    "ICICIBANK": {"name": "ICICI Bank Ltd", "sector": "Financial Services", "industry": "Private Banks", "mcap": 890000},
    "INFY": {"name": "Infosys Ltd", "sector": "Information Technology", "industry": "IT Services", "mcap": 760000},
    "SBIN": {"name": "State Bank of India", "sector": "Financial Services", "industry": "PSU Banks", "mcap": 720000},
    "LICI": {"name": "Life Insurance Corp of India", "sector": "Financial Services", "industry": "Life Insurance", "mcap": 610000},
    "ITC": {"name": "ITC Ltd", "sector": "FMCG", "industry": "Tobacco & Diversified", "mcap": 590000},
    "HINDUNILVR": {"name": "Hindustan Unilever Ltd", "sector": "FMCG", "industry": "Household Products", "mcap": 560000},
    "LT": {"name": "Larsen & Toubro Ltd", "sector": "Capital Goods", "industry": "Infrastructure & Engineering", "mcap": 480000},
    "BAJFINANCE": {"name": "Bajaj Finance Ltd", "sector": "Financial Services", "industry": "NBFC", "mcap": 430000},
    "HCLTECH": {"name": "HCL Technologies Ltd", "sector": "Information Technology", "industry": "IT Services", "mcap": 450000},
    "M&M": {"name": "Mahindra & Mahindra Ltd", "sector": "Automobiles", "industry": "Auto - Commercial & Passenger", "mcap": 360000},
    "SUNPHARMA": {"name": "Sun Pharmaceutical Industries", "sector": "Healthcare & Pharma", "industry": "Pharmaceuticals", "mcap": 410000},
    "TATAMOTORS": {"name": "Tata Motors Ltd", "sector": "Automobiles", "industry": "Auto - Passenger & EV", "mcap": 340000},
    "NTPC": {"name": "NTPC Ltd", "sector": "Power & Utilities", "industry": "Thermal Power", "mcap": 380000},
    "ONGC": {"name": "Oil & Natural Gas Corp Ltd", "sector": "Energy & Petrochemicals", "industry": "Oil Exploration", "mcap": 320000},
    "KOTAKBANK": {"name": "Kotak Mahindra Bank Ltd", "sector": "Financial Services", "industry": "Private Banks", "mcap": 350000},
    "TITAN": {"name": "Titan Company Ltd", "sector": "Consumer Durables", "industry": "Gems, Jewellery & Watches", "mcap": 305000},
    "ADANIENT": {"name": "Adani Enterprises Ltd", "sector": "Metals & Mining", "industry": "Trading & Mining", "mcap": 320000},
    "POWERGRID": {"name": "Power Grid Corporation of India", "sector": "Power & Utilities", "industry": "Power Transmission", "mcap": 310000},
    "AXISBANK": {"name": "Axis Bank Ltd", "sector": "Financial Services", "industry": "Private Banks", "mcap": 345000},
    "TRENT": {"name": "Trent Ltd", "sector": "Consumer Services", "industry": "Retail - Apparels", "mcap": 255000},
    "BEL": {"name": "Bharat Electronics Ltd", "sector": "Capital Goods", "industry": "Defense Electronics", "mcap": 215000},
    "HAL": {"name": "Hindustan Aeronautics Ltd", "sector": "Capital Goods", "industry": "Aerospace & Defense", "mcap": 280000},
    "DIXON": {"name": "Dixon Technologies (India) Ltd", "sector": "Consumer Durables", "industry": "Electronics Manufacturing", "mcap": 88000},
    "POLYCAB": {"name": "Polycab India Ltd", "sector": "Capital Goods", "industry": "Cables & Wires", "mcap": 98000},
    "BHARATFORG": {"name": "Bharat Forge Ltd", "sector": "Automobiles", "industry": "Auto Ancillaries & Defense", "mcap": 62000},
    "COCHINSHIP": {"name": "Cochin Shipyard Ltd", "sector": "Capital Goods", "industry": "Shipbuilding & Marine", "mcap": 48000},
    "PERSISTENT": {"name": "Persistent Systems Ltd", "sector": "Information Technology", "industry": "Digital IT Services", "mcap": 82000},
    "ANANDRATHI": {"name": "Anand Rathi Wealth Ltd", "sector": "Financial Services", "industry": "Wealth Management", "mcap": 18200},
    "ALIVUS": {"name": "Alivus Life Sciences Ltd", "sector": "Healthcare & Pharma", "industry": "Specialty Biotech", "mcap": 4200},
    "ALGOQUANT": {"name": "Algoquant Fintech Ltd", "sector": "Financial Services", "industry": "Fintech & Algorithmic", "mcap": 950},
    "MOTHERSON": {"name": "Samvardhana Motherson International", "sector": "Automobiles", "industry": "Auto Components", "mcap": 125000},
    "MAZDOCK": {"name": "Mazagon Dock Shipbuilders Ltd", "sector": "Capital Goods", "industry": "Defense Shipbuilding", "mcap": 86000},
    "BEML": {"name": "BEML Ltd", "sector": "Capital Goods", "industry": "Rail & Heavy Machinery", "mcap": 18500},
    "KAYNES": {"name": "Kaynes Technology India Ltd", "sector": "Consumer Durables", "industry": "Electronics Systems", "mcap": 34000},
    "CGPOWER": {"name": "CG Power and Industrial Solutions", "sector": "Capital Goods", "industry": "Electrical Equipment", "mcap": 115000},
    "SUZLON": {"name": "Suzlon Energy Ltd", "sector": "Power & Utilities", "industry": "Wind Energy", "mcap": 88000},
    "PRESTIGE": {"name": "Prestige Estates Projects Ltd", "sector": "Real Estate", "industry": "Residential & Commercial", "mcap": 71000},
    "DLF": {"name": "DLF Ltd", "sector": "Real Estate", "industry": "Real Estate Development", "mcap": 210000},
    "ZOMATO": {"name": "Zomato Ltd", "sector": "Consumer Services", "industry": "Food Delivery & Quick Commerce", "mcap": 240000},
    "SWIGGY": {"name": "Swiggy Ltd", "sector": "Consumer Services", "industry": "Quick Commerce", "mcap": 110000},
    "KPITTECH": {"name": "KPIT Technologies Ltd", "sector": "Information Technology", "industry": "Automotive Software", "mcap": 46000},
    "COFORGE": {"name": "Coforge Ltd", "sector": "Information Technology", "industry": "IT Solutions", "mcap": 52000},
    "MAXHEALTH": {"name": "Max Healthcare Institute Ltd", "sector": "Healthcare & Pharma", "industry": "Hospitals & Diagnostics", "mcap": 102000},
    "FORTIS": {"name": "Fortis Healthcare Ltd", "sector": "Healthcare & Pharma", "industry": "Hospitals", "mcap": 48000},
    "VOLTAS": {"name": "Voltas Ltd", "sector": "Consumer Durables", "industry": "Air Conditioning", "mcap": 58000},
    "BLUESTARCO": {"name": "Blue Star Ltd", "sector": "Consumer Durables", "industry": "Cooling Systems", "mcap": 38000},
    "CHAMBLFERT": {"name": "Chambal Fertilisers & Chemicals", "sector": "Chemicals & Fertilisers", "industry": "Agrochemicals", "mcap": 21000},
    "DEEPAKNTR": {"name": "Deepak Nitrite Ltd", "sector": "Chemicals & Fertilisers", "industry": "Specialty Chemicals", "mcap": 38000},
    "PIIND": {"name": "PI Industries Ltd", "sector": "Chemicals & Fertilisers", "industry": "Agro Sciences", "mcap": 64000},
    "AUROPHARMA": {"name": "Aurobindo Pharma Ltd", "sector": "Healthcare & Pharma", "industry": "Generic Formulations", "mcap": 82000},
    "LUPIN": {"name": "Lupin Ltd", "sector": "Healthcare & Pharma", "industry": "Formulations & Active Pharma", "mcap": 95000},
    "GLENMARK": {"name": "Glenmark Pharmaceuticals Ltd", "sector": "Healthcare & Pharma", "industry": "Specialty Pharma", "mcap": 46000},
    "TORNTPOWER": {"name": "Torrent Power Ltd", "sector": "Power & Utilities", "industry": "Power Generation & Distribution", "mcap": 82000},
    "JSWENERGY": {"name": "JSW Energy Ltd", "sector": "Power & Utilities", "industry": "Thermal & Renewables", "mcap": 118000},
    "HUDCO": {"name": "Housing & Urban Development Corp", "sector": "Financial Services", "industry": "Housing Finance", "mcap": 49000},
    "IREDA": {"name": "Indian Renewable Energy Development", "sector": "Financial Services", "industry": "Renewable Financing", "mcap": 58000},
    "PFC": {"name": "Power Finance Corporation", "sector": "Financial Services", "industry": "Infrastructure Finance", "mcap": 155000},
    "RECLTD": {"name": "REC Ltd", "sector": "Financial Services", "industry": "Power Infrastructure Finance", "mcap": 142000},
    "FEDERALBNK": {"name": "The Federal Bank Ltd", "sector": "Financial Services", "industry": "Private Banks", "mcap": 48000},
    "IDFCFIRSTB": {"name": "IDFC First Bank Ltd", "sector": "Financial Services", "industry": "Private Banks", "mcap": 52000},
    "MOTILALOFS": {"name": "Motilal Oswal Financial Services", "sector": "Financial Services", "industry": "Broking & Wealth", "mcap": 42000},
    "ANGELONE": {"name": "Angel One Ltd", "sector": "Financial Services", "industry": "Digital Brokerage", "mcap": 26000},
    "KIMS": {"name": "Krishna Institute of Medical Sciences", "sector": "Healthcare & Pharma", "industry": "Hospitals", "mcap": 23500},
    "MEDANTA": {"name": "Global Health Ltd (Medanta)", "sector": "Healthcare & Pharma", "industry": "Hospitals", "mcap": 31000},
    "APARINDS": {"name": "Apar Industries Ltd", "sector": "Capital Goods", "industry": "Conductors & Specialty Oils", "mcap": 39000},
    "KEI": {"name": "KEI Industries Ltd", "sector": "Capital Goods", "industry": "Cables & Wires", "mcap": 39500},
    "EXIDEIND": {"name": "Exide Industries Ltd", "sector": "Automobiles", "industry": "Storage Batteries", "mcap": 38000},
    "AMARAJABAT": {"name": "Amara Raja Energy & Mobility", "sector": "Automobiles", "industry": "Batteries & EV Cell Tech", "mcap": 24000},
    "RADICO": {"name": "Radico Khaitan Ltd", "sector": "FMCG", "industry": "Distilleries & Beverages", "mcap": 31000},
    "VBL": {"name": "Varun Beverages Ltd", "sector": "FMCG", "industry": "Beverages Bottling", "mcap": 195000},
    "TATACONSUM": {"name": "Tata Consumer Products Ltd", "sector": "FMCG", "industry": "Packaged Foods & Tea", "mcap": 115000},
    "GODREJPROP": {"name": "Godrej Properties Ltd", "sector": "Real Estate", "industry": "Residential Real Estate", "mcap": 82000},
    "OBEROIRLTY": {"name": "Oberoi Realty Ltd", "sector": "Real Estate", "industry": "Luxury Real Estate", "mcap": 68000},
    "PHOENIXLTD": {"name": "The Phoenix Mills Ltd", "sector": "Real Estate", "industry": "Retail Malls & Mixed Use", "mcap": 59000},
    "BRIGADE": {"name": "Brigade Enterprises Ltd", "sector": "Real Estate", "industry": "Real Estate Development", "mcap": 28000},
    "SOBHA": {"name": "Sobha Ltd", "sector": "Real Estate", "industry": "Residential Real Estate", "mcap": 18000},
    "GRASIM": {"name": "Grasim Industries Ltd", "sector": "Metals & Mining", "industry": "Diversified & Paints", "mcap": 175000},
    "JSWSTEEL": {"name": "JSW Steel Ltd", "sector": "Metals & Mining", "industry": "Steel Manufacturing", "mcap": 240000},
    "TATASTEEL": {"name": "Tata Steel Ltd", "sector": "Metals & Mining", "industry": "Steel Manufacturing", "mcap": 190000},
    "HINDALCO": {"name": "Hindalco Industries Ltd", "sector": "Metals & Mining", "industry": "Aluminium & Copper", "mcap": 160000},
    "VEDL": {"name": "Vedanta Ltd", "sector": "Metals & Mining", "industry": "Diversified Natural Resources", "mcap": 185000},
    "JINDALSTEL": {"name": "Jindal Steel & Power Ltd", "sector": "Metals & Mining", "industry": "Steel & Pellets", "mcap": 98000},
    "NATIONALUM": {"name": "National Aluminium Co Ltd", "sector": "Metals & Mining", "industry": "Aluminium", "mcap": 42000},
    "HINDPETRO": {"name": "Hindustan Petroleum Corp Ltd", "sector": "Energy & Petrochemicals", "industry": "Refineries & Marketing", "mcap": 84000},
    "BPCL": {"name": "Bharat Petroleum Corp Ltd", "sector": "Energy & Petrochemicals", "industry": "Refineries & Marketing", "mcap": 138000},
    "IOC": {"name": "Indian Oil Corporation Ltd", "sector": "Energy & Petrochemicals", "industry": "Refineries & Pipelines", "mcap": 210000},
    "GAIL": {"name": "GAIL (India) Ltd", "sector": "Energy & Petrochemicals", "industry": "Natural Gas Transmission", "mcap": 140000},
    "PETRONET": {"name": "Petronet LNG Ltd", "sector": "Energy & Petrochemicals", "industry": "LNG Terminal Operator", "mcap": 46000},
    "OIL": {"name": "Oil India Ltd", "sector": "Energy & Petrochemicals", "industry": "Upstream Oil Exploration", "mcap": 64000},
    "INDHOTEL": {"name": "The Indian Hotels Co Ltd (Taj)", "sector": "Consumer Services", "industry": "Hotels & Resorts", "mcap": 98000},
    "EIHOTEL": {"name": "EIH Ltd (Oberoi Hotels)", "sector": "Consumer Services", "industry": "Hotels & Hospitality", "mcap": 26000},
    "CHALET": {"name": "Chalet Hotels Ltd", "sector": "Consumer Services", "industry": "Hospitality & Commercial", "mcap": 18500},
    "LEMONONTREE": {"name": "Lemon Tree Hotels Ltd", "sector": "Consumer Services", "industry": "Mid-priced Hotels", "mcap": 12000},
}

def get_stock_metadata(symbol: str) -> Dict[str, Any]:
    """Retrieve metadata for a symbol, providing smart fallbacks."""
    sym = symbol.strip().upper()
    if sym in NSE_STOCKS_MASTER:
        meta = NSE_STOCKS_MASTER[sym]
        return {
            "symbol": sym,
            "company_name": meta.get("name", sym),
            "sector": meta.get("sector", "Other Equities"),
            "industry": meta.get("industry", "General"),
            "market_cap_cr": float(meta.get("mcap", 1500.0))
        }
    
    # Generic fallback based on symbol name
    return {
        "symbol": sym,
        "company_name": sym,
        "sector": "Other Equities",
        "industry": "General",
        "market_cap_cr": 1250.0 # Default conservative fallback
    }

def update_live_market_cap(symbol: str) -> Optional[float]:
    """
    Attempt to fetch real-time market cap using Yahoo Finance ticker SYMBOL.NS.
    Fails gracefully if offline or blocked.
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol.strip().upper()}.NS")
        info = ticker.fast_info
        if hasattr(info, 'market_cap') and info.market_cap:
            # Convert INR to Crore (1 Crore = 10,000,000)
            mcap_cr = round(info.market_cap / 1e7, 2)
            return mcap_cr
    except Exception:
        pass
    return None
