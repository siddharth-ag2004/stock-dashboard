"""
HighTrack NSE - 52-Week High Intelligence Dashboard.
A research and momentum tracking dashboard for NSE mainboard equities.
"""
import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date

import database
from collector import parse_and_ingest_csv, fetch_live_from_nse, fetch_from_mtf_pr, backfill_real_history
from config import MCAP_TIERS
from sample_data import seed_sample_database

# Page config
st.set_page_config(
    page_title="HighTrack NSE | 52-Week High Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark financial UI
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
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
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 46px;
        white-space: pre-wrap;
        border-radius: 6px 6px 0px 0px;
        font-weight: 600;
        font-size: 0.95rem;
        padding: 0 18px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
database.init_db()

# Check data; if completely empty, seed sample database
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
st.sidebar.title("HighTrack NSE")
st.sidebar.caption("52-Week High Momentum Screener")

st.sidebar.markdown("---")
st.sidebar.subheader("Screening Filters")

# 1. Universe Selection
series_choice = st.sidebar.selectbox(
    "Equity Universe",
    options=["EQ Only (Mainboard Equity)", "EQ + BE", "All Series (EQ, BE, SM, ST)"],
    index=0,
    help="EQ represents regular mainboard equities. BE is trade-to-trade, SM is SME."
)
if "EQ Only" in series_choice:
    filter_series = "EQ"
elif "EQ + BE" in series_choice:
    filter_series = "EQ"
else:
    filter_series = "ALL"

# 2. Lookback Period
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
else:
    col_d1, col_d2 = st.sidebar.columns(2)
    with col_d1:
        s_val = st.date_input("From", value=pd.to_datetime(oldest_available_date))
    with col_d2:
        e_val = st.date_input("To", value=pd.to_datetime(latest_available_date))
    start_date = s_val.strftime("%Y-%m-%d")
    end_date = e_val.strftime("%Y-%m-%d")

# 3. Market Cap Filter
st.sidebar.markdown("---")
mcap_option = st.sidebar.selectbox(
    "Minimum Market Cap",
    options=list(MCAP_TIERS.keys()) + ["Custom Minimum..."],
    index=1, # Default: > 500 Cr
    help="Filter stocks having a market cap above this threshold."
)

if mcap_option == "Custom Minimum...":
    min_mcap_val = st.sidebar.number_input("Min Market Cap (Cr)", min_value=0, max_value=2000000, value=500, step=250)
else:
    min_mcap_val = MCAP_TIERS[mcap_option]

# 4. Breakout Days Slider
min_breakouts = st.sidebar.slider(
    "Minimum Breakout Days",
    min_value=1,
    max_value=15,
    value=1,
    help="Select 2+ to see repeated high makers only."
)

# 5. Streak Filter
active_streak_only = st.sidebar.checkbox("Active Streak Only (Hit high on latest date)", value=False)

# 6. Search
search_query = st.sidebar.text_input("Search Symbol / Company", value="").strip().upper()

st.sidebar.markdown("---")
st.sidebar.caption(f"Latest Available Date: **{latest_available_date}**")
st.sidebar.caption(f"Universe: **{filter_series}**")

# ==============================================================================
# DATA QUERY
# ==============================================================================
df_leaderboard = database.get_leaderboard_data(
    start_date=start_date,
    end_date=end_date,
    series=filter_series,
    min_days=min_breakouts,
    min_mcap=min_mcap_val,
    sector=None # Excluded sector filtering
)

if not df_leaderboard.empty and active_streak_only:
    df_leaderboard = df_leaderboard[df_leaderboard['current_streak'] > 0]

if not df_leaderboard.empty and search_query:
    df_leaderboard = df_leaderboard[
        df_leaderboard['symbol'].str.contains(search_query, case=False, na=False) |
        df_leaderboard['company_name'].str.contains(search_query, case=False, na=False)
    ]

# ==============================================================================
# MAIN PAGE HEADER & STATS
# ==============================================================================
st.title("HighTrack NSE: 52-Week High Intelligence")
st.markdown(
    f"Tracking **NSE Mainboard Equities** repeatedly printing fresh 52-week highs from **{start_date}** to **{end_date}**."
)

# Top KPI Summary Cards
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

total_unique_stocks = len(df_leaderboard) if not df_leaderboard.empty else 0
repeated_high_stocks = len(df_leaderboard[df_leaderboard['breakout_days'] >= 2]) if not df_leaderboard.empty else 0
active_streaks = len(df_leaderboard[df_leaderboard['current_streak'] >= 2]) if not df_leaderboard.empty else 0
mcap_above_500 = len(df_leaderboard[df_leaderboard['market_cap_cr'] >= 500]) if not df_leaderboard.empty else 0
total_events = int(df_leaderboard['breakout_days'].sum()) if not df_leaderboard.empty else 0

with kpi1:
    st.metric("Unique High Makers", f"{total_unique_stocks}")
with kpi2:
    st.metric("Repeated Highs (≥ 2 Days)", f"{repeated_high_stocks}", help="Stocks that appeared on 2 or more distinct trading sessions")
with kpi3:
    st.metric("Active Streaks (≥ 2 Days)", f"{active_streaks}", help="Stocks hitting fresh highs on 2+ consecutive sessions ending on the latest date")
with kpi4:
    st.metric("Total Breakout Events", f"{total_events}")
with kpi5:
    st.metric("Market Cap ≥ 500 Cr", f"{mcap_above_500}")

st.markdown("---")

# ==============================================================================
# DASHBOARD NAVIGATION
# ==============================================================================
nav_options = [
    "Breakout Leaderboard",
    "Stock Deep-Dive",
    "Market Breadth & Trends",
    "Data Ingestion & Health"
]

# Apply any pending tab switch BEFORE widget instantiation to prevent StreamlitWidgetAlreadyInstantiatedError
if "pending_tab" in st.session_state and st.session_state["pending_tab"] in nav_options:
    st.session_state["nav_tab"] = st.session_state.pop("pending_tab")

if "nav_tab" not in st.session_state or st.session_state["nav_tab"] not in nav_options:
    st.session_state["nav_tab"] = "Breakout Leaderboard"

selected_tab = st.segmented_control(
    "Navigation",
    options=nav_options,
    key="nav_tab",
    label_visibility="collapsed"
)

if not selected_tab:
    selected_tab = st.session_state.get("nav_tab", "Breakout Leaderboard")

# ------------------------------------------------------------------------------
# TAB 1: BREAKOUT LEADERBOARD
# ------------------------------------------------------------------------------
if selected_tab == "Breakout Leaderboard":
    st.subheader(f"Leaderboard: Ranked by 52-Week High Breakout Frequency ({timeframe})")
    st.caption("Tip: Click any stock row to open its Stock Deep-Dive and official NSE page.")
    
    if df_leaderboard.empty:
        st.warning("No stocks match the current filter criteria. Try relaxing the market cap, minimum breakout days, or date range filters.")
    else:
        # Keep all numeric values strictly as pure floats and integers for 100% accurate column sorting!
        display_df = pd.DataFrame()
        display_df['Symbol'] = df_leaderboard['symbol']
        display_df['Company'] = df_leaderboard['company_name']
        display_df['Market Cap (Cr)'] = df_leaderboard['market_cap_cr'].astype(float).round(2)
        display_df['High Days'] = df_leaderboard['breakout_days'].astype(int)
        display_df['Current Streak'] = df_leaderboard['current_streak'].astype(int)
        display_df['Max Streak'] = df_leaderboard['max_streak'].astype(int)
        display_df['LTP (₹)'] = df_leaderboard['latest_ltp'].astype(float).round(2)
        display_df['52W High (₹)'] = df_leaderboard['highest_52w_high'].astype(float).round(2)
        display_df['Drawdown %'] = df_leaderboard['drawdown_pct'].astype(float).round(2)
        display_df['Day Change %'] = df_leaderboard['latest_pct_change'].astype(float).round(2)
        display_df['Volume Ratio'] = df_leaderboard['volume_ratio'].astype(float).round(2)
        display_df['Breakout Dates'] = df_leaderboard['breakout_dates_str']
        
        # Display Streamlit DataFrame with row selection enabled
        event = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Symbol": st.column_config.TextColumn("Symbol", help="NSE Symbol"),
                "Company": st.column_config.TextColumn("Company", help="Company Name"),
                "Market Cap (Cr)": st.column_config.NumberColumn(
                    "Market Cap (Cr)",
                    help="Market Capitalization in Crore Rupees (numeric)",
                    format="%.2f"
                ),
                "High Days": st.column_config.NumberColumn(
                    "High Days",
                    help="Total distinct trading days stock hit 52-week high in period",
                    format="%d"
                ),
                "Current Streak": st.column_config.NumberColumn(
                    "Current Streak",
                    help="Consecutive trading sessions at high ending on latest date",
                    format="%d"
                ),
                "Max Streak": st.column_config.NumberColumn(
                    "Max Streak",
                    help="Maximum consecutive breakout streak in period",
                    format="%d"
                ),
                "LTP (₹)": st.column_config.NumberColumn(
                    "LTP (₹)",
                    help="Last Traded Price",
                    format="%.2f"
                ),
                "52W High (₹)": st.column_config.NumberColumn(
                    "52W High (₹)",
                    help="Highest 52-week high price recorded",
                    format="%.2f"
                ),
                "Drawdown %": st.column_config.NumberColumn(
                    "Drawdown %",
                    help="Percentage distance from highest recorded 52-week high",
                    format="%.2f%%"
                ),
                "Day Change %": st.column_config.NumberColumn(
                    "Day Change %",
                    help="Daily percentage price change on latest breakout",
                    format="%.2f%%"
                ),
                "Volume Ratio": st.column_config.NumberColumn(
                    "Volume Ratio",
                    help="Breakout day volume ratio vs benchmark",
                    format="%.2fx"
                ),
                "Breakout Dates": st.column_config.TextColumn(
                    "Breakout Dates",
                    help="Dates on which the company printed a new 52-week high",
                    width="large"
                )
            }
        )
        
        # Handle stock click event -> navigate to Stock Deep-Dive
        if event and hasattr(event, "selection") and event.selection and event.selection.rows:
            clicked_idx = event.selection.rows[0]
            clicked_symbol = display_df.iloc[clicked_idx]["Symbol"]
            st.session_state["selected_stock"] = clicked_symbol
            st.session_state["pending_tab"] = "Stock Deep-Dive"
            st.rerun()
        
        # Export Actions
        col_exp1, col_exp2, _ = st.columns([1, 1, 4])
        with col_exp1:
            csv_data = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"hightrack_nse_{start_date}_to_{end_date}.csv",
                mime="text/csv"
            )
        with col_exp2:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                display_df.to_excel(writer, index=False, sheet_name='52W_High_Leaderboard')
            excel_data = output.getvalue()
            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name=f"hightrack_nse_{start_date}_to_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ------------------------------------------------------------------------------
