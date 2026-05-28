"""
NSE EOD Institutional Screener — v2.0 Premium Trading Terminal
==============================================================
Dark trading-terminal UI with:
  • Dynamic GREEN / RED coloring for % change (▲ positive / ▼ negative)
  • Color-coded Delivery % (green ≥ 70 | yellow ≥ 50 | red < 50)
  • Sidebar navigation
  • Metric summary cards
  • Responsive layout optimized for desktop + mobile

Sections:
  1. HNI Breakouts      — Close > ₹50 | Vol > 50k | Chg ≥ 4% | Delivery ≥ 50%
  2. 100% Pure Delivery — Close > ₹10 | Vol > 0   | Chg > 0  | Delivery = 100%
  3. F&O Master Tracker — All ~182 F&O EQ stocks with 10-day avg volume
"""

import io
import datetime
import pathlib
import requests
import pandas as pd
import pytz
import streamlit as st

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be the very first Streamlit call)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Institutional Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# PREMIUM CSS  — Trading Terminal Dark Theme
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ═══ RESET / GLOBAL ═══════════════════════════════════════ */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    -webkit-font-smoothing: antialiased;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 1.5rem 2rem 3rem !important;
    max-width: 1440px;
}
@media (max-width: 768px) {
    .block-container { padding: 1rem !important; }
}

/* ═══ APP BACKGROUND ═════════════════════════════════════ */
.stApp {
    background:
        radial-gradient(ellipse 60% 40% at 10% 0%, rgba(59,130,246,0.06) 0%, transparent 60%),
        radial-gradient(ellipse 50% 35% at 90% 0%, rgba(139,92,246,0.06) 0%, transparent 60%),
        #07091a;
    color: #e2e8f0;
}

/* ═══ SIDEBAR ════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0c1226 0%, #090e1c 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    min-width: 220px !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding: 1.2rem 1rem 2rem;
}

/* Sidebar Logo */
.sb-logo {
    text-align: center;
    padding-bottom: 1.2rem;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    margin-bottom: 1.4rem;
}
.sb-logo .sb-icon { font-size: 2rem; line-height: 1; margin-bottom: 6px; }
.sb-logo h2 {
    font-size: 1rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, #00d47a, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.sb-logo small {
    font-size: 0.68rem;
    color: #475569;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* Sidebar status badge */
.sb-status {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(0,212,122,0.08);
    border: 1px solid rgba(0,212,122,0.2);
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 0.76rem;
    color: #00d47a;
    font-weight: 500;
    margin-bottom: 1.4rem;
}
.live-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #00d47a;
    box-shadow: 0 0 7px #00d47a;
    flex-shrink: 0;
    animation: blink 1.8s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* Sidebar label */
.sb-label {
    font-size: 0.65rem;
    font-weight: 700;
    color: #334155;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 1.2rem 0 0.4rem 4px;
}

/* Sidebar divider */
.sb-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.06);
    margin: 1rem 0;
}

/* ═══ HEADER CARD ════════════════════════════════════════ */
.hdr-card {
    background: linear-gradient(135deg,
        rgba(59,130,246,0.07) 0%,
        rgba(139,92,246,0.07) 100%);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 22px 28px 20px;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.hdr-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #00d47a 0%, #3b82f6 50%, #8b5cf6 100%);
}
.hdr-card h1 {
    font-size: 1.65rem;
    font-weight: 900;
    letter-spacing: -0.04em;
    background: linear-gradient(90deg, #f1f5f9, #94a3b8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 4px;
    line-height: 1.1;
}
.hdr-card .tagline {
    font-size: 0.82rem;
    color: #475569;
    margin: 0;
}
.hdr-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
}
.date-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: 20px;
    padding: 5px 12px;
    font-size: 0.76rem;
    color: #60a5fa;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}
.cache-pill {
    font-size: 0.68rem;
    color: #334155;
    font-family: 'JetBrains Mono', monospace;
}

