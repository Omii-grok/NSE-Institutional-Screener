# -*- coding: utf-8 -*-
"""
NSE F&O Market Intelligence Dashboard
=====================================
Institutional derivative metrics, 52-Week High/Low tracking,
10-day volume bars, turnover in Crores, and automatic NSE F&O ban detection.
"""

import os
import glob
import pathlib
import datetime
import requests
import pandas as pd
import streamlit as st

# Configure OpenBLAS thread safety
os.environ["OPENBLAS_NUM_THREADS"] = "1"

# Official NSE F&O symbols universe (fallback base)
DEFAULT_FNO_SYMBOLS: list[str] = [
    "AARTIIND","ABB","ABBOTINDIA","ABCAPITAL","ABFRL","ACC","ADANIENT",
    "ADANIPORTS","ALKEM","AMBUJACEM","ANGELONE","APLAPOLLO","APOLLOHOSP",
    "APOLLOTYRE","ASHOKLEY","ASIANPAINT","ASTRAL","ATUL","AUBANK",
    "AUROPHARMA","AXISBANK","BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE",
    "BALKRISIND","BANDHANBNK","BANKBARODA","BATAINDIA","BEL","BERGEPAINT",
    "BHARATFORG","BHARTIARTL","BHEL","BIOCON","BOSCHLTD","BPCL",
    "BRITANNIA","BSOFT","CANBK","CANFINHOME","CDSL","CESC","CHOLAFIN",
    "CIPLA","COALINDIA","COFORGE","COLPAL","CONCOR","COROMANDEL",
    "CROMPTON","CUB","CUMMINSIND","DABUR","DALBHARAT","DEEPAKNTR",
    "DELTACORP","DIVISLAB","DIXON","DLF","DMART","DRREDDY","EICHERMOT",
    "ESCORTS","EXIDEIND","FEDERALBNK","FINNIFTY","FORTIS","GAIL",
    "GLENMARK","GMRINFRA","GNFC","GODREJCP","GODREJPROP","GRANULES",
    "GRASIM","GSPL","GUJGASLTD","HAL","HAVELLS","HCLTECH","HDFCAMC",
    "HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDCOPPER",
    "HINDPETRO","HINDUNILVR","HONAUT","IBULHSGFIN","ICICIBANK",
    "ICICIGI","ICICIPRULI","IDEA","IDFCFIRSTB","IEX","IGL","INDHOTEL",
    "INDIAMART","INDUSINDBK","INDUSTOWER","INFY","IOC","IPCALAB",
    "IRCTC","ISEC","ITC","JINDALSTEL","JKCEMENT","JSWSTEEL",
    "JUBLFOOD","KAYNES","KOTAKBANK","KPITTECH","L&TFH","LALPATHLAB","LAURUSLABS",
    "LICHSGFIN","LT","LTIM","LTTS","LUPIN","M&M","M&MFIN",
    "MANAPPURAM","MARICO","MARUTI","MCDOWELL-N","MCX","METROPOLIS",
    "MFSL","MGL","MPHASIS","MRF","MUTHOOTFIN","NAUKRI","NAVINFLUOR",
    "NESTLEIND","NMDC","NTPC","OBEROIRLTY","OFSS","ONGC","PAGEIND",
    "PEL","PERSISTENT","PETRONET","PFC","PIDILITIND","PIIND","PNB",
    "POLYCAB","POWERGRID","PVRINOX","RAMCOCEM","RBLBANK","RECLTD",
    "RELIANCE","SAIL","SBICARD","SBILIFE","SBIN","SHREECEM",
    "SHRIRAMFIN","SIEMENS","SRF","SUNPHARMA","SUNTV","SUPREMEIND",
    "SYNGENE","TATACHEM","TATACOMM","TATACONSUM","TATAMOTORS",
    "TATAPOWER","TATASTEEL","TCS","TECHM","TITAN","TORNTPHARM",
    "TORNTPOWER","TRENT","TVSMOTOR","UBL","ULTRACEMCO","UNIONBANK",
    "UPL","VEDL","VOLTAS","WIPRO","ZEEL","ZOMATO","ZYDUSLIFE",
]

