# -*- coding: utf-8 -*-
"""
NSE F&O Market Intelligence Dashboard - Pro Terminal Edition
============================================================
Featuring:
- Colourful, institutional-grade UI with dynamic neon tag styling
- Today Volume, 7-Day Average Volume, and 10-Day Average Volume
- Visual Volume Surge Indicators and mini intensity bars
- 52-Week High & Low distance tracking
- Turnover formatted in Indian Crores (₹Cr)
- Automatic official NSE F&O Ban detection
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

# Official NSE F&O universe base
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
def calculate_52w_high_low(ref_date: datetime.date | None = None) -> tuple[dict[str, float], dict[str, float]]:
    """Compute 52-week High and Low from historical data folder."""
    highs, lows = {}, {}
    data_dirs = [pathlib.Path("data"), pathlib.Path(__file__).parent / "data", pathlib.Path(".")]
    csv_files = []
    for d in data_dirs:
        if d.exists():
            found = sorted(glob.glob(str(d / "bhavcopy_*.csv")))
            if found:
                if ref_date:
                    ref_str = ref_date.strftime("%Y_%m_%d")
                    found = [f for f in found if os.path.basename(f) <= f"bhavcopy_{ref_str}.csv"]
                csv_files = found[-250:]
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


@st.cache_data(ttl=3600, show_spinner=False)
def calculate_7d_and_10d_avg_volumes(ref_date: datetime.date | None = None) -> tuple[dict[str, float], dict[str, float]]:
    """Calculate both 7-Day and 10-Day Average Daily Traded Volumes."""
    data_dirs = [pathlib.Path("data"), pathlib.Path(__file__).parent / "data", pathlib.Path(".")]
    csv_files = []
    for d in data_dirs:
        if d.exists():
            found = sorted(glob.glob(str(d / "bhavcopy_*.csv")))
            if found:
                if ref_date:
                    ref_str = ref_date.strftime("%Y_%m_%d")
                    found = [f for f in found if os.path.basename(f) <= f"bhavcopy_{ref_str}.csv"]
                csv_files = found
                break

    if not csv_files:
        return {}, {}

    last7 = csv_files[-7:]
    last10 = csv_files[-10:]

    f7, f10 = [], []
    for f in last10:
        try:
            df = pd.read_csv(f, skipinitialspace=True)
            df.columns = df.columns.str.strip()
            if "SERIES" in df.columns:
                eq = df[df["SERIES"].str.strip() == "EQ"][["SYMBOL", "TTL_TRD_QNTY"]].copy()
                eq["TTL_TRD_QNTY"] = pd.to_numeric(eq["TTL_TRD_QNTY"], errors="coerce")
                if f in last7:
                    f7.append(eq)
                f10.append(eq)
        except Exception:
            pass

    avg7_dict = {}
    avg10_dict = {}
    if f7:
        s7 = pd.concat(f7, ignore_index=True).groupby("SYMBOL")["TTL_TRD_QNTY"].mean().round(0)
        avg7_dict = s7.to_dict()
    if f10:
        s10 = pd.concat(f10, ignore_index=True).groupby("SYMBOL")["TTL_TRD_QNTY"].mean().round(0)
        avg10_dict = s10.to_dict()

    return avg7_dict, avg10_dict


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
    """Generate colorful high-contrast visual bar for volume surge ratio."""
    try:
        r = float(ratio)
        if r <= 0:
            return "░░░░░░░░░░ 0.0x"
        # 1.0x = 4 blocks, max 10 blocks
        filled = min(10, max(1, int(r * 4)))
        bar = "█" * filled + "░" * (10 - filled)
        if r >= 2.0:
            return f"🔥 {bar} {r:.2f}x"
        elif r >= 1.2:
            return f"⚡ {bar} {r:.2f}x"
        else:
            return f"📊 {bar} {r:.2f}x"
    except Exception:
        return "░░░░░░░░░░"


# ---------------------------------------------------------------------------
# PANDAS COLORFUL STYLING ENGINE
# ---------------------------------------------------------------------------

def _style_change(val):
    try:
        v = float(val)
        if v > 0:
            return "color: #00e676; font-weight: 700; background-color: rgba(0, 230, 118, 0.08);"
        elif v < 0:
            return "color: #ff3d57; font-weight: 700; background-color: rgba(255, 61, 87, 0.08);"
        return "color: #94a3b8;"
    except Exception:
        return ""


def _style_delivery(val):
    try:
        v = float(val)
        if v >= 70.0:
            return "color: #00ff88; font-weight: 800; background-color: rgba(0, 255, 136, 0.12);"
        elif v >= 50.0:
            return "color: #fbbf24; font-weight: 700; background-color: rgba(251, 191, 36, 0.10);"
        return "color: #94a3b8;"
    except Exception:
        return ""


def _style_dist_high(val):
    try:
        v = float(val)
        if v >= -1.0:
            return "color: #f59e0b; font-weight: 800; background-color: rgba(245, 158, 11, 0.18);"
        elif v >= -3.0:
            return "color: #fbbf24; font-weight: 700;"
        elif v >= -5.0:
            return "color: #fde047; font-weight: 600;"
        return "color: #94a3b8;"
    except Exception:
        return ""


def _style_dist_low(val):
    try:
        v = float(val)
        if v <= 1.0:
            return "color: #c084fc; font-weight: 800; background-color: rgba(192, 132, 252, 0.18);"
        elif v <= 5.0:
            return "color: #e879f9; font-weight: 600;"
        return "color: #94a3b8;"
    except Exception:
        return ""


def _style_vol_ratio(val):
    try:
        v = float(val)
        if v >= 2.0:
            return "color: #fb923c; font-weight: 800; background-color: rgba(251, 146, 60, 0.16);"
        elif v >= 1.2:
            return "color: #38bdf8; font-weight: 700;"
        return "color: #94a3b8;"
    except Exception:
        return ""


def _style_ban(val):
    if "BAN" in str(val):
        return "color: #ff4d4f; font-weight: 800; background-color: rgba(255, 77, 79, 0.22); border-radius: 4px;"
    return "color: #2dd4bf; font-weight: 600;"


def apply_colorful_terminal_styling(df: pd.DataFrame):
    """Apply rich colorful styling across all master columns."""
    styler = df.style
    if "Change (%)" in df.columns:
        styler = styler.map(_style_change, subset=["Change (%)"])
    if "Delivery (%)" in df.columns:
        styler = styler.map(_style_delivery, subset=["Delivery (%)"])
    if "Dist 52W High (%)" in df.columns:
        styler = styler.map(_style_dist_high, subset=["Dist 52W High (%)"])
    if "Dist 52W Low (%)" in df.columns:
        styler = styler.map(_style_dist_low, subset=["Dist 52W Low (%)"])
    if "Vol Surge (7D)" in df.columns:
        styler = styler.map(_style_vol_ratio, subset=["Vol Surge (7D)"])
    if "Ban Status" in df.columns:
        styler = styler.map(_style_ban, subset=["Ban Status"])
    return styler


# ---------------------------------------------------------------------------
# MAIN F&O DASHBOARD RENDERER
# ---------------------------------------------------------------------------

def render_fno_dashboard(raw_df: pd.DataFrame | None = None, trade_date: datetime.date | None = None):
    """Render the full colorful institutional F&O Market Dashboard."""

    if raw_df is None or raw_df.empty:
        st.info("📊 F&O Market Dashboard: Waiting for market bhavcopy to load...")
        return

    # Clean raw dataframe
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
    numeric_cols = ["CLOSE_PRICE", "PREV_CLOSE", "HIGH_PRICE", "LOW_PRICE", "TTL_TRD_QNTY", "TURNOVER_LACS", "DELIV_PER"]
    for col in numeric_cols:
        if col in fno_raw.columns:
            fno_raw[col] = pd.to_numeric(fno_raw[col], errors="coerce").fillna(0.0)

    # Calculate % Change
    if "PCT_CHANGE" not in fno_raw.columns:
        fno_raw["PCT_CHANGE"] = ((fno_raw["CLOSE_PRICE"] - fno_raw["PREV_CLOSE"]) / fno_raw["PREV_CLOSE"] * 100).round(2).fillna(0.0)

    # 1. Fetch 52W High and Low
    highs_52w, lows_52w = calculate_52w_high_low(trade_date)

    # 2. Fetch 7-Day & 10-Day Average Volumes
    avg7_dict, avg10_dict = calculate_7d_and_10d_avg_volumes(trade_date)

    # 3. Build F&O Master DataFrame
    records = []
    for _, r in fno_raw.iterrows():
        sym = str(r["SYMBOL"]).strip()
        close = float(r["CLOSE_PRICE"])
        pct_chg = float(r["PCT_CHANGE"])
        today_vol = float(r["TTL_TRD_QNTY"])
        deliv = float(r.get("DELIV_PER", 0.0))
        t_lacs = float(r.get("TURNOVER_LACS", (close * today_vol) / 100_000.0))

        # 52W Metrics
        h52 = highs_52w.get(sym, float(r.get("HIGH_PRICE", close)))
        l52 = lows_52w.get(sym, float(r.get("LOW_PRICE", close)))
        if h52 <= 0: h52 = close
        if l52 <= 0: l52 = close

        dist_hi_pct = round(((close / h52) - 1.0) * 100.0, 2)
        dist_lo_pct = round(((close / l52) - 1.0) * 100.0, 2)

        # Volume Metrics: 7D & 10D
        v7 = avg7_dict.get(sym, today_vol)
        v10 = avg10_dict.get(sym, today_vol)
        if v7 <= 0: v7 = today_vol
        if v10 <= 0: v10 = today_vol

        surge_7d = round(today_vol / v7, 2) if v7 > 0 else 1.00
        surge_10d = round(today_vol / v10, 2) if v10 > 0 else 1.00

        # Ban status
        is_banned = sym in ban_set
        ban_label = "🚫 BAN" if is_banned else "Normal"

        records.append({
            "Symbol": sym,
            "LTP (₹)": close,
            "Change (%)": pct_chg,
            "Today Volume": int(today_vol),
            "Today Vol": format_volume_readable(today_vol),
            "7D Avg Vol": format_volume_readable(v7),
            "7D Avg Volume": int(v7),
            "10D Avg Vol": format_volume_readable(v10),
            "10D Avg Volume": int(v10),
            "Vol Surge (7D)": surge_7d,
            "Vol Surge (10D)": surge_10d,
            "Volume Bar": build_volume_bar(surge_7d),
            "Delivery (%)": deliv,
            "52W High (₹)": h52,
            "Dist 52W High (%)": dist_hi_pct,
            "52W Low (₹)": l52,
            "Dist 52W Low (%)": dist_lo_pct,
            "Turnover (₹Cr)": round(t_lacs / 100.0, 2),
            "Turnover": format_turnover_cr(t_lacs),
            "Ban Status": ban_label,
            "Is Banned": is_banned,
        })

    fno_master = pd.DataFrame(records)

    # -----------------------------------------------------------------------
    # TOP MARKET METRICS CARDS (COLOURFUL INSTITUTIONAL DESIGN)
    # -----------------------------------------------------------------------
    total_fno = len(fno_master)
    near_high_cnt = len(fno_master[fno_master["Dist 52W High (%)"] >= -5.0])
    near_low_cnt = len(fno_master[fno_master["Dist 52W Low (%)"] <= 5.0])
    ban_cnt = len(ban_set)
    vol_surge_cnt = len(fno_master[fno_master["Vol Surge (7D)"] >= 1.5])
    total_to_cr = fno_master["Turnover (₹Cr)"].sum()
    total_vol_sum = fno_master["Today Volume"].sum()

    st.markdown("""
    <div class="sec-hdr blue" style="margin-top: 1.2rem; margin-bottom: 0.8rem;">
        <div class="title">📊 NSE F&O MARKET INTELLIGENCE TERMINAL</div>
        <div class="chips">
            <span class="chip" style="background: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.4);">
                ⚡ Real-Time Derivatives
            </span>
            <span class="chip" style="background: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.4);">
                📦 Today & 7D Volume Radar
            </span>
            <span class="chip" style="background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.4);">
                🚫 Live NSE Ban Tracker
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 6 Vibrant Metric Cards
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
        st.metric("Volume Spikes (>1.5x 7D)", vol_surge_cnt, delta="High Activity" if vol_surge_cnt > 0 else None)
    with m6:
        st.metric("Total F&O Turnover", f"₹{total_to_cr:,.1f} Cr")

    # -----------------------------------------------------------------------
    # VOLUME RADAR SPOTLIGHT (REAL APP FEEL)
    # -----------------------------------------------------------------------
    top_vol_stock = fno_master.sort_values("Today Volume", ascending=False).iloc[0] if not fno_master.empty else None
    top_surge_stock = fno_master.sort_values("Vol Surge (7D)", ascending=False).iloc[0] if not fno_master.empty else None
    top_deliv_stock = fno_master[fno_master["Today Volume"] > 500_000].sort_values("Delivery (%)", ascending=False).iloc[0] if not fno_master.empty else None

    if top_vol_stock is not None:
        st.markdown(f"""
        <div style="display: flex; gap: 12px; flex-wrap: wrap; margin: 12px 0 18px 0;">
            <div style="flex: 1; min-width: 260px; background: linear-gradient(135deg, rgba(59,130,246,0.12), rgba(30,58,138,0.25)); border: 1px solid rgba(59,130,246,0.35); border-radius: 10px; padding: 10px 14px;">
                <div style="font-size: 0.72rem; color: #93c5fd; font-weight: 700; text-transform: uppercase;">👑 Most Traded Today</div>
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 4px;">
                    <span style="font-size: 1.15rem; font-weight: 800; color: #ffffff;">{top_vol_stock['Symbol']}</span>
                    <span style="font-size: 0.95rem; font-weight: 700; color: #38bdf8;">{top_vol_stock['Today Vol']} shares ({top_vol_stock['Turnover']})</span>
                </div>
            </div>
            <div style="flex: 1; min-width: 260px; background: linear-gradient(135deg, rgba(245,158,11,0.12), rgba(180,83,9,0.25)); border: 1px solid rgba(245,158,11,0.35); border-radius: 10px; padding: 10px 14px;">
                <div style="font-size: 0.72rem; color: #fcd34d; font-weight: 700; text-transform: uppercase;">🔥 Highest 7D Volume Surge</div>
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 4px;">
                    <span style="font-size: 1.15rem; font-weight: 800; color: #ffffff;">{top_surge_stock['Symbol']}</span>
                    <span style="font-size: 0.95rem; font-weight: 700; color: #fbbf24;">{top_surge_stock['Vol Surge (7D)']}x 7-Day Average</span>
                </div>
            </div>
            <div style="flex: 1; min-width: 260px; background: linear-gradient(135deg, rgba(16,185,129,0.12), rgba(6,95,70,0.25)); border: 1px solid rgba(16,185,129,0.35); border-radius: 10px; padding: 10px 14px;">
                <div style="font-size: 0.72rem; color: #6ee7b7; font-weight: 700; text-transform: uppercase;">💎 Institutional Delivery Leader</div>
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 4px;">
                    <span style="font-size: 1.15rem; font-weight: 800; color: #ffffff;">{top_deliv_stock['Symbol']}</span>
                    <span style="font-size: 0.95rem; font-weight: 700; color: #34d399;">{top_deliv_stock['Delivery (%)']}% Delivery</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # 52W HIGH / 52W LOW / F&O BAN SUMMARY SECTIONS
    # -----------------------------------------------------------------------
    col_hi, col_lo = st.columns(2)

    with col_hi:
        st.markdown("""
        <div class="sec-hdr gold" style="margin-bottom:0.6rem;">
            <div class="title">🔥 F&O STOCKS NEAR 52-WEEK HIGH</div>
            <div class="chips"><span class="chip">Within 5% of Peak</span></div>
        </div>
        """, unsafe_allow_html=True)
        hi_df = fno_master[fno_master["Dist 52W High (%)"] >= -5.0].sort_values("Dist 52W High (%)", ascending=False)
        if hi_df.empty:
            st.info("No F&O stocks currently within 5% of their 52-week high.")
        else:
            disp_hi = hi_df[["Symbol", "LTP (₹)", "Change (%)", "52W High (₹)", "Dist 52W High (%)", "Today Vol", "7D Avg Vol", "Volume Bar", "Turnover"]]
            st.dataframe(apply_colorful_terminal_styling(disp_hi), use_container_width=True, hide_index=True, height=280)

    with col_lo:
        st.markdown("""
        <div class="sec-hdr red" style="margin-bottom:0.6rem;">
            <div class="title">📉 F&O STOCKS NEAR 52-WEEK LOW</div>
            <div class="chips"><span class="chip">Within 5% of Bottom</span></div>
        </div>
        """, unsafe_allow_html=True)
        lo_df = fno_master[fno_master["Dist 52W Low (%)"] <= 5.0].sort_values("Dist 52W Low (%)", ascending=True)
        if lo_df.empty:
            st.info("No F&O stocks currently within 5% of their 52-week low.")
        else:
            disp_lo = lo_df[["Symbol", "LTP (₹)", "Change (%)", "52W Low (₹)", "Dist 52W Low (%)", "Today Vol", "7D Avg Vol", "Volume Bar", "Turnover"]]
            st.dataframe(apply_colorful_terminal_styling(disp_lo), use_container_width=True, hide_index=True, height=280)

    # F&O Ban Banner Section
    st.markdown("""
    <div class="sec-hdr violet" style="margin-top:1.2rem; margin-bottom:0.6rem;">
        <div class="title">🚫 NSE F&O BAN RESTRICTIONS (MWPL)</div>
        <div class="chips"><span class="chip">Official Exchange Daily Report</span></div>
    </div>
    """, unsafe_allow_html=True)

    banned_df = fno_master[fno_master["Is Banned"] == True]
    if banned_df.empty:
        st.success("✅ **Zero securities in F&O ban period.** All derivative contracts open for regular order routing.")
    else:
        st.warning(f"⚠️ **{len(banned_df)} Securities in Ban:** {', '.join(banned_df['Symbol'].tolist())}")
        disp_ban = banned_df[["Symbol", "LTP (₹)", "Change (%)", "Today Vol", "7D Avg Vol", "Turnover", "Ban Status"]]
        st.dataframe(apply_colorful_terminal_styling(disp_ban), use_container_width=True, hide_index=True, height=180)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # MASTER F&O STOCKS DIRECTORY (COLOURFUL, INTERACTIVE, ALL VOLUMES)
    # -----------------------------------------------------------------------
    st.markdown("""
    <div class="sec-hdr blue" style="margin-bottom: 0.6rem;">
        <div class="title">📋 MASTER F&O STOCKS DIRECTORY</div>
        <div class="chips">
            <span class="chip" style="background:rgba(59,130,246,0.15); color:#60a5fa;">Today Volume</span>
            <span class="chip" style="background:rgba(16,185,129,0.15); color:#34d399;">7-Day Avg Vol</span>
            <span class="chip" style="background:rgba(245,158,11,0.15); color:#fbbf24;">10-Day Avg Vol</span>
            <span class="chip" style="background:rgba(139,92,246,0.15); color:#c084fc;">Surge Visual Bars</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick Filters & Search Bar
    qf_col1, qf_col2 = st.columns([1, 2])
    with qf_col1:
        quick_filter = st.selectbox(
            "Quick Filter",
            options=[
                "All F&O Stocks",
                "🔥 Near 52W High (≤5%)",
                "📉 Near 52W Low (≤5%)",
                "🚫 F&O Ban Only",
                "📊 High 7D Volume Surge (>1.5x)",
                "💥 Heavy 7D Volume Surge (>2.0x)",
                "💰 High Turnover (>₹250 Cr)",
                "📈 Top Gainers (>2%)",
                "🔻 Top Losers (<-2%)",
                "📦 Institutional Delivery (≥50%)"
            ],
            key="fno_master_filter_select"
        )
    with qf_col2:
        search_sym = st.text_input(
            "Search Symbol",
            placeholder="🔍 Search symbol (e.g. RELIANCE, TCS, INFY, SBIN, TATA...)",
            key="fno_master_search_input"
        )

    # Filter Application
    filtered_df = fno_master.copy()

    if quick_filter == "🔥 Near 52W High (≤5%)":
        filtered_df = filtered_df[filtered_df["Dist 52W High (%)"] >= -5.0]
    elif quick_filter == "📉 Near 52W Low (≤5%)":
        filtered_df = filtered_df[filtered_df["Dist 52W Low (%)"] <= 5.0]
    elif quick_filter == "🚫 F&O Ban Only":
        filtered_df = filtered_df[filtered_df["Is Banned"] == True]
    elif quick_filter == "📊 High 7D Volume Surge (>1.5x)":
        filtered_df = filtered_df[filtered_df["Vol Surge (7D)"] >= 1.5]
    elif quick_filter == "💥 Heavy 7D Volume Surge (>2.0x)":
        filtered_df = filtered_df[filtered_df["Vol Surge (7D)"] >= 2.0]
    elif quick_filter == "💰 High Turnover (>₹250 Cr)":
        filtered_df = filtered_df[filtered_df["Turnover (₹Cr)"] >= 250.0]
    elif quick_filter == "📈 Top Gainers (>2%)":
        filtered_df = filtered_df[filtered_df["Change (%)"] >= 2.0]
    elif quick_filter == "🔻 Top Losers (<-2%)":
        filtered_df = filtered_df[filtered_df["Change (%)"] <= -2.0]
    elif quick_filter == "📦 Institutional Delivery (≥50%)":
        filtered_df = filtered_df[filtered_df["Delivery (%)"] >= 50.0]

    if search_sym.strip():
        filtered_df = filtered_df[filtered_df["Symbol"].str.contains(search_sym.strip().upper(), case=False, na=False)]

    # Comprehensive Display Columns
    display_cols = [
        "Symbol",
        "LTP (₹)",
        "Change (%)",
        "Today Vol",
        "7D Avg Vol",
        "10D Avg Vol",
        "Vol Surge (7D)",
        "Volume Bar",
        "Delivery (%)",
        "52W High (₹)",
        "Dist 52W High (%)",
        "52W Low (₹)",
        "Dist 52W Low (%)",
        "Turnover",
        "Ban Status",
    ]

    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-size:0.82rem; color:#94a3b8;">Showing <b style="color:#f8fafc;">{len(filtered_df)}</b> of {total_fno} F&O Stocks</span>
        <span style="font-size:0.75rem; color:#64748b; font-family:'JetBrains Mono',monospace;">⚡ Click any column header to sort</span>
    </div>
    """, unsafe_allow_html=True)

    # Render Colorful Master Table
    styled_table = apply_colorful_terminal_styling(filtered_df[display_cols].sort_values("Change (%)", ascending=False))
    st.dataframe(
        styled_table,
        use_container_width=True,
        hide_index=True,
        height=580,
    )