/* ═══ METRIC CARDS ═══════════════════════════════════════ */
.m-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 16px 20px;
    position: relative;
    overflow: hidden;
    transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    cursor: default;
}
.m-card:hover {
    transform: translateY(-3px);
    border-color: rgba(255,255,255,0.14);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}
.m-card::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 0 0 12px 12px;
}
.m-card.gold::after  { background: #f59e0b; }
.m-card.green::after { background: #00d47a; }
.m-card.blue::after  { background: #3b82f6; }
.m-card.purple::after{ background: #8b5cf6; }

.m-icon { font-size: 1.3rem; margin-bottom: 8px; display: block; }
.m-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.1rem;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.03em;
}
.m-card.gold   .m-value  { color: #f59e0b; }
.m-card.green  .m-value  { color: #00d47a; }
.m-card.blue   .m-value  { color: #3b82f6; }
.m-card.purple .m-value  { color: #8b5cf6; }
.m-label {
    font-size: 0.68rem;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    font-weight: 600;
    margin-top: 5px;
}
.m-sub {
    font-size: 0.7rem;
    margin-top: 3px;
    opacity: 0.5;
}

/* ═══ SECTION HEADERS ════════════════════════════════════ */
.sec-hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
    padding: 13px 18px;
    border-radius: 10px 10px 0 0;
    margin-top: 8px;
}
.sec-hdr .title {
    font-size: 0.88rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
    letter-spacing: 0.01em;
}
.sec-hdr .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
}
.chip {
    background: rgba(255,255,255,0.07);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.67rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    opacity: 0.75;
}
.sec-hdr.gold {
    background: linear-gradient(90deg, rgba(245,158,11,0.12), rgba(245,158,11,0.02));
    border-left: 3px solid #f59e0b;
    color: #fbbf24;
}
.sec-hdr.green {
    background: linear-gradient(90deg, rgba(0,212,122,0.12), rgba(0,212,122,0.02));
    border-left: 3px solid #00d47a;
    color: #00d47a;
}
.sec-hdr.blue {
    background: linear-gradient(90deg, rgba(59,130,246,0.12), rgba(59,130,246,0.02));
    border-left: 3px solid #3b82f6;
    color: #60a5fa;
}

/* ═══ DATAFRAME WRAPPER ══════════════════════════════════ */
.table-wrap {
    border: 1px solid rgba(255,255,255,0.07);
    border-top: none;
    border-radius: 0 0 10px 10px;
    overflow: hidden;
    margin-bottom: 4px;
}

/* ═══ EMPTY STATE ════════════════════════════════════════ */
.empty-box {
    text-align: center;
    padding: 40px 20px;
    background: rgba(255,255,255,0.015);
    border: 1px solid rgba(255,255,255,0.07);
    border-top: none;
    border-radius: 0 0 10px 10px;
    color: #334155;
    font-size: 0.88rem;
}

/* ═══ SEARCH BOX ══════════════════════════════════════ */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-size: 0.85rem !important;
    padding: 8px 14px !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(59,130,246,0.5) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
}

/* ═══ ROW COUNT NOTE ═════════════════════════════════ */
.row-note {
    font-size: 0.72rem;
    color: #334155;
    text-align: right;
    margin: 4px 4px 20px;
    font-family: 'JetBrains Mono', monospace;
}

/* ═══ DIVIDER ════════════════════════════════════════ */
.divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.05);
    margin: 28px 0;
}

/* ═══ FOOTER ══════════════════════════════════════════ */
.footer {
    text-align: center;
    font-size: 0.7rem;
    color: #1e293b;
    margin-top: 48px;
    padding: 16px 0 0;
    border-top: 1px solid rgba(255,255,255,0.04);
    letter-spacing: 0.04em;
}

/* ═══ RADIO (sidebar) ════════════════════════════════ */
.stRadio > div { gap: 4px !important; }
.stRadio label {
    font-size: 0.84rem !important;
    padding: 8px 10px !important;
    border-radius: 7px !important;
    transition: background 0.15s !important;
}
.stRadio label:hover { background: rgba(255,255,255,0.05) !important; }

/* ═══ SCROLLBAR ══════════════════════════════════════ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #334155; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# NSE CONFIG
# ─────────────────────────────────────────────────────────────
NSE_HEADERS: dict[str, str] = {
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

NSE_HOLIDAYS: set[datetime.date] = {
    datetime.date(2025, 1, 26), datetime.date(2025, 2, 26),
    datetime.date(2025, 3, 14), datetime.date(2025, 3, 31),
    datetime.date(2025, 4, 14), datetime.date(2025, 4, 18),
    datetime.date(2025, 5, 1),  datetime.date(2025, 8, 15),
    datetime.date(2025, 8, 27), datetime.date(2025, 10, 2),
    datetime.date(2025, 10, 20),datetime.date(2025, 10, 21),
    datetime.date(2025, 11, 5), datetime.date(2025, 12, 25),
    datetime.date(2026, 1, 26), datetime.date(2026, 3, 3),
    datetime.date(2026, 3, 20), datetime.date(2026, 4, 3),
    datetime.date(2026, 4, 14), datetime.date(2026, 5, 1),
    datetime.date(2026, 8, 15), datetime.date(2026, 9, 16),
    datetime.date(2026, 10, 2), datetime.date(2026, 10, 9),
    datetime.date(2026, 11, 9), datetime.date(2026, 12, 25),
}

# ─────────────────────────────────────────────────────────────
# F&O UNIVERSE  (~182 NSE F&O stocks)
# ─────────────────────────────────────────────────────────────
FNO_SYMBOLS: list[str] = [
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT",
    "ADANIPORTS", "ALKEM", "AMBUJACEM", "ANGELONE", "APLAPOLLO", "APOLLOHOSP",
    "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATUL", "AUBANK",
    "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE",
    "BALKRISIND", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT",
    "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL",
    "BRITANNIA", "BSOFT", "CANBK", "CANFINHOME", "CDSL", "CESC", "CHOLAFIN",
    "CIPLA", "COALINDIA", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL",
    "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR",
    "DELTACORP", "DIVISLAB", "DIXON", "DLF", "DMART", "DRREDDY", "EICHERMOT",
    "ESCORTS", "EXIDEIND", "FEDERALBNK", "FINNIFTY", "FORTIS", "GAIL",
    "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES",
    "GRASIM", "GSPL", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC",
    "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER",
    "HINDPETRO", "HINDUNILVR", "HONAUT", "IBULHSGFIN", "ICICIBANK",
    "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL",
    "INDIAMART", "INDUSINDBK", "INDUSTOWER", "INFY", "IOC", "IPCALAB",
    "IRCTC", "ISEC", "ITC", "JINDALSTEL", "JKCEMENT", "JSWSTEEL",
    "JUBLFOOD", "KOTAKBANK", "KPITTECH", "L&TFH", "LALPATHLAB", "LAURUSLABS",
    "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN",
    "MANAPPURAM", "MARICO", "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS",
    "MFSL", "MGL", "MPHASIS", "MRF", "MUTHOOTFIN", "NAUKRI", "NAVINFLUOR",
    "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND",
    "PEL", "PERSISTENT", "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNB",
    "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD",
    "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM",
    "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SUPREMEIND",
    "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS",
    "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM",
    "TORNTPOWER", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UNIONBANK",
    "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZOMATO", "ZYDUSLIFE",
]
FNO_SET: set[str] = set(FNO_SYMBOLS)

# ─────────────────────────────────────────────────────────────
# DATE HELPERS
# ─────────────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")


def is_trading_day(d: datetime.date) -> bool:
    return d.weekday() < 5 and d not in NSE_HOLIDAYS


def last_trading_day() -> datetime.date:
    ist_now  = datetime.datetime.now(IST)
    ist_date = ist_now.date()
    cutoff   = ist_now.replace(hour=19, minute=0, second=0, microsecond=0)
    base     = ist_date if ist_now >= cutoff else ist_date - datetime.timedelta(days=1)
    d = base
    while not is_trading_day(d):
        d -= datetime.timedelta(days=1)
    return d


# ─────────────────────────────────────────────────────────────
# NSE DATA FETCHER
# ─────────────────────────────────────────────────────────────
def _fetch_one_date(
    session: requests.Session, d: datetime.date
) -> pd.DataFrame | None:
    url = (
        "https://nsearchives.nseindia.com/products/content/"
        f"sec_bhavdata_full_{d.strftime('%d%m%Y')}.csv"
    )
    try:
        r = session.get(url, headers=NSE_HEADERS, timeout=30)
        if r.status_code == 200 and len(r.content) > 10_000:
            df = pd.read_csv(io.StringIO(r.text), skipinitialspace=True)
            df.columns = df.columns.str.strip()
            return df
    except Exception:
        pass
    return None


@st.cache_data(ttl=86_400, show_spinner=False)
def fetch_nse_data() -> tuple[pd.DataFrame, datetime.date]:
    base    = last_trading_day()
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=10)
    except Exception:
        pass

    checked   = 0
    candidate = base
    while checked < 7:
        if is_trading_day(candidate):
            df = _fetch_one_date(session, candidate)
            if df is not None:
                return df, candidate
            checked += 1
        candidate -= datetime.timedelta(days=1)

    # ── Local file fallback (committed by GitHub Actions) ────────
    local_csv = pathlib.Path("sec_bhavdata_full.csv")
    if local_csv.exists():
        try:
            df = pd.read_csv(local_csv, skipinitialspace=True)
            df.columns = df.columns.str.strip()
            mtime = datetime.date.fromtimestamp(local_csv.stat().st_mtime)
            return df, mtime
        except Exception:
            pass

    raise ConnectionError(
        "Could not fetch NSE data for the last 7 trading days. "
        "NSE servers may be blocking cloud IPs. "
        "The GitHub Actions workflow will commit a fresh CSV tonight at 7 PM IST."
    )


@st.cache_data(ttl=86_400, show_spinner=False)
def fetch_10day_avg_volume() -> pd.Series:
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
    avg      = combined.groupby("SYMBOL")["TTL_TRD_QNTY"].mean().round(0)
    avg.name = "AVG_VOL_10D"
    return avg


# ─────────────────────────────────────────────────────────────
# DATA PROCESSOR
# ─────────────────────────────────────────────────────────────
DISPLAY_COLS    = ["SYMBOL", "CLOSE_PRICE", "PCT_CHANGE", "TTL_TRD_QNTY", "DELIV_PER"]
DISPLAY_HEADERS = ["Symbol", "Close (₹)", "Change (%)", "Total Volume", "Delivery (%)"]


def _to_display(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame[DISPLAY_COLS].copy()
    out.columns = DISPLAY_HEADERS
    out["Close (₹)"]   = out["Close (₹)"].round(2)
    out["Change (%)"]  = out["Change (%)"].round(2)
    out["Delivery (%)"]= out["Delivery (%)"].round(2)
    return out.reset_index(drop=True)


def process_data(
    raw: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    df = raw[raw["SERIES"].str.strip() == "EQ"].copy()
    for col in ("CLOSE_PRICE", "PREV_CLOSE", "TTL_TRD_QNTY", "DELIV_PER"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["PCT_CHANGE"] = (
        (df["CLOSE_PRICE"] - df["PREV_CLOSE"]) / df["PREV_CLOSE"]
    ) * 100
    df.dropna(subset=["CLOSE_PRICE", "PCT_CHANGE", "DELIV_PER"], inplace=True)
    total_eq = len(df)

    # Filter 1 — HNI Breakouts
    hni = df[
        (df["CLOSE_PRICE"]  > 50.0) &
        (df["TTL_TRD_QNTY"] > 50_000) &
        (df["PCT_CHANGE"]   >= 4.0) &
        (df["DELIV_PER"]    >= 50.0)
    ].sort_values("DELIV_PER", ascending=False)

    # Filter 2 — 100% Pure Delivery
    pure = df[
        (df["CLOSE_PRICE"]  > 10.0) &
        (df["TTL_TRD_QNTY"] > 0) &
        (df["PCT_CHANGE"]   > 0) &
        (df["DELIV_PER"]    == 100.0)
    ].sort_values("TTL_TRD_QNTY", ascending=False)

    return _to_display(hni), _to_display(pure), total_eq


def build_fno_tracker(raw: pd.DataFrame) -> pd.DataFrame:
    fno = raw[
        (raw["SYMBOL"].isin(FNO_SET)) &
        (raw["SERIES"].str.strip() == "EQ")
    ].copy()

    for col in ("CLOSE_PRICE", "PREV_CLOSE", "TTL_TRD_QNTY", "DELIV_PER"):
        if col in fno.columns:
            fno[col] = pd.to_numeric(fno[col], errors="coerce")

    if "PCT_CHANGE" not in fno.columns:
        fno["PCT_CHANGE"] = (
            (fno["CLOSE_PRICE"] - fno["PREV_CLOSE"]) / fno["PREV_CLOSE"]
        ) * 100

    fno = fno.sort_values("PCT_CHANGE", ascending=False)
    return _to_display(fno)


def _merge_avg_vol(display_df: pd.DataFrame, avg_vol: pd.Series) -> pd.DataFrame:
    display_df = display_df.copy()
    if avg_vol.empty:
        display_df["Avg Vol (10D)"] = pd.NA
    else:
        mapped    = display_df["Symbol"].map(avg_vol).round(0)
        insert_at = display_df.columns.get_loc("Total Volume") + 1
        display_df.insert(insert_at, "Avg Vol (10D)", mapped)
    return display_df


# ─────────────────────────────────────────────────────────────
# PANDAS CONDITIONAL STYLING  (green / red / delivery)
# ─────────────────────────────────────────────────────────────
def _color_change(val: float) -> str:
    """Green for positive change, red for negative."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    if v > 0:
        return "color: #00d47a; font-weight: 700;"
    if v < 0:
        return "color: #ff3d5a; font-weight: 700;"
    return "color: #64748b;"


def _color_delivery(val: float) -> str:
    """Color-code delivery % tier."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    if v == 100:
        return "color: #00d47a; font-weight: 800;"
    if v >= 70:
        return "color: #4ade80; font-weight: 700;"
    if v >= 50:
        return "color: #fbbf24; font-weight: 600;"
    return "color: #f87171; font-weight: 500;"


def style_df(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    """Return a Styler with green/red change % and color-coded delivery %."""
    s = df.style
    if "Change (%)" in df.columns:
        s = s.map(_color_change, subset=["Change (%)"])
    if "Delivery (%)" in df.columns:
        s = s.map(_color_delivery, subset=["Delivery (%)"])
    return s


# ─────────────────────────────────────────────────────────────
# COLUMN CONFIG
# ─────────────────────────────────────────────────────────────
_COL_CFG = {
    "Symbol":        st.column_config.TextColumn("Symbol"),
    "Close (₹)":    st.column_config.NumberColumn("Close (₹)",    format="₹%.2f"),
    "Change (%)":   st.column_config.NumberColumn("Change (%)",   format="%.2f%%"),
    "Total Volume": st.column_config.NumberColumn("Volume",       format="%d"),
    "Avg Vol (10D)":st.column_config.NumberColumn("Avg Vol 10D",  format="%d",
                        help="Average daily volume over last 10 trading sessions"),
    "Delivery (%)": st.column_config.NumberColumn("Delivery (%)", format="%.2f%%"),
}


# ─────────────────────────────────────────────────────────────
# UI COMPONENTS
# ─────────────────────────────────────────────────────────────
def metric_card(icon: str, value: str, label: str, sub: str, color: str) -> str:
    return f"""
    <div class="m-card {color}">
        <span class="m-icon">{icon}</span>
        <div class="m-value">{value}</div>
        <div class="m-label">{label}</div>
        <div class="m-sub">{sub}</div>
    </div>"""


def section_header(icon: str, title: str, chips: list[str], color: str) -> str:
    chips_html = "".join(f'<span class="chip">{c}</span>' for c in chips)
    return f"""
    <div class="sec-hdr {color}">
        <div class="title">{icon}&nbsp; {title}</div>
        <div class="chips">{chips_html}</div>
    </div>"""


def render_table(df: pd.DataFrame, empty_msg: str, height: int = 420) -> None:
    if df.empty:
        st.markdown(
            f'<div class="empty-box">🔍 {empty_msg}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
        st.dataframe(
            style_df(df),
            use_container_width=True,
            hide_index=True,
            height=height,
            column_config=_COL_CFG,
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────────────────────
def main() -> None:

    # ── SIDEBAR ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div class="sb-logo">
            <div class="sb-icon">📈</div>
            <h2>NSE Screener</h2>
            <small>Institutional Dashboard</small>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="sb-status">
            <div class="live-dot"></div>
            Live EOD Data
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sb-label">📌 Navigate</div>', unsafe_allow_html=True)
        section = st.radio(
            "Navigate",
            options=[
                "🏠 All Screens",
                "🏦 HNI Breakouts",
                "💎 Pure Delivery",
                "📊 F&O Tracker",
            ],
            label_visibility="collapsed",
        )

        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)
        st.markdown('<div class="sb-label">🎨 Color Guide</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.76rem; line-height:1.9; color:#475569; padding: 0 4px;">
            <span style="color:#00d47a">▲ Green</span> — Positive Change<br>
            <span style="color:#ff3d5a">▼ Red</span> — Negative Change<br>
            <span style="color:#00d47a">■</span> Delivery ≥ 70%<br>
            <span style="color:#fbbf24">■</span> Delivery 50–70%<br>
            <span style="color:#f87171">■</span> Delivery &lt; 50%
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)
        st.markdown('<div class="sb-label">ℹ️ Filters</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.72rem; color:#334155; line-height:1.8; padding: 0 4px;">
            <b style="color:#fbbf24">HNI:</b> Close&gt;₹50 | Vol&gt;50k<br>
            &nbsp;&nbsp;&nbsp;Chg≥4% | Delivery≥50%<br>
            <b style="color:#00d47a">Pure:</b> Close&gt;₹10 | Delivery=100%<br>
            <b style="color:#60a5fa">F&O:</b> ~182 official NSE symbols
        </div>
        """, unsafe_allow_html=True)

    # ── DATA LOADING ─────────────────────────────────────────
    with st.spinner("⏳ Fetching NSE EOD data…"):
        try:
            raw_df, trade_date = fetch_nse_data()
        except ConnectionError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            st.stop()

    hni_df, pure_df, total_eq = process_data(raw_df)
    fno_df                    = build_fno_tracker(raw_df)

    with st.spinner("📊 Loading 10-day average volume…"):
        try:
            avg_vol = fetch_10day_avg_volume()
        except Exception:
            avg_vol = pd.Series(dtype=float)

    hni_df  = _merge_avg_vol(hni_df,  avg_vol)
    pure_df = _merge_avg_vol(pure_df, avg_vol)
    fno_df  = _merge_avg_vol(fno_df,  avg_vol)

    ist_now = datetime.datetime.now(IST)

    # ── HEADER CARD ──────────────────────────────────────────
    c_left, c_right = st.columns([3, 1])
    with c_left:
        st.markdown("""
        <div class="hdr-card">
            <h1>📈 NSE Institutional Screener</h1>
            <p class="tagline">
                End-of-Day Quantitative Screening &nbsp;·&nbsp;
                Automated NSE Data &nbsp;·&nbsp;
                Institutional Grade Filters
            </p>
        </div>
        """, unsafe_allow_html=True)
    with c_right:
        st.markdown(f"""
        <div style="height:100%; display:flex; flex-direction:column;
                    justify-content:center; align-items:flex-end;
                    padding-right:4px; gap:8px;">
            <div class="date-pill">
                📅 &nbsp;{trade_date.strftime("%d %b %Y")}
            </div>
            <div class="cache-pill">
                Updated: {ist_now.strftime("%H:%M IST")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── METRIC CARDS ─────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            metric_card("🏦", str(len(hni_df)), "HNI BREAKOUTS", "Close>₹50 · Chg≥4%", "gold"),
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            metric_card("💎", str(len(pure_df)), "PURE DELIVERY", "Delivery = 100%", "green"),
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            metric_card("📊", str(len(fno_df)), "F&O STOCKS", "Active today", "blue"),
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            metric_card("📈", f"{total_eq:,}", "TOTAL EQ", "All EQ series", "purple"),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    show_all  = section == "🏠 All Screens"
    show_hni  = show_all or section == "🏦 HNI Breakouts"
    show_pure = show_all or section == "💎 Pure Delivery"
    show_fno  = show_all or section == "📊 F&O Tracker"

    # ══════════════════════════════════════════════════════════
    # SECTION 1 — HNI BREAKOUTS
    # ══════════════════════════════════════════════════════════
    if show_hni:
        st.markdown(
            section_header(
                "🏦", "HNI BREAKOUTS",
                ["Close > ₹50", "Volume > 50k", "Change ≥ 4%",
                 "Delivery ≥ 50%", "Sorted by Delivery ↓"],
                "gold",
            ),
            unsafe_allow_html=True,
        )
        render_table(
            hni_df,
            "No HNI Breakout stocks matched today's criteria.",
        )
        if not hni_df.empty:
            st.markdown(
                f'<div class="row-note">{len(hni_df)} stocks matched</div>',
                unsafe_allow_html=True,
            )

    if show_all:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # SECTION 2 — 100% PURE DELIVERY
    # ══════════════════════════════════════════════════════════
    if show_pure:
        st.markdown(
            section_header(
                "💎", "100% PURE DELIVERY",
                ["Close > ₹10", "Volume > 0", "Change > 0%",
                 "Delivery = 100%", "Sorted by Volume ↓"],
                "green",
            ),
            unsafe_allow_html=True,
        )
        render_table(
            pure_df,
            "No stocks recorded exactly 100% delivery with a positive close today.",
        )
        if not pure_df.empty:
            st.markdown(
                f'<div class="row-note">{len(pure_df)} stocks matched</div>',
                unsafe_allow_html=True,
            )

    if show_all:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # SECTION 3 — F&O MASTER TRACKER
    # ══════════════════════════════════════════════════════════
    if show_fno:
        st.markdown(
            section_header(
                "📊", "F&O MASTER TRACKER",
                ["~182 F&O stocks", "EQ series only",
                 "Sorted by Change % ↓", "Click column to re-sort"],
                "blue",
            ),
            unsafe_allow_html=True,
        )

        if fno_df.empty:
            st.markdown(
                '<div class="empty-box">🔍 No F&O stock data found in today\'s bhavcopy.</div>',
                unsafe_allow_html=True,
            )
        else:
            search = st.text_input(
                "fno_search",
                placeholder="🔍  Filter by symbol  (e.g. RELIANCE, INFY, TCS…)",
                label_visibility="collapsed",
                key="fno_search",
            )
            disp = fno_df
            if search.strip():
                mask = disp["Symbol"].str.contains(
                    search.strip().upper(), case=False, na=False
                )
                disp = disp[mask]

            render_table(disp, "No matching F&O symbols.", height=560)
            st.markdown(
                f'<div class="row-note">'
                f'Showing {len(disp)} of {len(fno_df)} F&O stocks'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── FOOTER ───────────────────────────────────────────────
    st.markdown(
        f'<div class="footer">'
        f'NSE Institutional Screener &nbsp;·&nbsp; '
        f'Data: NSE Archives &nbsp;·&nbsp; '
        f'Auto-refreshes daily at 7 PM IST &nbsp;·&nbsp; '
        f'Last loaded: {ist_now.strftime("%d %b %Y %H:%M IST")}'
        f'</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__" or True:
    main()
