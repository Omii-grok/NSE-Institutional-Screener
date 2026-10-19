# -*- coding: utf-8 -*-
"""
Market Universe & Classification Module
=======================================
Provides dynamic, cached classification for:
- Active official NSE F&O universe (dynamically fetched from NSE fo_mktlots.csv)
- Large Cap (NIFTY 100), Mid Cap (NIFTY Midcap 150), Small Cap (NIFTY Smallcap 250)
- Nifty Sector Mappings: Nifty Bank, Nifty IT, Nifty Auto, Nifty Pharma, Nifty FMCG,
  Nifty Metal, Nifty Financial Services, Nifty Realty, Nifty Energy, Nifty Infrastructure, Nifty Media.
- Strict symbol cleaning and standardization (.upper().strip(), .NS conversion).
- Explicit exclusion of non-F&O stocks (DELTACORP, IBULHSGFIN).
"""

import os
import io
import csv
import urllib.request
import streamlit as st

# Configure OpenBLAS
os.environ["OPENBLAS_NUM_THREADS"] = "1"

# Official Fallback Active F&O universe (Excludes DELTACORP, IBULHSGFIN, etc.)
FALLBACK_FNO_SYMBOLS: set[str] = {
    "AARTIIND","ABB","ABBOTINDIA","ABCAPITAL","ABFRL","ACC","ADANIENT",
    "ADANIPORTS","ALKEM","AMBUJACEM","ANGELONE","APLAPOLLO","APOLLOHOSP",
    "APOLLOTYRE","ASHOKLEY","ASIANPAINT","ASTRAL","ATUL","AUBANK",
    "AUROPHARMA","AXISBANK","BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE",
    "BALKRISIND","BANDHANBNK","BANKBARODA","BATAINDIA","BEL","BERGEPAINT",
    "BHARATFORG","BHARTIARTL","BHEL","BIOCON","BOSCHLTD","BPCL",
    "BRITANNIA","BSOFT","CANBK","CANFINHOME","CDSL","CESC","CHOLAFIN",
    "CIPLA","COALINDIA","COFORGE","COLPAL","CONCOR","COROMANDEL",
    "CROMPTON","CUB","CUMMINSIND","DABUR","DALBHARAT","DEEPAKNTR",
    "DIVISLAB","DIXON","DLF","DMART","DRREDDY","EICHERMOT",
    "ESCORTS","EXIDEIND","FEDERALBNK","FORCEMOT","FORTIS","GAIL",
    "GLENMARK","GMRINFRA","GNFC","GODRFRYPHLP","GODREJCP","GODREJPROP","GRANULES",
    "GRASIM","GSPL","GUJGASLTD","HAL","HAVELLS","HCLTECH","HDFCAMC",
    "HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDCOPPER",
    "HINDPETRO","HINDUNILVR","HONAUT","ICICIBANK","ICICIGI",
    "ICICIPRULI","IDEA","IDFCFIRSTB","IEX","IGL","INDHOTEL",
    "INDIAMART","INDUSINDBK","INDUSTOWER","INFY","IOC","IPCALAB",
    "IRCTC","ISEC","ITC","JINDALSTEL","JKCEMENT","JSWENERGY","JSWSTEEL",
    "JUBLFOOD","KAYNES","KOTAKBANK","KPITTECH","L&TFH","LALPATHLAB","LAURUSLABS",
    "LICHSGFIN","LT","LTIM","LTTS","LUPIN","M&M","M&MFIN",
    "MANAPPURAM","MARICO","MARUTI","MAXHEALTH","MCDOWELL-N","MCX","METROPOLIS",
    "MFSL","MGL","MPHASIS","MRF","MUTHOOTFIN","NAUKRI","NAVINFLUOR",
    "NESTLEIND","NMDC","NTPC","OBEROIRLTY","OFSS","ONGC","PAGEIND",
    "PEL","PERSISTENT","PETRONET","PFC","PGEL","PIDILITIND","PIIND",
    "PNB","POLYCAB","POONAWALLA","POWERGRID","PRESTIGE","PVRINOX","RAMCOCEM",
    "RBLBANK","RECLTD","RELIANCE","SAIL","SBICARD","SBILIFE",
    "SBIN","SHREECEM","SHRIRAMFIN","SIEMENS","SOLARINDS","SRF","SUNPHARMA",
    "SUNTV","SYNGENE","TATACHEM","TATACOMM","TATACONSUM","TATAMOTORS",
    "TATAPOWER","TATASTEEL","TCS","TECHM","TITAN","TORNTPHARM",
    "TRENT","TVSMOTOR","UBL","ULTRACEMCO","UNIONBANK","UNITDSPR",
    "UPL","VEDL","VOLTAS","WIPRO","YESBANK","ZYDUSLIFE"
}

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ── SECTOR MAPPING DICTIONARIES ──────────────────────────────
SECTOR_OPTIONS = [
    "All Sectors",
    "Nifty Bank",
    "Nifty IT",
    "Nifty Auto",
    "Nifty Pharma",
    "Nifty FMCG",
    "Nifty Metal",
    "Nifty Financial Services",
    "Nifty Realty",
    "Nifty Energy",
    "Nifty Infrastructure",
    "Nifty Media",
    "Consumer Services",
    "Other Equities"
]