# TAB 2: INDIVIDUAL STOCK DEEP-DIVE
# ------------------------------------------------------------------------------
elif selected_tab == "Stock Deep-Dive":
    st.subheader("Stock Analysis & Historical Breakout Activity")
    
    available_symbols = df_leaderboard['symbol'].tolist() if not df_leaderboard.empty else []
    if not available_symbols:
        with database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT symbol FROM daily_breakouts ORDER BY symbol ASC")
            available_symbols = [r[0] for r in cur.fetchall()]
            
    if available_symbols:
        default_idx = 0
        if "selected_stock" in st.session_state and st.session_state["selected_stock"] in available_symbols:
            default_idx = available_symbols.index(st.session_state["selected_stock"])
            
        col_pick, col_links = st.columns([3, 2])
        with col_pick:
            selected_stock = st.selectbox(
                "Select Stock for Deep Dive",
                options=available_symbols,
                index=default_idx,
                help="Choose a stock to inspect its complete breakout dates, price progression, and streaks."
            )
            st.session_state["selected_stock"] = selected_stock
            
        with col_links:
            st.write("")
            st.write("")
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                nse_url = f"https://www.nseindia.com/get-quotes/equity?symbol={selected_stock}"
                st.link_button("View on NSE India ↗", nse_url)
            with col_l2:
                if st.button("← Back to Leaderboard"):
                    st.session_state["pending_tab"] = "Breakout Leaderboard"
                    st.rerun()
        
        stock_data = database.get_stock_details(selected_stock)
        info = stock_data["stock"]
        breakouts = stock_data["breakouts"]
        
        # Stock Summary Cards
        sc1, sc2, sc3, sc4 = st.columns(4)
        
        with sc1:
            st.metric("Symbol", info.get("symbol", selected_stock))
            st.caption(info.get("company_name", ""))
            st.markdown(f"[Official NSE Page ↗](https://www.nseindia.com/get-quotes/equity?symbol={selected_stock})")
        with sc2:
            mcap_val = float(info.get("market_cap_cr") or 0.0)
            st.metric("Market Cap (Cr)", f"{mcap_val:,.2f}")
            st.caption("NSE Universe")
        with sc3:
            total_b = len(breakouts)
            st.metric("Total 52W High Days", f"{total_b}")
            st.caption("In Database History")
        with sc4:
            if not breakouts.empty:
                max_high = float(breakouts['new_52w_high'].max())
                latest_ltp = float(breakouts.iloc[-1]['ltp'])
                dd = ((latest_ltp - max_high) / max_high) * 100 if max_high > 0 else 0.0
                st.metric("Current Drawdown", f"{dd:.2f}%")
                st.caption(f"Peak: {max_high:,.2f} | LTP: {latest_ltp:,.2f}")
            else:
                st.metric("Current Drawdown", "0.00%")
                
        st.markdown("---")
        
        if not breakouts.empty:
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.markdown("##### 52-Week High Price Progression")
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
                st.markdown("##### Daily % Change on Breakout Sessions")
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
                
            st.markdown("##### Detailed Breakout History Log")
            
            # Numeric sorting in history table
            hist_display = pd.DataFrame()
            hist_display['Breakout Date'] = breakouts['breakout_date']
            hist_display['LTP (₹)'] = breakouts['ltp'].astype(float).round(2)
            hist_display['New 52W High (₹)'] = breakouts['new_52w_high'].astype(float).round(2)
            hist_display['Previous High (₹)'] = breakouts['prev_high'].astype(float).round(2)
            hist_display['Daily % Change'] = breakouts['pct_change'].astype(float).round(2)
            hist_display['Traded Volume'] = breakouts['volume'].astype(int)
            hist_display['Source File'] = breakouts['source_file']
            
            st.dataframe(
                hist_display.sort_values('Breakout Date', ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Breakout Date": st.column_config.TextColumn("Breakout Date"),
                    "LTP (₹)": st.column_config.NumberColumn("LTP (₹)", format="%.2f"),
                    "New 52W High (₹)": st.column_config.NumberColumn("New 52W High (₹)", format="%.2f"),
                    "Previous High (₹)": st.column_config.NumberColumn("Previous High (₹)", format="%.2f"),
                    "Daily % Change": st.column_config.NumberColumn("Daily % Change", format="%.2f%%"),
                    "Traded Volume": st.column_config.NumberColumn("Traded Volume", format="%d")
                }
            )
        else:
            st.info("No breakout records found for this symbol.")
    else:
        st.info("No stock data available.")