# ---------------------------------------------------------------------------
# DATA HELPERS & CACHING
# ---------------------------------------------------------------------------

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fo_ban_list() -> set[str]:
    """Fetch securities currently in NSE F&O ban period from official archive."""
    url = "https://nsearchives.nseindia.com/content/fo/fo_secban.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            ban_symbols = set()
            for line in r.text.strip().splitlines():
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    sym = parts[1].strip().upper()
                    if sym and not sym.isdigit() and "SYMBOL" not in sym:
                        ban_symbols.add(sym)
            return ban_symbols
    except Exception:
        pass
    return set()


@st.cache_data(ttl=43200, show_spinner=False)
def calculate_52w_high_low() -> tuple[dict[str, float], dict[str, float]]:
    """Compute 52-week High and Low from historical data folder."""
    highs, lows = {}, {}
    # Look in data/ folder
    data_dirs = [pathlib.Path("data"), pathlib.Path(__file__).parent / "data", pathlib.Path(".")]
    csv_files = []
    for d in data_dirs:
        if d.exists():
            found = sorted(glob.glob(str(d / "bhavcopy_*.csv")))
            if found:
                csv_files = found[-250:]  # approx 1 year of trading sessions
                break

    for f_path in csv_files:
        try:
            df = pd.read_csv(f_path, skipinitialspace=True)
            df.columns = df.columns.str.strip()
            if "SERIES" in df.columns:
                df = df[df["SERIES"].str.strip() == "EQ"]
            if "SYMBOL" in df.columns and "HIGH_PRICE" in df.columns and "LOW_PRICE" in df.columns:
                for _, r in df.iterrows():
                    sym = str(r["SYMBOL"]).strip()
                    try:
                        h = float(r["HIGH_PRICE"])
                        l = float(r["LOW_PRICE"])
                        if sym not in highs or h > highs[sym]:
                            highs[sym] = h
                        if sym not in lows or l < lows[sym]:
                            lows[sym] = l
                    except (ValueError, TypeError):
                        continue
        except Exception:
            continue

    return highs, lows


def format_turnover_cr(val_lacs: float) -> str:
    """Format turnover from Lakhs into readable Indian Crores."""
    try:
        val_lacs = float(val_lacs)
        cr = val_lacs / 100.0
        if cr >= 100_000:
            return f"₹{cr/100_000:.2f} Lakh Cr"
        elif cr >= 1_000:
            return f"₹{cr:,.1f} Cr"
        elif cr >= 1:
            return f"₹{cr:.2f} Cr"
        else:
            return f"₹{val_lacs:.1f} L"
    except Exception:
        return "Data unavailable"


def format_volume_readable(qty: float) -> str:
    """Format volume into readable K, M, Cr format."""
    try:
        qty = float(qty)
        if qty >= 10_000_000:
            return f"{qty/10_000_000:.2f} Cr"
        elif qty >= 1_000_000:
            return f"{qty/1_000_000:.2f}M"
        elif qty >= 1_000:
            return f"{qty/1_000:.1f}K"
        return f"{int(qty):,}"
    except Exception:
        return "Data unavailable"


def build_volume_bar(ratio: float) -> str:
    """Generate compact mini visual bar for 10D Volume Ratio."""
    try:
        r = float(ratio)
        if r <= 0:
            return "░░░░░░░░░░ 0.0x"
        # 1.0x = 4 bars, 2.5x = 10 bars (capped at 10)
        filled = min(10, max(1, int(r * 4)))
        bar = "█" * filled + "░" * (10 - filled)
        return f"{bar} {r:.2f}x"
    except Exception:
        return "░░░░░░░░░░"


# ---------------------------------------------------------------------------
# MAIN F&O DASHBOARD RENDERER
# ---------------------------------------------------------------------------