BANK_SYMBOLS = {
    "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "BANKBARODA", "PNB",
    "INDUSINDBK", "AUBANK", "FEDERALBNK", "BANDHANBNK", "IDFCFIRSTB", "CANBK", "RBLBANK",
    "UNIONBANK", "YESBANK", "BANKINDIA", "CENTRALBK", "IOB", "UCOBANK", "MAHABANK", "PSB",
    "J&KBANK", "KARURVYSYA", "SOUTHBANK", "CUB"
}

FIN_SERVICES_SYMBOLS = {
    "BAJFINANCE", "BAJAJFINSV", "HDFCLIFE", "SBILIFE", "ICICIGI", "ICICIPRULI",
    "CHOLAFIN", "MUTHOOTFIN", "SHRIRAMFIN", "PFC", "RECLTD", "L&TFH", "M&MFIN",
    "ABCAPITAL", "MANAPPURAM", "POONAWALLA", "LICHSGFIN", "CANFINHOME", "HDFCAMC",
    "CDSL", "MCX", "IEX", "ANGELONE", "MOTILALOFS", "BSE", "SBICARD"
}

IT_SYMBOLS = {
    "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM", "PERSISTENT", "COFORGE",
    "MPHASIS", "LTTS", "KPITTECH", "TATAELXSI", "OFSS", "BSOFT", "CYIENT",
    "SONACOMS", "ZENSARTECH", "HAPPSTMNDS", "INTELLECT", "MASTEK"
}

AUTO_SYMBOLS = {
    "MARUTI", "M&M", "TATAMOTORS", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO", "TVSMOTOR",
    "BHARATFORG", "ASHOKLEY", "BALKRISIND", "MRF", "APOLLOTYRE", "BOSCHLTD", "MOTHERSON",
    "TIINDIA", "EXIDEIND", "AMARAJABAT", "ENDURANCE", "FORCEMOT", "CEATLTD"
}

PHARMA_SYMBOLS = {
    "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN", "AUROPHARMA", "TORNTPHARM",
    "ZYDUSLIFE", "MANKIND", "ALKEM", "BIOCON", "GLENMARK", "IPCALAB", "ABBOTINDIA",
    "LAURUSLABS", "SYNGENE", "GRANULES", "NATCOPHARM", "AJANTPHARM", "PFIZER", "SANOFI", "JBCHEPHARM"
}

FMCG_SYMBOLS = {
    "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "TATACONSUM", "VBL", "GODREJCP",
    "DABUR", "MARICO", "COLPAL", "PGHH", "EMAMILTD", "RADICO", "UBL", "UNITDSPR",
    "MCDOWELL-N", "BIKAJI", "PATANJALI", "HONASA"
}

METAL_SYMBOLS = {
    "TATASTEEL", "JSWSTEEL", "HINDALCO", "JINDALSTEL", "VEDL", "COALINDIA", "NMDC",
    "SAIL", "HINDCOPPER", "NATIONALUM", "APLAPOLLO", "RATNAMANI", "WELCORP", "JSL"
}

REALTY_SYMBOLS = {
    "DLF", "LODHA", "MACROTECH", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "PHOENIXLTD",
    "BRIGADE", "SOBHA", "SIGNATURE", "SUNTECK"
}

ENERGY_SYMBOLS = {
    "RELIANCE", "ONGC", "NTPC", "POWERGRID", "BPCL", "IOC", "GAIL", "HINDPETRO",
    "TATAPOWER", "ADANIGREEN", "ADANIPOWER", "ADANITRANS", "ATGL", "JSWENERGY",
    "OIL", "PETRONET", "IGL", "MGL", "GUJGASLTD", "GSPL", "NHPC", "SJVN", "SUZLON"
}

INFRA_SYMBOLS = {
    "LT", "ULTRACEMCO", "GRASIM", "AMBUJACEM", "ACC", "SHREECEM", "DALBHARAT",
    "JKCEMENT", "RAMCOCEM", "GMRINFRA", "IRB", "KNRCON", "PNCINFRA", "NCC",
    "SIEMENS", "ABB", "HAL", "BEL", "BHEL", "CUMMINSIND"
}

MEDIA_SYMBOLS = {
    "ZEEL", "SUNTV", "PVRINOX", "NETWORK18", "TV18BRDCST", "NAUKRI", "SAREGAMA", "TIPSINDLTD"
}


def clean_symbol(sym: str) -> str:
    """Standardize symbol by uppercase and trimming, stripping .NS if present."""
    if not sym:
        return ""
    s = str(sym).upper().strip()
    if s.endswith(".NS"):
        s = s[:-3]
    return s.strip()