# ------------------------------------------------------------------------------
# TAB 3: MARKET BREADTH & DAILY TRENDS
# ------------------------------------------------------------------------------
elif selected_tab == "Market Breadth & Trends":
    st.subheader("Market Breadth & Daily 52-Week High Trends")
    
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
            st.markdown("##### Daily Count of Mainboard Stocks Hitting 52-Week High")
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
            st.markdown("##### Market Cap Classification of High Makers")
            if not df_leaderboard.empty:
                def categorize_mcap(val):
                    if val >= 20000:
                        return "Large Cap (> 20,000 Cr)"
                    elif val >= 5000:
                        return "Mid Cap (5,000 - 20,000 Cr)"
                    elif val >= 500:
                        return "Small Cap (500 - 5,000 Cr)"
                    else:
                        return "Micro Cap (< 500 Cr)"
                        
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
                
        if not df_leaderboard.empty:
            st.markdown("##### Streak Distribution (Consecutive Sessions at Highs)")
            fig_hist = px.histogram(
                df_leaderboard,
                x='max_streak',
                nbins=10,
                color_discrete_sequence=['#3B82F6'],
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
# TAB 4: DATA INGESTION & SYSTEM HEALTH
# ------------------------------------------------------------------------------
elif selected_tab == "Data Ingestion & Health":
    st.subheader("Data Ingestion, Collection & Health Audit")
    
    st.markdown("### Real Historical Data Sync (NSE PR Archive)")
    st.info("NSE's daily Price/Reports archive covers every trading day from 2017 to today. You can backfill verified official 52-week highs and exact market caps with 1 click.")
    
    col_hist1, col_hist2 = st.columns([1, 1])
    with col_hist1:
        backfill_count = st.slider("Number of Past Trading Sessions to Backfill", min_value=5, max_value=60, value=30, step=5)
        if st.button(f"Backfill Past {backfill_count} Trading Days", type="primary"):
            with st.spinner(f"Downloading real 52-week-high data for past {backfill_count} trading sessions..."):
                res = backfill_real_history(num_days=backfill_count, end_date_str=latest_available_date)
                if res["success"]:
                    st.success(f"Successfully backfilled {res['days_backfilled']} trading sessions! Total new breakout records inserted: {res['total_inserted']}.")
                    st.rerun()
                else:
                    st.error("Failed to backfill data.")
                    
    with col_hist2:
        custom_pr_date = st.date_input("Fetch Specific Historical Date", value=pd.to_datetime("2026-11-03"))
        if st.button("Fetch Historical Date"):
            with st.spinner(f"Fetching real PR records for {custom_pr_date}..."):
                res = fetch_from_mtf_pr(custom_pr_date.strftime("%Y-%m-%d"))
                if res["success"]:
                    st.success(res['message'])
                    st.rerun()
                else:
                    st.warning(res['message'])
                    
    st.markdown("---")
    col_ing1, col_ing2 = st.columns(2)
    
    with col_ing1:
        st.markdown("### Upload Downloaded NSE CSV")
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
        
        if st.button("Process & Ingest CSV"):
            if uploaded_file is not None:
                with st.spinner("Parsing and storing records..."):
                    res = parse_and_ingest_csv(
                        source_input=uploaded_file.getvalue(),
                        snapshot_date=upload_date.strftime("%Y-%m-%d"),
                        source_label=f"Manual Upload: {uploaded_file.name}",
                        filter_series_eq=False
                    )
                    if res["success"]:
                        st.success(res['message'])
                        st.rerun()
                    else:
                        st.error(res['message'])
            else:
                st.warning("Please select a CSV file first.")
                
    with col_ing2:
        st.markdown("### Automated Fetch from NSE Live")
        st.write("Trigger automated download directly from official NSE India.")
        
        fetch_date = st.date_input(
            "Fetch Snapshot Date",
            value=date.today(),
            key="fetch_date_input"
        )
        
        if st.button("Fetch Today's Highs from NSE"):
            with st.spinner("Connecting to NSE and downloading 52-week-high report..."):
                res = fetch_live_from_nse(snapshot_date=fetch_date.strftime("%Y-%m-%d"))
                if res["success"]:
                    st.success(res['message'])
                    st.rerun()
                else:
                    st.warning(res['message'])
                    st.info("Tip: If NSE blocks automated cloud requests, download the CSV via your browser and upload it using the left panel.")

    st.markdown("---")
    
    # Audit Logs
    st.markdown("### Ingestion Logs & System Audit")
    logs_df = database.get_ingestion_logs(limit=25)
    if not logs_df.empty:
        log_display = pd.DataFrame()
        log_display['Timestamp'] = logs_df['timestamp']
        log_display['Trading Date'] = logs_df['trading_date']
        log_display['Source'] = logs_df['source']
        log_display['Status'] = logs_df['status']
        log_display['Total Rows'] = logs_df['total_records'].astype(int)
        log_display['EQ Rows'] = logs_df['eq_records'].astype(int)
        log_display['Inserted'] = logs_df['inserted_records'].astype(int)
        log_display['Duplicates'] = logs_df['duplicate_records'].astype(int)
        log_display['Audit Log Message'] = logs_df['message']
        
        st.dataframe(
            log_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Total Rows": st.column_config.NumberColumn("Total Rows", format="%d"),
                "EQ Rows": st.column_config.NumberColumn("EQ Rows", format="%d"),
                "Inserted": st.column_config.NumberColumn("Inserted", format="%d"),
                "Duplicates": st.column_config.NumberColumn("Duplicates", format="%d"),
            }
        )
    else:
        st.info("No ingestion logs available.")
        
    st.markdown("---")
    if st.button("Reset / Re-seed Sample Data"):
        seed_sample_database(force=True)
        st.success("Sample database reset successfully!")
        st.rerun()
