"""
NSE EOD Institutional Screener — v3.0 Pro Trading Terminal
===========================================================
• Click metric cards to drill into that section
• Dynamic GREEN/RED coloring for % change
• Color-coded Delivery %
• Session-state navigation (no page reload feel)
• Premium dark trading terminal design
"""

import io
import datetime
import pathlib
import requests
import pandas as pd
import pytz
import streamlit as st

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Institutional Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# SESSION STATE — tracks which section is active
# ─────────────────────────────────────────────────────────────
if "view" not in st.session_state:
    st.session_state.view = "overview"

# ─────────────────────────────────────────────────────────────
# PREMIUM CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ═══ GLOBAL ════════════════════════════════════════════════ */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 1.5rem 2rem 3rem !important;
    max-width: 1440px;
    margin-left: auto !important;
    margin-right: auto !important;
}
@media (max-width: 768px) { .block-container { padding: 1rem !important; } }

/* ═══ BACKGROUND ════════════════════════════════════════════ */
.stApp {
    background:
        radial-gradient(ellipse 60% 35% at 15% 0%, rgba(59,130,246,0.07) 0%, transparent 65%),
        radial-gradient(ellipse 50% 30% at 85% 0%, rgba(139,92,246,0.06) 0%, transparent 65%),
        #07091a;
    color: #e2e8f0;
}

