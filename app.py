"""
HighTrack NSE - 52-Week High Intelligence Dashboard.
A comprehensive research and momentum tracking dashboard for NSE mainboard equities.
"""
import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date

import database
from collector import parse_and_ingest_csv, fetch_live_from_nse
from config import MCAP_TIERS
from sample_data import seed_sample_database

# Set page config
st.set_page_config(
    page_title="HighTrack NSE | 52-Week High Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished financial dashboard UI
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: #0e1117;
    }
    
    /* Metrics styling */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #10B981 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: #9CA3AF !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Table styling */
    .dataframe {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-size: 0.9rem !important;
    }
    
    /* Streak badge */
    .streak-badge {
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    
    /* Card-like boxes */
    .kpi-card {
        background-color: #1E222D;
        border: 1px solid #2A2E39;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        border-radius: 8px 8px 0px 0px;
        font-weight: 600;
        font-size: 0.95rem;
        padding: 0 18px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
database.init_db()

# Ensure we have data; if completely empty, seed sample data
with database.get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM daily_breakouts")
    if cur.fetchone()[0] == 0:
        seed_sample_database(force=False)

# Fetch all available trading dates
all_dates = database.get_distinct_trading_dates(series="ALL")
latest_available_date = all_dates[0] if all_dates else date.today().isoformat()
oldest_available_date = all_dates[-1] if all_dates else date.today().isoformat()

# ==============================================================================
# SIDEBAR FILTERS
# ==============================================================================
st.sidebar.image("https://img.icons8.com/fluency/96/bullish.png", width=64)
st.sidebar.title("HighTrack NSE")
st.sidebar.caption("52-Week High Intelligence & Momentum Screener")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Screening Filters")

# 1. Universe Selection (EQ vs ALL)
series_choice = st.sidebar.selectbox(
    "Equity Universe",
    options=["EQ Only (Mainboard Equity)", "EQ + BE", "All Series (EQ, BE, SM, ST)"],
    index=0,
    help="EQ represents regular mainboard equities. BE is trade-to-trade, SM is SME."
)
if "EQ Only" in series_choice:
    filter_series = "EQ"
elif "EQ + BE" in series_choice:
    filter_series = "EQ" # Can be extended
else:
    filter_series = "ALL"

# 2. Time Horizon / Lookback Period
timeframe = st.sidebar.selectbox(
    "Lookback Period",
    options=[
        "Past 30 Days (Recommended)",
        "Past 7 Days",
        "Past 15 Days",
        "Past 60 Days",
        "Past 90 Days",
        "All History",
        "Custom Date Range"
    ],
    index=0
)

# Determine start_date and end_date
if timeframe == "Past 7 Days":
    start_date = (pd.to_datetime(latest_available_date) - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = latest_available_date
elif timeframe == "Past 15 Days":
    start_date = (pd.to_datetime(latest_available_date) - timedelta(days=15)).strftime("%Y-%m-%d")
    end_date = latest_available_date
elif timeframe == "Past 30 Days (Recommended)":
    start_date = (pd.to_datetime(latest_available_date) - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = latest_available_date
elif timeframe == "Past 60 Days":
    start_date = (pd.to_datetime(latest_available_date) - timedelta(days=60)).strftime("%Y-%m-%d")
    end_date = latest_available_date
elif timeframe == "Past 90 Days":
    start_date = (pd.to_datetime(latest_available_date) - timedelta(days=90)).strftime("%Y-%m-%d")
    end_date = latest_available_date
elif timeframe == "All History":
    start_date = oldest_available_date
    end_date = latest_available_date
else: # Custom Date Range
    col_d1, col_d2 = st.sidebar.columns(2)
    with col_d1:
        s_val = st.date_input("From", value=pd.to_datetime(start_date if 'start_date' in locals() else oldest_available_date))
    with col_d2:
        e_val = st.date_input("To", value=pd.to_datetime(latest_available_date))
    start_date = s_val.strftime("%Y-%m-%d")
    end_date = e_val.strftime("%Y-%m-%d")

# 3. Market Cap Filter (INR Crore)
st.sidebar.markdown("---")
mcap_option = st.sidebar.selectbox(
    "Minimum Market Cap",
    options=list(MCAP_TIERS.keys()) + ["Custom Minimum..."],
    index=1, # Default: > ₹500 Cr (as user requested!)
    help="Filter stocks having a market cap above this threshold."
)

if mcap_option == "Custom Minimum...":
    min_mcap_val = st.sidebar.number_input("Min Market Cap (₹ Cr)", min_value=0, max_value=2000000, value=500, step=250)
else:
    min_mcap_val = MCAP_TIERS[mcap_option]

# 4. Breakout Days / Repeated Breakout Filter
min_breakouts = st.sidebar.slider(
    "Minimum Breakout Days",
    min_value=1,
    max_value=15,
    value=1,
    help="Select 2+ to see repeated high makers only."
)

# 5. Sector Filter
all_sectors = ["All"] + database.get_all_sectors()
selected_sector = st.sidebar.selectbox("Sector", options=all_sectors, index=0)

# 6. Streak Filter
active_streak_only = st.sidebar.checkbox("Active Streak Only (Hit high on latest date)", value=False)

# 7. Search box
search_query = st.sidebar.text_input("🔍 Search Symbol / Company", value="").strip().upper()

st.sidebar.markdown("---")
st.sidebar.caption(f"📅 Latest Data Date: **{latest_available_date}**")
st.sidebar.caption(f"🏛️ Universe: **{filter_series}**")

# ==============================================================================
# DATA QUERY
# ==============================================================================
df_leaderboard = database.get_leaderboard_data(
    start_date=start_date,
    end_date=end_date,
    series=filter_series,
    min_days=min_breakouts,
    min_mcap=min_mcap_val,
    sector=selected_sector if selected_sector != "All" else None
)

# Apply active streak filter if checked
if not df_leaderboard.empty and active_streak_only:
    df_leaderboard = df_leaderboard[df_leaderboard['current_streak'] > 0]

# Apply search filter if typed
if not df_leaderboard.empty and search_query:
    df_leaderboard = df_leaderboard[
        df_leaderboard['symbol'].str.contains(search_query, case=False, na=False) |
        df_leaderboard['company_name'].str.contains(search_query, case=False, na=False)
    ]

# ==============================================================================
# MAIN PAGE HEADER & STATS
# ==============================================================================
st.title("📈 HighTrack NSE: 52-Week High Intelligence")
st.markdown(
    f"Tracking **NSE Mainboard Equities** repeatedly printing fresh 52-week highs from **{start_date}** to **{end_date}**."
)

# Top KPI Summary Cards
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

total_unique_stocks = len(df_leaderboard) if not df_leaderboard.empty else 0
repeated_high_stocks = len(df_leaderboard[df_leaderboard['breakout_days'] >= 2]) if not df_leaderboard.empty else 0
active_streaks = len(df_leaderboard[df_leaderboard['current_streak'] >= 2]) if not df_leaderboard.empty else 0
mcap_above_500 = len(df_leaderboard[df_leaderboard['market_cap_cr'] >= 500]) if not df_leaderboard.empty else 0
total_events = df_leaderboard['breakout_days'].sum() if not df_leaderboard.empty else 0

with kpi1:
    st.metric("Unique High Makers", f"{total_unique_stocks}")
with kpi2:
    st.metric("Repeated Highs (≥2D)", f"{repeated_high_stocks}", help="Stocks that appeared on 2 or more distinct trading sessions")
with kpi3:
    st.metric("Active Streaks (≥2D)", f"{active_streaks}", help="Stocks hitting fresh highs on 2+ consecutive sessions ending on the latest date")
with kpi4:
    st.metric("Total Breakout Events", f"{total_events}")
with kpi5:
    st.metric("Mcap ≥ ₹500 Cr", f"{mcap_above_500}")

st.markdown("---")

# ==============================================================================
# DASHBOARD TABS
# ==============================================================================
tab_leaderboard, tab_stock, tab_sector, tab_breadth, tab_health = st.tabs([
    "🏆 Breakout Leaderboard",
    "🔍 Stock Deep-Dive",
    "🏭 Sector Analysis",
    "📊 Market Breadth & Trends",
    "⚙️ Data Ingestion & Health"
])

# ------------------------------------------------------------------------------
# TAB 1: BREAKOUT LEADERBOARD
# ------------------------------------------------------------------------------
with tab_leaderboard:
    st.subheader(f"Leaderboard: Ranked by 52-Week High Breakout Frequency ({timeframe})")
    
    if df_leaderboard.empty:
        st.warning("⚠️ No stocks match the current filter criteria. Try relaxing the market cap, minimum breakout days, or date range filters.")
    else:
        # Format columns for human display
        display_df = df_leaderboard.copy()
        
        # Add visual streak indicators
        def format_streak(val):
            if val >= 4:
                return f"🔥 {val} Days"
            elif val >= 2:
                return f"⚡ {val} Days"
            elif val == 1:
                return "1 Day"
            return "-"
            
        display_df['Streak'] = display_df['current_streak'].apply(format_streak)
        display_df['Max Streak'] = display_df['max_streak'].apply(lambda x: f"{x} Days" if x > 0 else "-")
        display_df['Market Cap'] = display_df['market_cap_cr'].apply(lambda x: f"₹{x:,.0f} Cr")
        display_df['LTP (₹)'] = display_df['latest_ltp'].apply(lambda x: f"₹{x:,.2f}")
        display_df['52W High (₹)'] = display_df['highest_52w_high'].apply(lambda x: f"₹{x:,.2f}")
        display_df['Drawdown'] = display_df['drawdown_pct'].apply(lambda x: f"{x:+.1f}%")
        display_df['Day Change'] = display_df['latest_pct_change'].apply(lambda x: f"{x:+.2f}%")
        display_df['Vol Ratio'] = display_df['volume_ratio'].apply(lambda x: f"{x:.1f}x")
        
        columns_to_show = [
            'symbol', 'company_name', 'sector', 'Market Cap',
            'breakout_days', 'Streak', 'Max Streak',
            'LTP (₹)', '52W High (₹)', 'Drawdown', 'Day Change', 'Vol Ratio',
            'breakout_dates_str'
        ]
        
        rename_map = {
            'symbol': 'Symbol',
            'company_name': 'Company',
            'sector': 'Sector',
            'breakout_days': 'High Days',
            'breakout_dates_str': 'Breakout Dates'
        }
        
        table_df = display_df[columns_to_show].rename(columns=rename_map)
        
        # Display Streamlit DataFrame with custom column configs
        st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Symbol": st.column_config.TextColumn(help="NSE Symbol"),
                "High Days": st.column_config.ProgressColumn(
                    help="Number of days stock hit 52-week high in period",
                    format="%d",
                    min_value=0,
                    max_value=int(df_leaderboard['breakout_days'].max())
                ),
                "Breakout Dates": st.column_config.TextColumn(
                    help="All dates on which the company printed a new 52-week high",
                    width="large"
                ),
                "Drawdown": st.column_config.TextColumn(
                    help="% change between latest price and highest 52W high recorded"
                )
            }
        )
        
        # Export Actions
        col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 4])
        with col_exp1:
            csv_data = df_leaderboard.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name=f"hightrack_nse_{start_date}_to_{end_date}.csv",
                mime="text/csv"
            )
        with col_exp2:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_leaderboard.to_excel(writer, index=False, sheet_name='52W_High_Leaderboard')
            excel_data = output.getvalue()
            st.download_button(
                label="📊 Download Excel",
                data=excel_data,
                file_name=f"hightrack_nse_{start_date}_to_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ------------------------------------------------------------------------------
# TAB 2: INDIVIDUAL STOCK DEEP-DIVE
# ------------------------------------------------------------------------------
with tab_stock:
    st.subheader("🔍 Stock Analysis & Historical Breakout Activity")
    
    # Stock picker
    available_symbols = df_leaderboard['symbol'].tolist() if not df_leaderboard.empty else []
    if not available_symbols:
        with database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT symbol FROM daily_breakouts ORDER BY symbol ASC")
            available_symbols = [r[0] for r in cur.fetchall()]
            
    if available_symbols:
        selected_stock = st.selectbox(
            "Select Stock for Deep Dive",
            options=available_symbols,
            index=0,
            help="Choose a stock to inspect its complete breakout dates, price progression, and streaks."
        )
        
        stock_data = database.get_stock_details(selected_stock)
        info = stock_data["stock"]
        breakouts = stock_data["breakouts"]
        
        # Stock Summary Cards
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        
        with sc1:
            st.metric("Symbol", info.get("symbol", selected_stock))
            st.caption(info.get("company_name", ""))
        with sc2:
            st.metric("Sector", info.get("sector", "General"))
            st.caption(f"Industry: {info.get('industry', 'N/A')}")
        with sc3:
            st.metric("Market Cap", f"₹{info.get('market_cap_cr', 0):,.0f} Cr")
            st.caption("NSE EQ Universe")
        with sc4:
            total_b = len(breakouts)
            st.metric("Total 52W High Days", f"{total_b}")
            st.caption("In Database History")
        with sc5:
            if not breakouts.empty:
                max_high = breakouts['new_52w_high'].max()
                latest_ltp = breakouts.iloc[-1]['ltp']
                dd = ((latest_ltp - max_high) / max_high) * 100
                st.metric("Current Drawdown", f"{dd:.1f}%")
                st.caption(f"Peak: ₹{max_high:,.2f} | LTP: ₹{latest_ltp:,.2f}")
            else:
                st.metric("Current Drawdown", "0.0%")
                
        st.markdown("---")
        
        if not breakouts.empty:
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.markdown("##### 📈 52-Week High Price Progression")
                fig_prog = go.Figure()
                fig_prog.add_trace(go.Scatter(
                    x=breakouts['breakout_date'],
                    y=breakouts['new_52w_high'],
                    mode='lines+markers',
                    name='New 52W High Price',
                    line=dict(color='#10B981', width=3),
                    marker=dict(size=8)
                ))
                fig_prog.add_trace(go.Scatter(
                    x=breakouts['breakout_date'],
                    y=breakouts['ltp'],
                    mode='lines+markers',
                    name='Session LTP',
                    line=dict(color='#3B82F6', width=2, dash='dot'),
                    marker=dict(size=6)
                ))
                fig_prog.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis_title="Breakout Date",
                    yaxis_title="Price (₹)",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_prog, use_container_width=True)
                
            with col_chart2:
                st.markdown("##### 🚀 Daily % Change on Breakout Sessions")
                fig_bar = px.bar(
                    breakouts,
                    x='breakout_date',
                    y='pct_change',
                    color='pct_change',
                    color_continuous_scale='Mint',
                    labels={'breakout_date': 'Date', 'pct_change': '% Change'},
                    template="plotly_dark"
                )
                fig_bar.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
            st.markdown("##### 📅 Detailed Breakout History Log")
            st.dataframe(
                breakouts[[
                    'breakout_date', 'ltp', 'new_52w_high', 'prev_high',
                    'prev_high_date', 'pct_change', 'volume_ratio', 'source_file'
                ]].sort_values('breakout_date', ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "breakout_date": "Breakout Date",
                    "ltp": st.column_config.NumberColumn("LTP (₹)", format="₹%.2f"),
                    "new_52w_high": st.column_config.NumberColumn("New 52W High (₹)", format="₹%.2f"),
                    "prev_high": st.column_config.NumberColumn("Previous High (₹)", format="₹%.2f"),
                    "prev_high_date": "Previous High Date",
                    "pct_change": st.column_config.NumberColumn("Daily % Change", format="%.2f%%"),
                    "volume_ratio": st.column_config.NumberColumn("Volume Confirmation", format="%.1fx")
                }
            )
        else:
            st.info("No breakout records found for this symbol.")
    else:
        st.info("No stock data available.")