def to_ns_ticker(sym: str) -> str:
    """Format symbol for Yahoo Finance API by appending .NS."""
    s = clean_symbol(sym)
    return f"{s}.NS" if not s.endswith(".NS") else s


def get_sector_category(sym: str, raw_industry: str = "") -> str:
    """Classify a symbol into a Nifty Sector category."""
    s = clean_symbol(sym)
    if s in BANK_SYMBOLS:
        return "Nifty Bank"
    if s in FIN_SERVICES_SYMBOLS:
        return "Nifty Financial Services"
    if s in IT_SYMBOLS:
        return "Nifty IT"
    if s in AUTO_SYMBOLS:
        return "Nifty Auto"
    if s in PHARMA_SYMBOLS:
        return "Nifty Pharma"
    if s in FMCG_SYMBOLS:
        return "Nifty FMCG"
    if s in METAL_SYMBOLS:
        return "Nifty Metal"
    if s in REALTY_SYMBOLS:
        return "Nifty Realty"
    if s in ENERGY_SYMBOLS:
        return "Nifty Energy"
    if s in INFRA_SYMBOLS:
        return "Nifty Infrastructure"
    if s in MEDIA_SYMBOLS:
        return "Nifty Media"

    # Fallback to raw industry text parsing
    ind = str(raw_industry).lower()
    if "bank" in ind:
        return "Nifty Bank"
    elif "financial" in ind:
        return "Nifty Financial Services"
    elif "information technology" in ind or "software" in ind or "computer" in ind:
        return "Nifty IT"
    elif "auto" in ind:
        return "Nifty Auto"
    elif "health" in ind or "pharma" in ind or "drug" in ind:
        return "Nifty Pharma"
    elif "consumer goods" in ind or "fmcg" in ind or "tobacco" in ind or "food" in ind:
        return "Nifty FMCG"
    elif "metal" in ind or "mining" in ind or "steel" in ind or "aluminum" in ind:
        return "Nifty Metal"
    elif "realt" in ind or "estate" in ind:
        return "Nifty Realty"
    elif "oil" in ind or "gas" in ind or "power" in ind or "energy" in ind or "petroleum" in ind:
        return "Nifty Energy"
    elif "construct" in ind or "capital goods" in ind or "infra" in ind or "cement" in ind:
        return "Nifty Infrastructure"
    elif "media" in ind or "entertainment" in ind:
        return "Nifty Media"
    elif "consumer service" in ind or "service" in ind:
        return "Consumer Services"

    return "Other Equities"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_active_fno_symbols() -> set[str]:
    """Fetch live active F&O underlying symbols directly from NSE Archives fo_mktlots.csv."""
    url = "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            symbols = set()
            for line in lines[1:]:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2 and parts[1]:
                    sym = clean_symbol(parts[1])
                    if sym and sym != "UNDERLYING" and not sym.startswith("NIFTY") and not sym.startswith("BANKNIFTY") and not sym.startswith("FINNIFTY") and not sym.startswith("MIDCPNIFTY"):
                        symbols.add(sym)
            if len(symbols) >= 150:
                # Explicit safety check: ensure DELTACORP is not in active list
                symbols.discard("DELTACORP")
                return symbols
    except Exception:
        pass
    return set(FALLBACK_FNO_SYMBOLS)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def fetch_market_cap_universes() -> dict[str, set[str]]:
    """Fetch official NSE index constituent lists for market cap categorization."""
    indices = {
        "Large Cap": "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv",
        "Mid Cap": "https://nsearchives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
        "Small Cap": "https://nsearchives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
    }
    result = {"Large Cap": set(), "Mid Cap": set(), "Small Cap": set()}
    for cap_name, url in indices.items():
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=6) as resp:
                lines = resp.read().decode("utf-8", errors="ignore").splitlines()
                reader = csv.DictReader(lines)
                for row in reader:
                    sym = clean_symbol(row.get("Symbol", ""))
                    if sym:
                        result[cap_name].add(sym)
        except Exception:
            pass
    return result


def get_market_cap_category(sym: str, universes: dict[str, set[str]] = None) -> str:
    """Return market cap tier: 'Large Cap', 'Mid Cap', 'Small Cap', or 'Micro / Other'."""
    s = clean_symbol(sym)
    if universes is None:
        universes = fetch_market_cap_universes()
    if s in universes.get("Large Cap", set()):
        return "Large Cap"
    elif s in universes.get("Mid Cap", set()):
        return "Mid Cap"
    elif s in universes.get("Small Cap", set()):
        return "Small Cap"
    return "Micro / Other"


def is_fno_stock(sym: str, fno_set: set[str] = None) -> bool:
    """Check if symbol is currently an active F&O contract on NSE."""
    s = clean_symbol(sym)
    if s == "DELTACORP":
        return False
    if fno_set is None:
        fno_set = fetch_active_fno_symbols()
    return s in fno_set