/* ═══ SIDEBAR ════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0c1226 0%, #090e1c 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
section[data-testid="stSidebar"] > div:first-child { padding: 1.2rem 1rem 2rem; }

.sb-logo { text-align:center; padding-bottom:1.2rem; border-bottom:1px solid rgba(255,255,255,0.07); margin-bottom:1.4rem; }
.sb-logo .ic { font-size:2.2rem; line-height:1; }
.sb-logo h2 { font-size:1rem; font-weight:800; margin:6px 0 2px; letter-spacing:-0.02em;
    background:linear-gradient(90deg,#00d47a,#3b82f6); -webkit-background-clip:text;
    -webkit-text-fill-color:transparent; background-clip:text; }
.sb-logo small { font-size:0.65rem; color:#334155; letter-spacing:0.07em; text-transform:uppercase; }

.sb-live { display:flex; align-items:center; gap:8px; background:rgba(0,212,122,0.08);
    border:1px solid rgba(0,212,122,0.2); border-radius:8px; padding:8px 10px;
    font-size:0.76rem; color:#00d47a; font-weight:500; margin-bottom:1.4rem; }
.live-dot { width:7px; height:7px; border-radius:50%; background:#00d47a;
    box-shadow:0 0 7px #00d47a; flex-shrink:0; animation:blink 1.8s ease-in-out infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

.sb-label { font-size:0.65rem; font-weight:700; color:#334155; text-transform:uppercase;
    letter-spacing:0.1em; margin:1.2rem 0 0.5rem 2px; }
.sb-hr { border:none; border-top:1px solid rgba(255,255,255,0.06); margin:1rem 0; }

/* ═══ HEADER ════════════════════════════════════════════ */
.hdr {
    background: linear-gradient(135deg, rgba(59,130,246,0.07) 0%, rgba(139,92,246,0.06) 100%);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 20px 28px 18px;
    margin-bottom: 18px;
    position: relative;
    overflow: hidden;
}
.hdr::before { content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:linear-gradient(90deg,#00d47a,#3b82f6,#8b5cf6); }
.hdr h1 { font-size:1.55rem; font-weight:900; letter-spacing:-0.04em; margin:0 0 4px;
    background:linear-gradient(90deg,#f1f5f9,#94a3b8); -webkit-background-clip:text;
    -webkit-text-fill-color:transparent; background-clip:text; }
.hdr p { font-size:0.8rem; color:#475569; margin:0; }
.date-pill { display:inline-flex; align-items:center; gap:6px;
    background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.2);
    border-radius:20px; padding:5px 12px; font-size:0.75rem; color:#60a5fa;
    font-weight:600; font-family:'JetBrains Mono',monospace; }

/* ═══ METRIC NAV CARDS (clickable via buttons) ═══════════ */

/* Base style for ALL metric-row buttons */
[data-testid="stHorizontalBlock"]:first-of-type .stButton > button {
    background: rgba(255,255,255,0.025) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    padding: 0 !important;
    min-height: 118px !important;
    width: 100% !important;
    text-align: left !important;
    white-space: pre-wrap !important;
    font-family: 'Inter', sans-serif !important;
    color: #e2e8f0 !important;
    font-size: 0.78rem !important;
    line-height: 1.5 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    display: flex !important;
    align-items: flex-start !important;
    justify-content: flex-start !important;
    overflow: hidden !important;
    position: relative !important;
}
[data-testid="stHorizontalBlock"]:first-of-type .stButton > button:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 30px rgba(0,0,0,0.5) !important;
    border-color: rgba(255,255,255,0.15) !important;
    background: rgba(255,255,255,0.04) !important;
}

/* Per-card accent color on bottom border */
[data-testid="stHorizontalBlock"]:first-of-type
  [data-testid="column"]:nth-child(1) .stButton > button {
    border-bottom: 3px solid #f59e0b !important;
}
[data-testid="stHorizontalBlock"]:first-of-type
  [data-testid="column"]:nth-child(2) .stButton > button {
    border-bottom: 3px solid #00d47a !important;
}
[data-testid="stHorizontalBlock"]:first-of-type
  [data-testid="column"]:nth-child(3) .stButton > button {
    border-bottom: 3px solid #3b82f6 !important;
}
[data-testid="stHorizontalBlock"]:first-of-type
  [data-testid="column"]:nth-child(4) .stButton > button {
    border-bottom: 3px solid #8b5cf6 !important;
}

/* Active card glow */
[data-testid="stHorizontalBlock"]:first-of-type
  [data-testid="column"]:nth-child(1) .stButton > button:focus {
    box-shadow: 0 0 0 2px rgba(245,158,11,0.4), 0 8px 30px rgba(0,0,0,0.5) !important;
}
[data-testid="stHorizontalBlock"]:first-of-type
  [data-testid="column"]:nth-child(2) .stButton > button:focus {
    box-shadow: 0 0 0 2px rgba(0,212,122,0.4), 0 8px 30px rgba(0,0,0,0.5) !important;
}
[data-testid="stHorizontalBlock"]:first-of-type
  [data-testid="column"]:nth-child(3) .stButton > button:focus {
    box-shadow: 0 0 0 2px rgba(59,130,246,0.4), 0 8px 30px rgba(0,0,0,0.5) !important;
}

/* ═══ ACTIVE SECTION BADGE ════════════════════════════════ */
.active-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 0.85rem;
    font-weight: 700;
    margin-bottom: 14px;
}
.active-badge.gold   { background:rgba(245,158,11,0.1);  border:1px solid rgba(245,158,11,0.25);  color:#fbbf24; }
.active-badge.green  { background:rgba(0,212,122,0.1);   border:1px solid rgba(0,212,122,0.25);   color:#00d47a; }
.active-badge.blue   { background:rgba(59,130,246,0.1);  border:1px solid rgba(59,130,246,0.25);  color:#60a5fa; }

/* ═══ BACK BUTTON ═══════════════════════════════════════ */
.back-btn .stButton > button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 7px !important;
    color: #475569 !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 5px 14px !important;
    transition: all 0.15s !important;
    height: auto !important;
    min-height: unset !important;
    white-space: nowrap !important;
}
.back-btn .stButton > button:hover {
    background: rgba(255,255,255,0.05) !important;
    border-color: rgba(255,255,255,0.15) !important;
    color: #94a3b8 !important;
    transform: none !important;
}

/* ═══ SECTION HEADERS ═══════════════════════════════════ */
.sec-hdr {
    display:flex; align-items:center; justify-content:space-between;
    flex-wrap:wrap; gap:8px; padding:13px 18px;
    border-radius:10px 10px 0 0; margin-top:6px;
}
.sec-hdr .title { font-size:0.88rem; font-weight:700;
    display:flex; align-items:center; gap:8px; }
.sec-hdr .chips { display:flex; flex-wrap:wrap; gap:5px; }
.chip { background:rgba(255,255,255,0.07); border-radius:4px;
    padding:2px 8px; font-size:0.67rem; font-weight:600; opacity:0.8; }
.sec-hdr.gold  { background:linear-gradient(90deg,rgba(245,158,11,0.1),rgba(245,158,11,0.02));  border-left:3px solid #f59e0b; color:#fbbf24; }
.sec-hdr.green { background:linear-gradient(90deg,rgba(0,212,122,0.1),rgba(0,212,122,0.02));   border-left:3px solid #00d47a; color:#00d47a; }
.sec-hdr.blue  { background:linear-gradient(90deg,rgba(59,130,246,0.1),rgba(59,130,246,0.02)); border-left:3px solid #3b82f6; color:#60a5fa; }

/* ═══ TABLE WRAPPER ══════════════════════════════════════ */
.tbl-wrap {
    border:1px solid rgba(255,255,255,0.07);
    border-top:none;
    border-radius:0 0 10px 10px;
    overflow:hidden;
    margin-bottom:6px;
}
.empty-box {
    text-align:center; padding:40px 20px;
    background:rgba(255,255,255,0.015);
    border:1px solid rgba(255,255,255,0.07);
    border-top:none; border-radius:0 0 10px 10px;
    color:#334155; font-size:0.88rem;
}
.row-note { font-size:0.71rem; color:#334155; text-align:right;
    margin:4px 4px 20px; font-family:'JetBrains Mono',monospace; }

/* ═══ DIVIDER ════════════════════════════════════════════ */
.divider { border:none; border-top:1px solid rgba(255,255,255,0.05); margin:24px 0; }

/* ═══ SEARCH BOX ═══════════════════════════════════════ */
.stTextInput > div > div > input {
    background:rgba(255,255,255,0.04) !important;
    border:1px solid rgba(255,255,255,0.09) !important;
    border-radius:8px !important; color:#e2e8f0 !important;
    font-size:0.85rem !important; padding:8px 14px !important;
}
.stTextInput > div > div > input:focus {
    border-color:rgba(59,130,246,0.5) !important;
    box-shadow:0 0 0 3px rgba(59,130,246,0.1) !important;
}

/* ═══ FOOTER ══════════════════════════════════════════ */
.footer { text-align:center; font-size:0.7rem; color:#1e293b;
    margin-top:48px; padding:16px 0 0;
    border-top:1px solid rgba(255,255,255,0.04); letter-spacing:0.04em; }

/* ═══ SCROLLBAR ══════════════════════════════════════ */
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#1e293b; border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:#334155; }
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

FNO_SYMBOLS: list[str] = [
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
    "JUBLFOOD","KOTAKBANK","KPITTECH","L&TFH","LALPATHLAB","LAURUSLABS",
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
# DATA FETCHERS
# ─────────────────────────────────────────────────────────────
def _fetch_one_date(session: requests.Session, d: datetime.date) -> pd.DataFrame | None:
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
    checked, candidate = 0, base
    while checked < 7:
        if is_trading_day(candidate):
            df = _fetch_one_date(session, candidate)
            if df is not None:
                return df, candidate
            checked += 1
        candidate -= datetime.timedelta(days=1)

    local = pathlib.Path("sec_bhavdata_full.csv")
    if local.exists():
        try:
            df = pd.read_csv(local, skipinitialspace=True)
            df.columns = df.columns.str.strip()
            return df, datetime.date.fromtimestamp(local.stat().st_mtime)
        except Exception:
            pass
    raise ConnectionError(
        "Could not fetch NSE data. GitHub Actions will commit fresh data at 7 PM IST."
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
    collected, candidate, attempts = 0, base, 0
    while collected < 10 and attempts < 25:
        attempts += 1
        if is_trading_day(candidate):
            df = _fetch_one_date(session, candidate)
            if df is not None and "SERIES" in df.columns:
                eq = df[df["SERIES"].str.strip() == "EQ"][["SYMBOL","TTL_TRD_QNTY"]].copy()
                eq["TTL_TRD_QNTY"] = pd.to_numeric(eq["TTL_TRD_QNTY"], errors="coerce")
                frames.append(eq)
                collected += 1
        candidate -= datetime.timedelta(days=1)
    if not frames:
        return pd.Series(dtype=float, name="AVG_VOL_10D")
    combined = pd.concat(frames, ignore_index=True)
    avg = combined.groupby("SYMBOL")["TTL_TRD_QNTY"].mean().round(0)
    avg.name = "AVG_VOL_10D"
    return avg

# ─────────────────────────────────────────────────────────────
# DATA PROCESSING
# ─────────────────────────────────────────────────────────────
DCOLS = ["SYMBOL","CLOSE_PRICE","PCT_CHANGE","TTL_TRD_QNTY","DELIV_PER"]
DHDRS = ["Symbol","Close (₹)","Change (%)","Total Volume","Delivery (%)"]

def _to_display(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame[DCOLS].copy()
    out.columns = DHDRS
    out["Close (₹)"]    = out["Close (₹)"].round(2)
    out["Change (%)"]   = out["Change (%)"].round(2)
    out["Delivery (%)"] = out["Delivery (%)"].round(2)
    return out.reset_index(drop=True)

def process_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    df = raw[raw["SERIES"].str.strip() == "EQ"].copy()
    for c in ("CLOSE_PRICE","PREV_CLOSE","TTL_TRD_QNTY","DELIV_PER"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["PCT_CHANGE"] = (df["CLOSE_PRICE"] - df["PREV_CLOSE"]) / df["PREV_CLOSE"] * 100
    df.dropna(subset=["CLOSE_PRICE","PCT_CHANGE","DELIV_PER"], inplace=True)
    total = len(df)
    hni = df[
        (df["CLOSE_PRICE"]  > 50)  &
        (df["TTL_TRD_QNTY"] > 50_000) &
        (df["PCT_CHANGE"]   >= 4) &
        (df["DELIV_PER"]    >= 50)
    ].sort_values("DELIV_PER", ascending=False)
    pure = df[
        (df["CLOSE_PRICE"]  > 10)  &
        (df["TTL_TRD_QNTY"] > 0) &
        (df["PCT_CHANGE"]   > 0) &
        (df["DELIV_PER"]    == 100)
    ].sort_values("TTL_TRD_QNTY", ascending=False)
    return _to_display(hni), _to_display(pure), total

def build_fno_tracker(raw: pd.DataFrame) -> pd.DataFrame:
    fno = raw[(raw["SYMBOL"].isin(FNO_SET)) & (raw["SERIES"].str.strip()=="EQ")].copy()
    for c in ("CLOSE_PRICE","PREV_CLOSE","TTL_TRD_QNTY","DELIV_PER"):
        if c in fno.columns:
            fno[c] = pd.to_numeric(fno[c], errors="coerce")
    if "PCT_CHANGE" not in fno.columns:
        fno["PCT_CHANGE"] = (fno["CLOSE_PRICE"]-fno["PREV_CLOSE"])/fno["PREV_CLOSE"]*100
    return _to_display(fno.sort_values("PCT_CHANGE", ascending=False))

def _merge_avg_vol(df: pd.DataFrame, avg: pd.Series) -> pd.DataFrame:
    df = df.copy()
    if not avg.empty:
        idx = df.columns.get_loc("Total Volume") + 1
        df.insert(idx, "Avg Vol (10D)", df["Symbol"].map(avg).round(0))
    return df

# ─────────────────────────────────────────────────────────────
# PANDAS STYLER  — green/red/delivery colors
# ─────────────────────────────────────────────────────────────
def _clr_chg(v):
    try:
        f = float(v)
    except Exception:
        return ""
    if f > 0: return "color:#00d47a;font-weight:700"
    if f < 0: return "color:#ff3d5a;font-weight:700"
    return "color:#475569"

def _clr_del(v):
    try:
        f = float(v)
    except Exception:
        return ""
    if f == 100: return "color:#00d47a;font-weight:800"
    if f >= 70:  return "color:#4ade80;font-weight:700"
    if f >= 50:  return "color:#fbbf24;font-weight:600"
    return "color:#f87171;font-weight:500"

def styled(df: pd.DataFrame):
    s = df.style
    if "Change (%)"   in df.columns: s = s.map(_clr_chg, subset=["Change (%)"])
    if "Delivery (%)" in df.columns: s = s.map(_clr_del, subset=["Delivery (%)"])
    return s

_CFG = {
    "Symbol":        st.column_config.TextColumn("Symbol"),
    "Close (₹)":    st.column_config.NumberColumn("Close (₹)",    format="₹%.2f"),
    "Change (%)":   st.column_config.NumberColumn("Change (%)",   format="%.2f%%"),
    "Total Volume": st.column_config.NumberColumn("Volume",       format="%d"),
    "Avg Vol (10D)":st.column_config.NumberColumn("Avg Vol 10D",  format="%d",
                        help="Average daily volume over last 10 sessions"),
    "Delivery (%)": st.column_config.NumberColumn("Delivery (%)", format="%.2f%%"),
}

# ─────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────
def render_section(icon, title, chips, color, df, empty_msg, height=420):
    chips_html = "".join(f'<span class="chip">{c}</span>' for c in chips)
    st.markdown(f"""
    <div class="sec-hdr {color}">
        <div class="title">{icon}&nbsp; {title}</div>
        <div class="chips">{chips_html}</div>
    </div>""", unsafe_allow_html=True)

    if df.empty:
        st.markdown(f'<div class="empty-box">🔍 {empty_msg}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="tbl-wrap">', unsafe_allow_html=True)
        st.dataframe(styled(df), use_container_width=True,
                     hide_index=True, height=height, column_config=_CFG)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(f'<div class="row-note">{len(df)} stocks matched</div>',
                    unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────
def main():

    # ── SIDEBAR ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div class="sb-logo">
            <div class="ic">📈</div>
            <h2>NSE Screener</h2>
            <small>Institutional Dashboard</small>
        </div>
        <div class="sb-live">
            <div class="live-dot"></div>
            Live EOD Data
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sb-label">🎨 Color Guide</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.76rem;line-height:2;color:#475569;padding:0 4px">
            <span style="color:#00d47a">▲</span> Positive Change<br>
            <span style="color:#ff3d5a">▼</span> Negative Change<br>
            <span style="color:#00d47a">●</span> Delivery ≥ 70%<br>
            <span style="color:#fbbf24">●</span> Delivery 50–70%<br>
            <span style="color:#f87171">●</span> Delivery &lt; 50%
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<hr class="sb-hr"><div class="sb-label">📐 Filter Logic</div>',
                    unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.71rem;color:#334155;line-height:1.9;padding:0 4px">
            <b style="color:#fbbf24">HNI</b> · Close&gt;₹50 · Vol&gt;50k<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Chg≥4% · Delivery≥50%<br>
            <b style="color:#00d47a">Pure</b> · Close&gt;₹10 · Del=100%<br>
            <b style="color:#60a5fa">F&amp;O</b> · ~182 official symbols
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<hr class="sb-hr"><div class="sb-label">ℹ️ Tip</div>',
                    unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.71rem;color:#334155;line-height:1.7;padding:0 4px">
            Click any metric card above<br>
            to drill into that section.<br>
            Click <b style="color:#94a3b8">Overview</b> to see all.
        </div>
        """, unsafe_allow_html=True)

    # ── DATA LOADING ─────────────────────────────────────────
    with st.spinner("⏳ Fetching NSE EOD data…"):
        try:
            raw_df, trade_date = fetch_nse_data()
        except ConnectionError as e:
            st.error(str(e)); st.stop()
        except Exception as e:
            st.error(f"Unexpected error: {e}"); st.stop()

    hni_df, pure_df, total_eq = process_data(raw_df)
    fno_df                    = build_fno_tracker(raw_df)

    with st.spinner("📊 Loading 10-day average volume…"):
        try:   avg_vol = fetch_10day_avg_volume()
        except Exception: avg_vol = pd.Series(dtype=float)

    hni_df  = _merge_avg_vol(hni_df,  avg_vol)
    pure_df = _merge_avg_vol(pure_df, avg_vol)
    fno_df  = _merge_avg_vol(fno_df,  avg_vol)

    ist_now = datetime.datetime.now(IST)

    # ── HEADER ───────────────────────────────────────────────
    hc1, hc2 = st.columns([3, 1])
    with hc1:
        st.markdown("""
        <div class="hdr">
            <h1>📈 NSE Institutional Screener</h1>
            <p>End-of-Day Quantitative Screening &nbsp;·&nbsp;
               Automated NSE Data &nbsp;·&nbsp;
               Institutional Grade Filters</p>
        </div>""", unsafe_allow_html=True)
    with hc2:
        st.markdown(f"""
        <div style="height:100%;display:flex;flex-direction:column;
                    justify-content:center;align-items:flex-end;gap:8px;padding-right:4px">
            <div class="date-pill">📅 &nbsp;{trade_date.strftime('%d %b %Y')}</div>
            <div style="font-size:0.68rem;color:#334155;
                        font-family:'JetBrains Mono',monospace">
                Refreshed {ist_now.strftime('%H:%M IST')}
            </div>
        </div>""", unsafe_allow_html=True)

    # ── CLICKABLE METRIC NAV CARDS ───────────────────────────
    # Each button is styled as a metric card via CSS (nth-child targeting).
    # Clicking sets session_state.view and reruns.
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        active_hni = st.session_state.view == "hni"
        if st.button(
            f"🏦  HNI BREAKOUTS\n"
            f"{'━'*18}\n"
            f"  {len(hni_df):>4}  stocks\n"
            f"Close>₹50 · Chg≥4%",
            key="nav_hni",
            use_container_width=True,
        ):
            st.session_state.view = "overview" if active_hni else "hni"
            st.rerun()

    with c2:
        active_pure = st.session_state.view == "pure"
        if st.button(
            f"💎  PURE DELIVERY\n"
            f"{'━'*18}\n"
            f"  {len(pure_df):>4}  stocks\n"
            f"Delivery = 100%",
            key="nav_pure",
            use_container_width=True,
        ):
            st.session_state.view = "overview" if active_pure else "pure"
            st.rerun()

    with c3:
        active_fno = st.session_state.view == "fno"
        if st.button(
            f"📊  F&O TRACKER\n"
            f"{'━'*18}\n"
            f"  {len(fno_df):>4}  stocks\n"
            f"~182 F&O symbols",
            key="nav_fno",
            use_container_width=True,
        ):
            st.session_state.view = "overview" if active_fno else "fno"
            st.rerun()

    with c4:
        if st.button(
            f"📈  TOTAL EQ\n"
            f"{'━'*18}\n"
            f"  {total_eq:>4}  stocks\n"
            f"All EQ series",
            key="nav_all",
            use_container_width=True,
        ):
            st.session_state.view = "overview"
            st.rerun()

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── BACK BUTTON + ACTIVE SECTION BADGE ───────────────────
    view = st.session_state.view
    if view != "overview":
        badge_map = {
            "hni":  ("gold",  "🏦  HNI BREAKOUTS"),
            "pure": ("green", "💎  100% PURE DELIVERY"),
            "fno":  ("blue",  "📊  F&O MASTER TRACKER"),
        }
        bcolor, btitle = badge_map[view]
        row_l, row_r = st.columns([5, 1])
        with row_l:
            st.markdown(
                f'<div class="active-badge {bcolor}">'
                f'{btitle} &nbsp;·&nbsp; Click card again or "← All" to return'
                f'</div>',
                unsafe_allow_html=True,
            )
        with row_r:
            st.markdown('<div class="back-btn">', unsafe_allow_html=True)
            if st.button("← All Screens", key="back_btn"):
                st.session_state.view = "overview"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # CONTENT SECTIONS  (conditional on session state)
    # ══════════════════════════════════════════════════════════
    if view in ("overview", "hni"):
        render_section(
            "🏦", "HNI BREAKOUTS",
            ["Close > ₹50", "Volume > 50k", "Change ≥ 4%",
             "Delivery ≥ 50%", "Sorted by Delivery ↓"],
            "gold", hni_df,
            "No HNI Breakout stocks matched today's criteria.",
        )

    if view == "overview":
        st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if view in ("overview", "pure"):
        render_section(
            "💎", "100% PURE DELIVERY",
            ["Close > ₹10", "Volume > 0", "Change > 0%",
             "Delivery = 100%", "Sorted by Volume ↓"],
            "green", pure_df,
            "No stocks recorded exactly 100% delivery with a positive close today.",
        )

    if view == "overview":
        st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if view in ("overview", "fno"):
        render_section(
            "📊", "F&O MASTER TRACKER",
            ["~182 F&O stocks", "EQ series", "Sorted Change % ↓", "Click header to sort"],
            "blue", pd.DataFrame(),   # placeholder — handled separately below
            "",
            height=560,
        ) if False else None   # skip — F&O needs search box, handle manually

        # F&O section header
        chips_h = "".join(
            f'<span class="chip">{c}</span>'
            for c in ["~182 F&O stocks","EQ series","Sorted Change % ↓","Click header to sort"]
        )
        st.markdown(f"""
        <div class="sec-hdr blue">
            <div class="title">📊&nbsp; F&O MASTER TRACKER</div>
            <div class="chips">{chips_h}</div>
        </div>""", unsafe_allow_html=True)

        if fno_df.empty:
            st.markdown(
                '<div class="empty-box">🔍 No F&O stock data found.</div>',
                unsafe_allow_html=True,
            )
        else:
            search = st.text_input(
                "fno_search",
                placeholder="🔍  Filter symbol  (e.g. RELIANCE, INFY, TCS, HDFC…)",
                label_visibility="collapsed",
                key="fno_search",
            )
            disp = fno_df
            if search.strip():
                disp = disp[disp["Symbol"].str.contains(
                    search.strip().upper(), case=False, na=False
                )]
            st.markdown('<div class="tbl-wrap">', unsafe_allow_html=True)
            st.dataframe(styled(disp), use_container_width=True,
                         hide_index=True, height=560, column_config=_CFG)
            st.markdown("</div>", unsafe_allow_html=True)
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
        f'Auto-refreshes daily 7 PM IST &nbsp;·&nbsp; '
        f'{ist_now.strftime("%d %b %Y %H:%M IST")}'
        f'</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__" or True:
    main()