# ------------------------------------------------------------------------------
# TAB 3: SECTOR ANALYSIS
# ------------------------------------------------------------------------------
with tab_sector:
    st.subheader("🏭 Sector-wise Momentum & Breakout Breadth")
    
    if not df_leaderboard.empty:
        # Group by sector
        sector_summary = df_leaderboard.groupby('sector').agg(
            total_breakout_events=('breakout_days', 'sum'),
            unique_stocks=('symbol', 'count'),
            avg_mcap=('market_cap_cr', 'mean'),
            leaders=('symbol', lambda x: ", ".join(list(x)[:3]))
        ).reset_index().sort_values(by=['total_breakout_events', 'unique_stocks'], ascending=[False, False])
        
        col_sec1, col_sec2 = st.columns([3, 2])
        
        with col_sec1:
            st.markdown("##### 🌐 Breakout Share by Sector")
            fig_sec = px.treemap(
                df_leaderboard,
                path=['sector', 'symbol'],
                values='breakout_days',
                color='breakout_days',
                color_continuous_scale='Viridis',
                title="Sector & Stock Breakdown by 52W High Frequency",
                template="plotly_dark"
            )
            fig_sec.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_sec, use_container_width=True)
            
        with col_sec2:
            st.markdown("##### 📊 Top Sectors by Total Breakout Events")
            fig_bar_sec = px.bar(
                sector_summary.head(10),
                x='total_breakout_events',
                y='sector',
                orientation='h',
                color='total_breakout_events',
                color_continuous_scale='Teal',
                template="plotly_dark"
            )
            fig_bar_sec.update_layout(
                yaxis=dict(autorange="reversed"),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                coloraxis_showscale=False,
                xaxis_title="Breakout Days",
                yaxis_title=""
            )
            st.plotly_chart(fig_bar_sec, use_container_width=True)
            
        st.markdown("##### 📋 Sector Breakdown Leaderboard")
        sector_display = sector_summary.rename(columns={
            'sector': 'Sector',
            'total_breakout_events': 'Total Breakout Events',
            'unique_stocks': 'Unique High Makers',
            'avg_mcap': 'Average Mcap (₹ Cr)',
            'leaders': 'Top Momentum Leaders'
        })
        sector_display['Average Mcap (₹ Cr)'] = sector_display['Average Mcap (₹ Cr)'].apply(lambda x: f"₹{x:,.0f} Cr")
        st.dataframe(sector_display, use_container_width=True, hide_index=True)
    else:
        st.info("No data available for sector analysis.")

