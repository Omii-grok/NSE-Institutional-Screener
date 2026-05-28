"""
NSE EOD Institutional Screener — Automated Streamlit App
=========================================================
Fetches sec_bhavdata_full.csv directly from NSE archives,
handles weekends & holidays gracefully, caches once per day,
and displays three sections:

  1. HNI Breakouts      — Close > ₹50 | Vol > 50k | Chg ≥ 4% | Delivery ≥ 50%
  2. 100% Pure Delivery — Close > ₹10 | Vol > 0   | Chg > 0  | Delivery = 100%
  3. F&O Master Tracker — All ~182 F&O EQ stocks, raw & sortable
"""

import io
import datetime
import requests
import pandas as pd
import pytz
import streamlit as st

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Institutional Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS — dark premium look
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Main background */
.stApp {
    background: linear-gradient(160deg, #070b14 0%, #0a1020 50%, #0d1428 100%);
    color: #e2e8f0;
}

/* Header banner */
.header-card {
    background: linear-gradient(135deg, #0f1e3d 0%, #111f3a 60%, #0a1528 100%);
    border: 1px solid rgba(99,179,237,0.2);
    border-radius: 20px;
    padding: 32px 40px;
    margin-bottom: 28px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06);
    position: relative;
    overflow: hidden;
}
.header-card::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 220px; height: 220px;
    background: radial-gradient(circle, rgba(99,179,237,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.header-card h1 {
    margin: 0 0 6px 0;
    font-size: 2.1rem;
    font-weight: 800;
    background: linear-gradient(90deg, #63b3ed 0%, #90cdf4 40%, #48bb78 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
}
.header-card .subtitle {
    font-size: 0.92rem;
    color: #667eea;
    margin: 0;
    font-weight: 400;
}

/* Date badge */
.date-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(72,187,120,0.12);
    border: 1px solid rgba(72,187,120,0.35);
    border-radius: 10px;
    padding: 7px 16px;
    font-size: 0.88rem;
    color: #68d391;
    font-weight: 600;
    margin-top: 14px;
    letter-spacing: 0.01em;
}

/* Metric cards */
.metric-row {
    display: flex;
    gap: 16px;
    margin-bottom: 28px;
    flex-wrap: wrap;
}
.metric-card {
    flex: 1;
    min-width: 160px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 20px 24px;
    text-align: center;
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    cursor: default;
}
.metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.metric-card.gold  { border-color: rgba(237,192,99,0.2); }
.metric-card.teal  { border-color: rgba(99,179,237,0.2); }
.metric-card.green { border-color: rgba(72,187,120,0.2); }
.metric-card.purple{ border-color: rgba(159,122,234,0.2); }
.metric-card:hover.gold  { border-color: rgba(237,192,99,0.45); }
.metric-card:hover.teal  { border-color: rgba(99,179,237,0.45); }
.metric-card:hover.green { border-color: rgba(72,187,120,0.45); }
.metric-card:hover.purple{ border-color: rgba(159,122,234,0.45); }
.metric-card .m-value {
    font-size: 2.2rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.03em;
}
.metric-card .m-label {
    font-size: 0.76rem;
    color: #4a5568;
    margin-top: 7px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 500;
}
.metric-card.gold   .m-value { color: #f6e05e; }
.metric-card.teal   .m-value { color: #90cdf4; }
.metric-card.green  .m-value { color: #68d391; }
.metric-card.purple .m-value { color: #b794f4; }

/* Section headers */
.section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 24px;
    border-radius: 14px 14px 0 0;
    font-weight: 700;
    font-size: 1.02rem;
    letter-spacing: 0.01em;
}
.section-header .criteria {
    font-size: 0.78rem;
    opacity: 0.65;
    font-weight: 400;
    margin-left: 4px;
}
.section-header.gold {
    background: linear-gradient(90deg, rgba(237,192,99,0.13), rgba(237,192,99,0.04));
    border-left: 4px solid #edc063;
    color: #f6e05e;
}
.section-header.green {
    background: linear-gradient(90deg, rgba(72,187,120,0.13), rgba(72,187,120,0.04));
    border-left: 4px solid #48bb78;
    color: #68d391;
}
.section-header.blue {
    background: linear-gradient(90deg, rgba(99,179,237,0.13), rgba(99,179,237,0.04));
    border-left: 4px solid #63b3ed;
    color: #90cdf4;
}

/* F&O search / filter bar */
.fno-search-note {
    font-size: 0.8rem;
    color: #4a5568;
    margin: 6px 0 2px 0;
    font-style: italic;
}

/* Dataframe wrapper */
.stDataFrame {
    border-radius: 0 0 14px 14px;
    overflow: hidden;
}

/* Divider */
.custom-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.06);
    margin: 36px 0;
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 50px 20px;
    color: #4a5568;
    font-style: italic;
    font-size: 0.95rem;
    background: rgba(255,255,255,0.015);
    border-radius: 0 0 14px 14px;
    border: 1px solid rgba(255,255,255,0.05);
    border-top: none;
}

/* Cache info */
.cache-note {
    font-size: 0.8rem;
    color: #4a5568;
    margin-bottom: 24px;
    font-style: italic;
}

/* Footer */
.footer {
    text-align: center;
    color: #2d3748;
    font-size: 0.76rem;
    padding: 28px 0 12px;
    margin-top: 48px;
    border-top: 1px solid rgba(255,255,255,0.04);
}

/* Error box */
.err-box {
    background: rgba(252,129,129,0.08);
    border: 1px solid rgba(252,129,129,0.3);
    border-radius: 12px;
    padding: 20px 24px;
    color: #fc8181;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# NSE HOLIDAY CALENDAR  (update annually)
# ─────────────────────────────────────────────────────────────
NSE_HOLIDAYS: set[datetime.date] = {
    # 2025
    datetime.date(2025, 1, 26),
    datetime.date(2025, 2, 26),
    datetime.date(2025, 3, 14),
    datetime.date(2025, 3, 31),
    datetime.date(2025, 4, 14),
    datetime.date(2025, 4, 18),
    datetime.date(2025, 5, 1),
    datetime.date(2025, 8, 15),
    datetime.date(2025, 8, 27),
    datetime.date(2025, 10, 2),
    datetime.date(2025, 10, 20),
    datetime.date(2025, 10, 21),
    datetime.date(2025, 11, 5),
    datetime.date(2025, 12, 25),
    # 2026
    datetime.date(2026, 1, 26),
    datetime.date(2026, 3, 3),
    datetime.date(2026, 3, 20),
    datetime.date(2026, 4, 3),
    datetime.date(2026, 4, 14),
    datetime.date(2026, 5, 1),
    datetime.date(2026, 8, 15),
    datetime.date(2026, 9, 16),
    datetime.date(2026, 10, 2),
    datetime.date(2026, 10, 9),
    datetime.date(2026, 11, 9),
    datetime.date(2026, 12, 25),
}

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer":         "https://www.nseindia.com/",
    "Connection":      "keep-alive",
}


# ─────────────────────────────────────────────────────────────
# DATE HELPERS
# ─────────────────────────────────────────────────────────────
def is_trading_day(d: datetime.date) -> bool:
    """True if d is a weekday and not a known NSE holiday."""
    return d.weekday() < 5 and d not in NSE_HOLIDAYS


def last_trading_day() -> datetime.date:
    """
    Returns the most recent trading day for which NSE data should exist.
    NSE typically uploads EOD data by ~18:30 IST. If it's before that
    cut-off, we look at the previous trading day.
    """
    ist   = pytz.timezone("Asia/Kolkata")
    now   = datetime.datetime.now(ist)
    today = now.date()

    # Before the upload cut-off → treat previous day as latest
    candidate = today if now.hour >= 19 else today - datetime.timedelta(days=1)

    for _ in range(15):
        if is_trading_day(candidate):
            return candidate
        candidate -= datetime.timedelta(days=1)

    raise RuntimeError("Could not locate a trading day in the last 15 calendar days.")


# ─────────────────────────────────────────────────────────────
# NSE FETCHER
# ─────────────────────────────────────────────────────────────
def _fetch_one_date(session: requests.Session, d: datetime.date) -> pd.DataFrame | None:
    """Try to download the bhavcopy for a single date. Returns DataFrame or None."""
    date_str = d.strftime("%d%m%Y")
    url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"
    try:
        resp = session.get(url, headers=NSE_HEADERS, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 10_000:
            df = pd.read_csv(io.StringIO(resp.text), skipinitialspace=True)
            df.columns = df.columns.str.strip()
            return df
    except Exception:
        pass
    return None


@st.cache_data(ttl=86_400, show_spinner=False)   # ← cached for 24 hours
def fetch_nse_data() -> tuple[pd.DataFrame, datetime.date]:
    """
    Download the most recent available NSE Bhavcopy (sec_bhavdata_full).
    Walks backwards up to 7 trading days to handle holidays / upload delays.
    Returns (raw_DataFrame, trading_date).
    """
    base    = last_trading_day()
    session = requests.Session()

    # Warm up cookies — NSE blocks cold requests
    try:
        session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=10)
    except Exception:
        pass

    checked = 0
    candidate = base
    while checked < 7:
        if is_trading_day(candidate):
            df = _fetch_one_date(session, candidate)
            if df is not None:
                return df, candidate
            checked += 1
        candidate -= datetime.timedelta(days=1)

    # ── Local file fallback (committed by GitHub Actions daily) ──────────────
    import pathlib
    local_csv = pathlib.Path("sec_bhavdata_full.csv")
    if local_csv.exists():
        try:
            df = pd.read_csv(local_csv, skipinitialspace=True)
            df.columns = df.columns.str.strip()
            # Infer date from file modification time
            mtime = datetime.date.fromtimestamp(local_csv.stat().st_mtime)
            return df, mtime
        except Exception:
            pass

    raise ConnectionError(
        "Could not fetch NSE data for the last 7 trading days, "
        "and no local backup file (sec_bhavdata_full.csv) was found. "
        "On Streamlit Cloud: add the GitHub Actions workflow (fetch_nse.yml) "
        "so a fresh CSV is committed to the repo every weekday evening."
    )


# ─────────────────────────────────────────────────────────────
# 10-DAY AVERAGE VOLUME FETCHER
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=86_400, show_spinner=False)   # ← cached for 24 hours
def fetch_10day_avg_volume() -> "pd.Series":
    """
    Downloads the last 10 available trading-day bhavcopy files and
    returns a Series { SYMBOL -> mean(TTL_TRD_QNTY) } for EQ stocks.
    Cached separately from the daily fetch so it only runs once per day.
    """
    base    = last_trading_day()
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=10)
    except Exception:
        pass

    frames: list[pd.DataFrame] = []
    collected = 0
    candidate = base
    attempts  = 0

    while collected < 10 and attempts < 25:
        attempts += 1
        if is_trading_day(candidate):
            df = _fetch_one_date(session, candidate)
            if df is not None and "SERIES" in df.columns:
                eq = df[df["SERIES"].str.strip() == "EQ"][["SYMBOL", "TTL_TRD_QNTY"]].copy()
                eq["TTL_TRD_QNTY"] = pd.to_numeric(eq["TTL_TRD_QNTY"], errors="coerce")
                frames.append(eq)
                collected += 1
        candidate -= datetime.timedelta(days=1)

    if not frames:
        return pd.Series(dtype=float, name="AVG_VOL_10D")

    combined = pd.concat(frames, ignore_index=True)
    avg = (
        combined.groupby("SYMBOL")["TTL_TRD_QNTY"]
        .mean()
        .round(0)
    )
    avg.name = "AVG_VOL_10D"
    return avg


# ─────────────────────────────────────────────────────────────
# DATA PROCESSOR
# ─────────────────────────────────────────────────────────────
DISPLAY_COLS    = ["SYMBOL", "CLOSE_PRICE", "PCT_CHANGE", "TTL_TRD_QNTY", "DELIV_PER"]
DISPLAY_HEADERS = ["Symbol", "Close (₹)", "Change (%)", "Total Volume", "Delivery (%)"]


def _rename_and_round(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame[DISPLAY_COLS].copy()
    out.columns = DISPLAY_HEADERS
    out["Close (₹)"]     = out["Close (₹)"].round(2)
    out["Change (%)"]    = out["Change (%)"].round(2)
    out["Delivery (%)"]  = out["Delivery (%)"].round(2)
    return out.reset_index(drop=True)


def process_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """
    Clean raw bhavcopy and return:
      (hni_breakouts_df, pure_delivery_df, total_eq_count)
    """
    # Keep EQ series only
    if "SERIES" in df.columns:
        df = df[df["SERIES"].str.strip() == "EQ"].copy()

    # Coerce numeric columns
    for col in ("DELIV_PER", "CLOSE_PRICE", "PREV_CLOSE", "TTL_TRD_QNTY"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Percentage change
    df["PCT_CHANGE"] = ((df["CLOSE_PRICE"] - df["PREV_CLOSE"]) / df["PREV_CLOSE"]) * 100

    total_eq = len(df)

    # ── Filter 1: HNI Breakouts ────────────────────────────
    # Close > ₹50 | Volume > 50,000 | Change ≥ 4% | Delivery ≥ 50%
    hni = df[
        (df["CLOSE_PRICE"]  > 50.0)   &
        (df["TTL_TRD_QNTY"] > 50_000) &
        (df["PCT_CHANGE"]   >= 4.0)   &
        (df["DELIV_PER"]    >= 50.0)
    ].sort_values("DELIV_PER", ascending=False)

    # ── Filter 2: 100% Pure Delivery ──────────────────────
    # Close > ₹10 | Volume > 0 | Change > 0% | Delivery = 100%
    pure = df[
        (df["CLOSE_PRICE"]  > 10.0)  &
        (df["TTL_TRD_QNTY"] > 0)     &
        (df["PCT_CHANGE"]   > 0)      &
        (df["DELIV_PER"]    == 100.0)
    ].sort_values("TTL_TRD_QNTY", ascending=False)

    return _rename_and_round(hni), _rename_and_round(pure), total_eq


# ─────────────────────────────────────────────────────────────
# F&O UNIVERSE  — NSE official F&O stock list (~182 symbols)
# Source: NSE F&O Security Ban List + active derivatives segment
# ─────────────────────────────────────────────────────────────
FNO_SYMBOLS: list[str] = [
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC",
    "ADANIENT", "ADANIGREEN", "ADANIPORTS", "ADANIPOWER", "ADANITRANS",
    "AIAENG", "AJANTPHARM", "ALKEM", "ALKYLAMINE", "AMARAJABAT",
    "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "APLAPOLLO", "APTUS",
    "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATUL", "AUBANK",
    "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJAJHLDNG",
    "BAJFINANCE", "BALKRISIND", "BANDHANBNK", "BANKBARODA", "BANKINDIA",
    "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL",
    "BHEL", "BIOCON", "BIRLACORPN", "BPCL", "BSOFT",
    "CANBK", "CANFINHOME", "CDSL", "CESC", "CGPOWER",
    "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE",
    "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB",
    "CUMMINSIND", "CYIENT", "DABUR", "DALBHARAT", "DEEPAKNTR",
    "DELTACORP", "DIVISLAB", "DIXON", "DLF", "DMART",
    "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK",
    "FINNIFTY", "FORTIS", "GAIL", "GLENMARK", "GMRINFRA",
    "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRAPHITE",
    "GRASIM", "GSPL", "GUJGASLTD", "HAL", "HAVELLS",
    "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO",
    "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "HONASA",
    "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDBI", "IDFCFIRSTB",
    "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART",
    "INDIANB", "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY",
    "IOB", "IOC", "IPCALAB", "IRCTC", "IRFC",
    "ITC", "JINDALSTEL", "JKCEMENT", "JSL", "JSWENERGY",
    "JSWSTEEL", "JUBLFOOD", "JUSTDIAL", "KALYANKJIL", "KOTAKBANK",
    "KPITTECH", "KRBL", "KRISHNADEF", "L&TFH", "LAURUSLABS",
    "LICI", "LINDEINDIA", "LT", "LTIM", "LTTS",
    "LUPIN", "MANAPPURAM", "MARICO", "MARUTI", "MCX",
    "METROPOLIS", "MFSL", "MGL", "MMFINANCIAL", "MNGL",
    "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM",
    "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NHPC", "NMDC",
    "NTPC", "NYKAA", "OBEROIRLTY", "OFSS", "OIL",
    "ONGC", "PAGEIND", "PEL", "PERSISTENT", "PETRONET",
    "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB",
    "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD",
    "RELIANCE", "ROUTE", "SAIL", "SBICARD", "SBILIFE",
    "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF",
    "STARHEALTH", "SUNPHARMA", "SUNTV", "SUPREMEIND", "SYNGENE",
    "TATACHEM", "TATACOMM", "TATACONSUM", "TATAELXSI", "TATAMOTORS",
    "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TIINDIA",
    "TITAN", "TORNTPHARM", "TORNTPOWER", "TRENT", "TVSMOTOR",
    "UBL", "ULTRACEMCO", "UNIONBANK", "UPL", "VEDL",
    "VOLTAS", "WHIRLPOOL", "WIPRO", "ZEEL", "ZOMATO", "ZYDUSLIFE",
]

FNO_SYMBOLS_SET: set[str] = set(FNO_SYMBOLS)   # O(1) lookup


def build_fno_tracker(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter the cleaned EQ DataFrame to only F&O stocks.
    Returns a display-ready DataFrame with standard columns,
    sorted by Change % descending (best movers at top).
    """
    fno = df[
        (df["SYMBOL"].isin(FNO_SYMBOLS_SET)) &
        (df["SERIES"].str.strip() == "EQ")
    ].copy()

    # Coerce all numeric inputs (raw df may not have PCT_CHANGE yet)
    for col in ("CLOSE_PRICE", "PREV_CLOSE", "TTL_TRD_QNTY", "DELIV_PER"):
        if col in fno.columns:
            fno[col] = pd.to_numeric(fno[col], errors="coerce")

    # Compute % change if not already in the dataframe
    if "PCT_CHANGE" not in fno.columns:
        fno["PCT_CHANGE"] = (
            (fno["CLOSE_PRICE"] - fno["PREV_CLOSE"]) / fno["PREV_CLOSE"]
        ) * 100

    fno = fno.sort_values("PCT_CHANGE", ascending=False)

    out = fno[DISPLAY_COLS].copy()
    out.columns = DISPLAY_HEADERS
    out["Close (₹)"]    = out["Close (₹)"].round(2)
    out["Change (%)"]   = out["Change (%)"].round(2)
    out["Delivery (%)"] = out["Delivery (%)"].round(2)
    return out.reset_index(drop=True)


# ─────────────────────────────────────────────────────────────
# AVG VOL MERGER
# ─────────────────────────────────────────────────────────────
def _merge_avg_vol(display_df: pd.DataFrame, avg_vol: "pd.Series") -> pd.DataFrame:
    """
    Insert an 'Avg Vol (10D)' column right after 'Total Volume'.
    avg_vol is a Series indexed by raw SYMBOL strings.
    """
    display_df = display_df.copy()
    if avg_vol.empty:
        display_df["Avg Vol (10D)"] = pd.NA
    else:
        mapped = display_df["Symbol"].map(avg_vol)
        # Insert after Total Volume column
        insert_at = display_df.columns.get_loc("Total Volume") + 1
        display_df.insert(insert_at, "Avg Vol (10D)", mapped.round(0))
    return display_df


# ─────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────
_COL_CONFIG = {
    "Close (₹)":     st.column_config.NumberColumn(format="₹%.2f"),
    "Change (%)":    st.column_config.NumberColumn(format="%.2f%%"),
    "Total Volume":  st.column_config.NumberColumn(format="%d"),
    "Avg Vol (10D)": st.column_config.NumberColumn(
        "Avg Vol (10D)",
        format="%d",
        help="Average daily traded volume over the last 10 trading sessions",
    ),
    "Delivery (%)": st.column_config.NumberColumn(format="%.2f%%"),
}


def render_table(df: pd.DataFrame, empty_msg: str):
    if df.empty:
        st.markdown(
            f'<div class="empty-state">🔍 {empty_msg}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config=_COL_CONFIG,
        )


# ─────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────
def main():

    # ── Header ────────────────────────────────────────────────
    st.markdown("""
    <div class="header-card">
        <h1>📈 NSE Institutional Screener</h1>
        <p class="subtitle">End-of-Day Delivery &amp; Breakout Scanner — Powered by NSE Bhavcopy</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Fetch ─────────────────────────────────────────────────
    with st.spinner("⏳ Fetching latest NSE Bhavcopy data…"):
        try:
            raw_df, trade_date = fetch_nse_data()
        except ConnectionError as e:
            st.markdown(
                f'<div class="err-box">⚠️ <strong>Data fetch failed.</strong><br>{e}</div>',
                unsafe_allow_html=True,
            )
            st.info(
                "💡 **Tip for Streamlit Cloud**: NSE sometimes blocks cloud server IPs. "
                "Consider adding a scheduled GitHub Action that downloads and commits the CSV "
                "to the repo daily, then read from the local file as a fallback."
            )
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            st.stop()

    hni_df, pure_df, total_eq = process_data(raw_df)

    # Build F&O tracker from the raw (un-filtered) df so SERIES is still available
    fno_df = build_fno_tracker(raw_df)

    # ── Fetch 10-day average volume (cached — only downloads once per day) ──
    with st.spinner("📊 Loading 10-day average volume data (10 sessions)…"):
        try:
            avg_vol_10d = fetch_10day_avg_volume()
        except Exception:
            avg_vol_10d = pd.Series(dtype=float)

    hni_df  = _merge_avg_vol(hni_df,  avg_vol_10d)
    pure_df = _merge_avg_vol(pure_df, avg_vol_10d)
    fno_df  = _merge_avg_vol(fno_df,  avg_vol_10d)

    # ── Date badge ────────────────────────────────────────────
    st.markdown(
        f'<div class="date-badge">'
        f'✅ &nbsp;Data for: &nbsp;<strong>{trade_date.strftime("%A, %d %B %Y")}</strong>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("")  # spacer

    # ── Summary metric cards ──────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card gold">
            <div class="m-value">{len(hni_df)}</div>
            <div class="m-label">HNI Breakouts</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card green">
            <div class="m-value">{len(pure_df)}</div>
            <div class="m-label">100% Pure Delivery</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card teal">
            <div class="m-value">{len(fno_df)}</div>
            <div class="m-label">F&amp;O Stocks Active</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card purple">
            <div class="m-value">{total_eq:,}</div>
            <div class="m-label">Total EQ Stocks</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown(
        '<p class="cache-note">ℹ️ Data is cached for 24 hours. '
        'Refreshing the page will not trigger a new NSE download.</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # FILTER 1 — HNI BREAKOUTS
    # ══════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header gold">
        🏦 &nbsp;FILTER 1 — HNI BREAKOUTS
        <span class="criteria">
            Close&nbsp;&gt;&nbsp;₹50 &nbsp;·&nbsp;
            Volume&nbsp;&gt;&nbsp;50k &nbsp;·&nbsp;
            Change&nbsp;≥&nbsp;4% &nbsp;·&nbsp;
            Delivery&nbsp;≥&nbsp;50%
            &nbsp;|&nbsp; sorted by Delivery % ↓
        </span>
    </div>
    """, unsafe_allow_html=True)
    render_table(hni_df, "No stocks met the HNI Breakout criteria for this session.")

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # FILTER 2 — 100% PURE DELIVERY
    # ══════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header green">
        💎 &nbsp;FILTER 2 — 100% PURE DELIVERY
        <span class="criteria">
            Close&nbsp;&gt;&nbsp;₹10 &nbsp;·&nbsp;
            Volume&nbsp;&gt;&nbsp;0 &nbsp;·&nbsp;
            Change&nbsp;&gt;&nbsp;0% &nbsp;·&nbsp;
            Delivery&nbsp;=&nbsp;100%
            &nbsp;|&nbsp; sorted by Volume ↓
        </span>
    </div>
    """, unsafe_allow_html=True)
    render_table(pure_df, "No stocks recorded exactly 100% delivery with a positive close today.")

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # F&O MASTER TRACKER
    # ══════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header blue">
        📊 &nbsp;F&amp;O MASTER TRACKER
        <span class="criteria">
            All ~182 NSE F&amp;O stocks &nbsp;·&nbsp;
            EQ series only &nbsp;·&nbsp;
            Sorted by Change % ↓ &nbsp;|&nbsp;
            Click any column header to re-sort
        </span>
    </div>
    """, unsafe_allow_html=True)

    if fno_df.empty:
        st.markdown(
            '<div class="empty-state">🔍 No F&amp;O stock data found in today\'s bhavcopy.</div>',
            unsafe_allow_html=True,
        )
    else:
        # Search box to filter by symbol
        search_term = st.text_input(
            "",
            placeholder="🔍  Filter by symbol (e.g. RELIANCE, INFY, TCS…)",
            key="fno_search",
            label_visibility="collapsed",
        )
        display_fno = fno_df
        if search_term.strip():
            mask = display_fno["Symbol"].str.contains(
                search_term.strip().upper(), case=False, na=False
            )
            display_fno = display_fno[mask]

        st.dataframe(
            display_fno,
            use_container_width=True,
            hide_index=True,
            height=520,
            column_config={
                "Symbol":        st.column_config.TextColumn("Symbol"),
                "Close (₹)":    st.column_config.NumberColumn("Close (₹)",   format="₹%.2f"),
                "Change (%)":   st.column_config.NumberColumn(
                    "Change (%)",
                    format="%.2f%%",
                    help="Positive = green close, Negative = red close",
                ),
                "Total Volume":  st.column_config.NumberColumn("Total Volume",  format="%d"),
                "Avg Vol (10D)": st.column_config.NumberColumn(
                    "Avg Vol (10D)",
                    format="%d",
                    help="Average daily traded volume over last 10 sessions",
                ),
                "Delivery (%)": st.column_config.NumberColumn("Delivery (%)", format="%.2f%%"),
            },
        )
        st.markdown(
            f'<p class="fno-search-note">Showing {len(display_fno)} of {len(fno_df)} F&amp;O stocks · '
            f'Click any column header to sort · Use search box above to filter</p>',
            unsafe_allow_html=True,
        )

    # ── Footer ────────────────────────────────────────────────
    ist_now = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
    st.markdown(f"""
    <div class="footer">
        NSE Institutional Screener &nbsp;·&nbsp;
        Data sourced from NSE Archives &nbsp;·&nbsp;
        Last page load: {ist_now.strftime("%d %b %Y %H:%M IST")}
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__" or True:
    main()