def render_fno_dashboard(raw_df: pd.DataFrame | None = None, trade_date: datetime.date | None = None):
    """Render the full institutional F&O Market Dashboard."""
    
    # 1. Ensure raw_df is loaded
    if raw_df is None or raw_df.empty:
        st.info("📊 F&O Market Dashboard: Waiting for market bhavcopy to load...")
        return

    # Clean columns
    df = raw_df.copy()
    df.columns = df.columns.str.strip()
    if "SERIES" in df.columns:
        df = df[df["SERIES"].str.strip() == "EQ"].copy()

    # Determine F&O Universe
    ban_set = fetch_fo_ban_list()
    fno_universe = set(DEFAULT_FNO_SYMBOLS) | ban_set
    fno_raw = df[df["SYMBOL"].isin(fno_universe)].copy()

    if fno_raw.empty:
        st.warning("⚠️ No F&O symbols found in the loaded session.")
        return

    # Convert numeric fields
    for col in ["CLOSE_PRICE", "PREV_CLOSE", "HIGH_PRICE", "LOW_PRICE", "TTL_TRD_QNTY", "TURNOVER_LACS", "DELIV_PER"]:
        if col in fno_raw.columns:
            fno_raw[col] = pd.to_numeric(fno_raw[col], errors="coerce").fillna(0.0)

    # % Change
    if "PCT_CHANGE" not in fno_raw.columns:
        fno_raw["PCT_CHANGE"] = ((fno_raw["CLOSE_PRICE"] - fno_raw["PREV_CLOSE"]) / fno_raw["PREV_CLOSE"] * 100).round(2).fillna(0.0)

    # Fetch 52W High and Low
    highs_52w, lows_52w = calculate_52w_high_low()

    # Build F&O Master DataFrame
    records = []
    for _, r in fno_raw.iterrows():
        sym = str(r["SYMBOL"]).strip()
        close = float(r["CLOSE_PRICE"])
        prev = float(r["PREV_CLOSE"])
        pct_chg = float(r["PCT_CHANGE"])
        vol = float(r["TTL_TRD_QNTY"])
        deliv = float(r.get("DELIV_PER", 0.0))
        t_lacs = float(r.get("TURNOVER_LACS", (close * vol) / 100_000.0))

        # 52W metrics
        h52 = highs_52w.get(sym, float(r.get("HIGH_PRICE", close)))
        l52 = lows_52w.get(sym, float(r.get("LOW_PRICE", close)))
        if h52 <= 0: h52 = close
        if l52 <= 0: l52 = close

        # Distances
        dist_hi_pct = round(((close / h52) - 1.0) * 100.0, 2)  # negative or 0
        dist_lo_pct = round(((close / l52) - 1.0) * 100.0, 2)  # positive or 0

        # 10D Average volume (from avg_vol if merged, or approx from vol)
        avg_vol = float(r.get("AVG_VOL_10D", 0.0))
        if avg_vol <= 0:
            avg_vol = vol  # fallback
        vol_ratio = round(vol / avg_vol, 2) if avg_vol > 0 else 1.00

        # Ban status
        is_banned = sym in ban_set
        ban_label = "🚫 BAN" if is_banned else "Normal"

        records.append({
            "Symbol": sym,
            "LTP (₹)": close,
            "Change (%)": pct_chg,
            "52W High (₹)": h52,
            "Dist 52W High (%)": dist_hi_pct,
            "52W Low (₹)": l52,
            "Dist 52W Low (%)": dist_lo_pct,
            "Today Volume": int(vol),
            "10D Avg Vol": int(avg_vol),
            "Vol Ratio": vol_ratio,
            "10D Vol Bar": build_volume_bar(vol_ratio),
            "Delivery (%)": deliv,
            "Turnover (₹Cr)": round(t_lacs / 100.0, 2),
            "Turnover": format_turnover_cr(t_lacs),
            "Ban Status": ban_label,
            "Is Banned": is_banned,
        })

    fno_master = pd.DataFrame(records)

    # -----------------------------------------------------------------------
    # TOP MARKET METRICS CARDS
    # -----------------------------------------------------------------------
    total_fno = len(fno_master)
    near_high_cnt = len(fno_master[fno_master["Dist 52W High (%)"] >= -5.0])
    near_low_cnt = len(fno_master[fno_master["Dist 52W Low (%)"] <= 5.0])
    ban_cnt = len(ban_set)
    high_vol_cnt = len(fno_master[fno_master["Vol Ratio"] >= 2.0])
    total_to_cr = fno_master["Turnover (₹Cr)"].sum()
    total_vol_sum = fno_master["Today Volume"].sum()

    st.markdown("""
    <div class="sec-hdr blue" style="margin-top: 1.2rem; margin-bottom: 1rem;">
        <div class="title">📊 NSE F&O MARKET INTELLIGENCE DASHBOARD</div>
        <div class="chips">
            <span class="chip">Institutional Derivative Suite</span>
            <span class="chip">Auto EOD Sync</span>
            <span class="chip">Live F&O Ban Tracker</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top metrics row
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("Total F&O Stocks", total_fno)
    with m2:
        st.metric("Near 52W High (≤5%)", near_high_cnt, delta="Bullish" if near_high_cnt > 0 else None)
    with m3:
        st.metric("Near 52W Low (≤5%)", near_low_cnt, delta="Oversold" if near_low_cnt > 0 else None, delta_color="inverse")
    with m4:
        st.metric("F&O Ban Count", ban_cnt, delta="Restricted" if ban_cnt > 0 else "0 in Ban", delta_color="inverse" if ban_cnt > 0 else "normal")
    with m5:
        st.metric("Volume Spikes (>2x)", high_vol_cnt)
    with m6:
        st.metric("Total F&O Turnover", f"₹{total_to_cr:,.1f} Cr")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # DEDICATED SECTIONS: 52W HIGH / 52W LOW / F&O BAN
    # -----------------------------------------------------------------------
    col_hi, col_lo = st.columns(2)

    with col_hi:
        st.markdown("""
        <div class="sec-hdr gold" style="margin-bottom:0.6rem;">
            <div class="title">🔥 F&O STOCKS NEAR 52-WEEK HIGH</div>
            <div class="chips"><span class="chip">Within 5% of Annual Peak</span></div>
        </div>
        """, unsafe_allow_html=True)
        hi_df = fno_master[fno_master["Dist 52W High (%)"] >= -5.0].sort_values("Dist 52W High (%)", ascending=False)
        if hi_df.empty:
            st.info("No F&O stocks currently within 5% of their 52-week high.")
        else:
            disp_hi = hi_df[["Symbol", "LTP (₹)", "Change (%)", "52W High (₹)", "Dist 52W High (%)", "10D Vol Bar", "Turnover"]]
            st.dataframe(disp_hi, use_container_width=True, hide_index=True, height=280)

    with col_lo:
        st.markdown("""
        <div class="sec-hdr red" style="margin-bottom:0.6rem;">
            <div class="title">📉 F&O STOCKS NEAR 52-WEEK LOW</div>
            <div class="chips"><span class="chip">Within 5% of Annual Low</span></div>
        </div>
        """, unsafe_allow_html=True)
        lo_df = fno_master[fno_master["Dist 52W Low (%)"] <= 5.0].sort_values("Dist 52W Low (%)", ascending=True)
        if lo_df.empty:
            st.info("No F&O stocks currently within 5% of their 52-week low.")
        else:
            disp_lo = lo_df[["Symbol", "LTP (₹)", "Change (%)", "52W Low (₹)", "Dist 52W Low (%)", "10D Vol Bar", "Turnover"]]
            st.dataframe(disp_lo, use_container_width=True, hide_index=True, height=280)

    # F&O Ban Banner Section
    st.markdown("""
    <div class="sec-hdr violet" style="margin-top:1.2rem; margin-bottom:0.6rem;">
        <div class="title">🚫 NSE F&O BAN SECURITIES</div>
        <div class="chips"><span class="chip">Official NSE MWPL Ban Restrictions</span></div>
    </div>
    """, unsafe_allow_html=True)

    banned_df = fno_master[fno_master["Is Banned"] == True]
    if banned_df.empty:
        st.success("✅ **Zero securities currently under F&O ban period.** All derivative positions open for normal trading.")
    else:
        st.warning(f"⚠️ **{len(banned_df)} Stocks under F&O Ban:** {', '.join(banned_df['Symbol'].tolist())}")
        disp_ban = banned_df[["Symbol", "LTP (₹)", "Change (%)", "Today Volume", "Turnover", "Ban Status"]]
        st.dataframe(disp_ban, use_container_width=True, hide_index=True, height=180)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # MAIN F&O MASTER STOCK TABLE WITH QUICK FILTERS & SEARCH
    # -----------------------------------------------------------------------
    st.markdown("""
    <div class="sec-hdr blue" style="margin-bottom: 0.6rem;">
        <div class="title">📋 MASTER F&O STOCKS DIRECTORY</div>
        <div class="chips">
            <span class="chip">Multi-Parameter Screener</span>
            <span class="chip">Volume Ratio Bars</span>
            <span class="chip">Turnover Analysis</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick Filters Bar
    qf_col1, qf_col2 = st.columns([1, 2])
    with qf_col1:
        quick_filter = st.selectbox(
            "Quick Filter",
            options=[
                "All F&O Stocks",
                "🔥 Near 52W High (≤5%)",
                "📉 Near 52W Low (≤5%)",
                "🚫 F&O Ban Only",
                "📊 High Volume (>2x Avg)",
                "💰 High Turnover (>₹250 Cr)",
                "📈 Top Gainers (>2%)",
                "🔻 Top Losers (<-2%)"
            ],
            key="fno_quick_filter_select"
        )
    with qf_col2:
        search_sym = st.text_input(
            "Search Symbol",
            placeholder="🔍 Filter symbol (e.g. RELIANCE, TCS, INFY, SBIN, TATA...)",
            key="fno_master_search_input"
        )

    # Apply Filters
    filtered_df = fno_master.copy()

    if quick_filter == "🔥 Near 52W High (≤5%)":
        filtered_df = filtered_df[filtered_df["Dist 52W High (%)"] >= -5.0]
    elif quick_filter == "📉 Near 52W Low (≤5%)":
        filtered_df = filtered_df[filtered_df["Dist 52W Low (%)"] <= 5.0]
    elif quick_filter == "🚫 F&O Ban Only":
        filtered_df = filtered_df[filtered_df["Is Banned"] == True]
    elif quick_filter == "📊 High Volume (>2x Avg)":
        filtered_df = filtered_df[filtered_df["Vol Ratio"] >= 2.0]
    elif quick_filter == "💰 High Turnover (>₹250 Cr)":
        filtered_df = filtered_df[filtered_df["Turnover (₹Cr)"] >= 250.0]
    elif quick_filter == "📈 Top Gainers (>2%)":
        filtered_df = filtered_df[filtered_df["Change (%)"] >= 2.0]
    elif quick_filter == "🔻 Top Losers (<-2%)":
        filtered_df = filtered_df[filtered_df["Change (%)"] <= -2.0]

    if search_sym.strip():
        filtered_df = filtered_df[filtered_df["Symbol"].str.contains(search_sym.strip().upper(), case=False, na=False)]

    # Final table display columns
    display_cols = [
        "Symbol",
        "LTP (₹)",
        "Change (%)",
        "52W High (₹)",
        "Dist 52W High (%)",
        "52W Low (₹)",
        "Dist 52W Low (%)",
        "10D Vol Bar",
        "Delivery (%)",
        "Turnover",
        "Ban Status",
    ]

    st.markdown(f'<div style="font-size:0.8rem; color:#94a3b8; margin-bottom:6px;">Showing <b>{len(filtered_df)}</b> of {total_fno} F&O Stocks</div>', unsafe_allow_html=True)
    st.dataframe(
        filtered_df[display_cols].sort_values("Change (%)", ascending=False),
        use_container_width=True,
        hide_index=True,
        height=520,
    )