# ------------------------------------------------------------------------------
# TAB 4: MARKET BREADTH & DAILY TRENDS
# ------------------------------------------------------------------------------
with tab_breadth:
    st.subheader("📊 Market Breadth & Daily 52-Week High Trends")
    
    with database.get_connection() as conn:
        trend_query = """
            SELECT breakout_date, COUNT(DISTINCT symbol) as high_count
            FROM daily_breakouts
            WHERE series = 'EQ'
            GROUP BY breakout_date
            ORDER BY breakout_date ASC
        """
        trend_df = pd.read_sql_query(trend_query, conn)
        
    if not trend_df.empty:
        col_t1, col_t2 = st.columns([3, 2])
        
        with col_t1:
            st.markdown("##### 📈 Daily Count of Mainboard Stocks Hitting 52-Week High")
            fig_trend = px.area(
                trend_df,
                x='breakout_date',
                y='high_count',
                markers=True,
                labels={'breakout_date': 'Trading Session', 'high_count': 'Stocks at 52W High'},
                template="plotly_dark"
            )
            fig_trend.update_traces(line_color='#10B981', fillcolor='rgba(16, 185, 129, 0.2)')
            fig_trend.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Date",
                yaxis_title="Number of Stocks"
            )
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with col_t2:
            st.markdown("##### 🍰 Market Cap Classification of High Makers")
            if not df_leaderboard.empty:
                def categorize_mcap(val):
                    if val >= 20000:
                        return "Large Cap (> ₹20k Cr)"
                    elif val >= 5000:
                        return "Mid Cap (₹5k - ₹20k Cr)"
                    elif val >= 500:
                        return "Small Cap (₹500 - ₹5k Cr)"
                    else:
                        return "Micro Cap (< ₹500 Cr)"
                        
                cat_counts = df_leaderboard['market_cap_cr'].apply(categorize_mcap).value_counts().reset_index()
                cat_counts.columns = ['Category', 'Count']
                
                fig_pie = px.pie(
                    cat_counts,
                    names='Category',
                    values='Count',
                    hole=0.45,
                    color_discrete_sequence=px.colors.sequential.Teal,
                    template="plotly_dark"
                )
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pie, use_container_width=True)
                
        # Consecutive streaks distribution
        if not df_leaderboard.empty:
            st.markdown("##### 🔥 Streak Distribution (Consecutive Sessions at Highs)")
            fig_hist = px.histogram(
                df_leaderboard,
                x='max_streak',
                nbins=10,
                color_discrete_sequence=['#FF6B6B'],
                labels={'max_streak': 'Max Consecutive Breakout Days'},
                template="plotly_dark"
            )
            fig_hist.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis_title="Stock Count"
            )
            st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("No trend data available.")

# ------------------------------------------------------------------------------
# TAB 5: DATA INGESTION & SYSTEM HEALTH
# ------------------------------------------------------------------------------
with tab_health:
    st.subheader("⚙️ Data Ingestion, Collection & Health Audit")
    
    col_ing1, col_ing2 = st.columns(2)
    
    # Section A: Manual CSV Upload
    with col_ing1:
        st.markdown("### 📤 Upload Downloaded NSE CSV")
        st.write("Upload the `52WeekHigh.csv` directly from your downloads folder.")
        
        uploaded_file = st.file_uploader(
            "Choose 52WeekHigh.csv file",
            type=["csv"],
            help="Drop the CSV downloaded from nseindia.com/market-data/52-week-high-equity-market"
        )
        
        upload_date = st.date_input(
            "Trading / Snapshot Date for this CSV",
            value=date.today(),
            help="Specify the date on which this CSV was downloaded (defaults to today)."
        )
        
        if st.button("Process & Ingest CSV", type="primary"):
            if uploaded_file is not None:
                with st.spinner("Parsing and storing records..."):
                    res = parse_and_ingest_csv(
                        source_input=uploaded_file.getvalue(),
                        snapshot_date=upload_date.strftime("%Y-%m-%d"),
                        source_label=f"Manual Upload: {uploaded_file.name}",
                        filter_series_eq=False
                    )
                    if res["success"]:
                        st.success(f"✅ {res['message']}")
                        st.rerun()
                    else:
                        st.error(f"❌ {res['message']}")
            else:
                st.warning("Please select a CSV file first.")
                
    # Section B: Automated Fetch from NSE
    with col_ing2:
        st.markdown("### 🌐 Automated Fetch from NSE Live")
        st.write("Trigger automated download directly from the official NSE India server.")
        
        fetch_date = st.date_input(
            "Fetch Snapshot Date",
            value=date.today(),
            key="fetch_date_input"
        )
        
        if st.button("⚡ Fetch Today's Highs from NSE"):
            with st.spinner("Connecting to NSE, fetching cookies, and downloading 52-week-high report..."):
                res = fetch_live_from_nse(snapshot_date=fetch_date.strftime("%Y-%m-%d"))
                if res["success"]:
                    st.success(f"✅ {res['message']}")
                    st.rerun()
                else:
                    st.warning(f"⚠️ {res['message']}")
                    st.info("Tip: If NSE blocks automated cloud requests, simply download the CSV via your browser and upload it using the left panel.")

    st.markdown("---")
    
    # Audit Logs
    st.markdown("### 📋 Ingestion Logs & System Audit")
    logs_df = database.get_ingestion_logs(limit=25)
    if not logs_df.empty:
        st.dataframe(
            logs_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "timestamp": "Timestamp",
                "trading_date": "Trading Date",
                "source": "Source",
                "status": "Status",
                "total_records": "Total Rows",
                "eq_records": "EQ Rows",
                "inserted_records": "Inserted",
                "duplicate_records": "Duplicates",
                "message": "Audit Log Message"
            }
        )
    else:
        st.info("No ingestion logs available.")
        
    st.markdown("---")
    col_reset1, col_reset2 = st.columns([1, 3])
    with col_reset1:
        if st.button("🔄 Reset / Re-seed Sample Data"):
            seed_sample_database(force=True)
            st.success("Sample database reset successfully!")
            st.rerun()
